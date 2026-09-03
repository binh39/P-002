"""Build and cache immutable project environment artifacts.

The builder is deliberately separate from the v8 shared-runtime preparer.  It
accepts a canonical DependencyPlan, resolves one project into a staging venv,
and publishes an immutable archive only after consistency and inventory checks.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

from cloud.sandbox_dependency_plan import DependencyPlan, DependencySource
from cloud.sandbox_errors import ResolverDiagnostic, classify_resolver_failure
from cloud.sandbox_security import redact_sensitive_text

ARTIFACT_MANIFEST_VERSION = 1


class SandboxBuildError(RuntimeError):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        retryable: bool = False,
        diagnostic: ResolverDiagnostic | None = None,
        sources: tuple[str, ...] = (),
    ):
        self.error_code = error_code
        self.retryable = retryable
        self.diagnostic = diagnostic
        self.sources = sources
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ImageIdentity:
    python_minor: str
    python_full_version: str
    platform: str
    architecture: str
    image_digest: str

    def __post_init__(self) -> None:
        if not self.image_digest.startswith("sha256:") or len(self.image_digest) != 71:
            raise ValueError("image_digest must be a sha256:<64 lowercase hex> digest")
        try:
            int(self.image_digest.removeprefix("sha256:"), 16)
        except ValueError as exc:
            raise ValueError("image_digest must be a sha256:<64 lowercase hex> digest") from exc
        if self.image_digest != self.image_digest.lower():
            raise ValueError("image_digest must be a sha256:<64 lowercase hex> digest")

    @classmethod
    def current(cls, *, image_digest: str) -> ImageIdentity:
        full = platform.python_version()
        return cls(
            python_minor=".".join(full.split(".")[:2]),
            python_full_version=full,
            platform=sys.platform,
            architecture=platform.machine().lower(),
            image_digest=image_digest,
        )


@dataclass(frozen=True, slots=True)
class RunnerIdentity:
    profile: str
    pytest_version: str
    coverage_version: str
    adapter_version: int = 1


@dataclass(frozen=True, slots=True)
class PackageRecord:
    name: str
    version: str


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    fingerprint: str
    artifact_sha256: str
    artifact_size: int
    dependency_plan_fingerprint: str
    image: ImageIdentity
    runner: RunnerIdentity
    inventory: tuple[PackageRecord, ...]
    inventory_sha256: str
    created_at_epoch: int
    last_used_at_epoch: int
    manifest_version: int = ARTIFACT_MANIFEST_VERSION

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["inventory"] = [asdict(item) for item in self.inventory]
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> ArtifactManifest:
        if payload.get("manifest_version") != ARTIFACT_MANIFEST_VERSION:
            raise ValueError("Unsupported artifact manifest version")
        return cls(
            fingerprint=payload["fingerprint"],
            artifact_sha256=payload["artifact_sha256"],
            artifact_size=int(payload["artifact_size"]),
            dependency_plan_fingerprint=payload["dependency_plan_fingerprint"],
            image=ImageIdentity(**payload["image"]),
            runner=RunnerIdentity(**payload["runner"]),
            inventory=tuple(PackageRecord(**item) for item in payload["inventory"]),
            inventory_sha256=payload["inventory_sha256"],
            created_at_epoch=int(payload["created_at_epoch"]),
            last_used_at_epoch=int(payload["last_used_at_epoch"]),
            manifest_version=int(payload["manifest_version"]),
        )


@dataclass(slots=True)
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    publishes: int = 0
    corruptions: int = 0
    evictions: int = 0
    lease_contentions: int = 0
    build_duration_seconds: list[float] = field(default_factory=list)
    retry_count: int = 0


@dataclass(frozen=True, slots=True)
class CachePolicy:
    ttl_seconds: int = 30 * 24 * 60 * 60
    quota_bytes: int = 10 * 1024 * 1024 * 1024
    lease_seconds: int = 1800


@dataclass(frozen=True, slots=True)
class CachedArtifact:
    directory: Path
    archive: Path
    manifest: ArtifactManifest


class ArtifactLease:
    def __init__(self, path: Path, owner: str):
        self.path = path
        self.owner = owner
        self.acquired = False

    def __enter__(self) -> ArtifactLease:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        if not self.acquired:
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("owner") == self.owner:
                self.path.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError):
            pass


class FileArtifactCache:
    def __init__(
        self,
        root: Path,
        *,
        policy: CachePolicy | None = None,
        clock=time.time,
        metrics: CacheMetrics | None = None,
    ):
        self.root = root.resolve()
        self.policy = policy or CachePolicy()
        self.clock = clock
        self.metrics = metrics or CacheMetrics()
        self.objects = self.root / "objects"
        self.staging = self.root / "staging"
        self.leases = self.root / "leases"
        self.access = self.root / "access"
        self.quarantine = self.root / "quarantine"
        for directory in (self.objects, self.staging, self.leases, self.access, self.quarantine):
            directory.mkdir(parents=True, exist_ok=True)

    def _object_directory(self, fingerprint: str) -> Path:
        _validate_fingerprint(fingerprint)
        return self.objects / fingerprint

    def get(self, fingerprint: str, *, count_metrics: bool = True) -> CachedArtifact | None:
        directory = self._object_directory(fingerprint)
        manifest_path = directory / "manifest.json"
        archive = directory / "environment.tar.gz"
        if not manifest_path.is_file() or not archive.is_file():
            if count_metrics:
                self.metrics.misses += 1
            return None
        try:
            manifest = ArtifactManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
            if manifest.fingerprint != fingerprint:
                raise ValueError("Manifest fingerprint mismatch")
            expected_fingerprint = _identity_fingerprint(
                manifest.dependency_plan_fingerprint,
                manifest.image,
                manifest.runner,
            )
            if expected_fingerprint != fingerprint:
                raise ValueError("Manifest identity mismatch")
            if _inventory_sha256(manifest.inventory) != manifest.inventory_sha256:
                raise ValueError("Package inventory hash mismatch")
            if archive.stat().st_size != manifest.artifact_size or _sha256_file(archive) != manifest.artifact_sha256:
                raise ValueError("Artifact content hash mismatch")
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            self.metrics.corruptions += 1
            self._quarantine(directory, fingerprint)
            if count_metrics:
                self.metrics.misses += 1
            return None
        self._record_access(fingerprint)
        if count_metrics:
            self.metrics.hits += 1
        return CachedArtifact(directory=directory, archive=archive, manifest=manifest)

    def acquire(self, fingerprint: str) -> ArtifactLease:
        _validate_fingerprint(fingerprint)
        path = self.leases / f"{fingerprint}.json"
        owner = uuid.uuid4().hex
        now = int(self.clock())
        payload = {"owner": owner, "created_at": now, "expires_at": now + self.policy.lease_seconds}
        lease = ArtifactLease(path, owner)
        try:
            with path.open("x", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True)
            lease.acquired = True
            return lease
        except FileExistsError:
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                expired = int(existing.get("expires_at", 0)) <= now
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                expired = True
            if expired:
                path.unlink(missing_ok=True)
                return self.acquire(fingerprint)
            self.metrics.lease_contentions += 1
            raise SandboxBuildError(
                "ARTIFACT_BUILD_IN_PROGRESS", "Another worker holds the artifact lease", retryable=True
            )

    def create_staging(self, fingerprint: str) -> Path:
        _validate_fingerprint(fingerprint)
        directory = Path(tempfile.mkdtemp(prefix=f"{fingerprint[:12]}-", dir=self.staging))
        return directory

    def publish(self, fingerprint: str, staging: Path, manifest: ArtifactManifest) -> CachedArtifact:
        target = self._object_directory(fingerprint)
        if manifest.fingerprint != fingerprint:
            raise SandboxBuildError("ARTIFACT_FINGERPRINT_MISMATCH", "Manifest does not match cache key")
        archive = staging / "environment.tar.gz"
        if not archive.is_file() or _sha256_file(archive) != manifest.artifact_sha256:
            raise SandboxBuildError("ARTIFACT_STAGING_INVALID", "Staged artifact does not match its manifest")
        (staging / "manifest.json").write_text(
            json.dumps(manifest.as_dict(), sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )
        existing = self.get(fingerprint, count_metrics=False)
        if existing is not None:
            shutil.rmtree(staging, ignore_errors=True)
            return existing
        if target.exists():
            self._quarantine(target, fingerprint)
        try:
            staging.replace(target)
        except FileExistsError:
            shutil.rmtree(staging, ignore_errors=True)
            raced = self.get(fingerprint, count_metrics=False)
            if raced is None:
                raise SandboxBuildError("ARTIFACT_PUBLISH_RACE", "Concurrent artifact publish was invalid")
            return raced
        self.metrics.publishes += 1
        self._record_access(fingerprint)
        return CachedArtifact(target, target / "environment.tar.gz", manifest)

    def discard_staging(self, staging: Path) -> None:
        try:
            staging.resolve().relative_to(self.staging)
        except ValueError as exc:
            raise ValueError("Refusing to remove staging outside cache root") from exc
        shutil.rmtree(staging, ignore_errors=True)

    def collect_garbage(self, *, pinned: set[str] | None = None) -> tuple[str, ...]:
        pinned = pinned or set()
        now = int(self.clock())
        records: list[tuple[int, int, str, Path]] = []
        for directory in self.objects.iterdir():
            if not directory.is_dir():
                continue
            manifest_path = directory / "manifest.json"
            try:
                manifest = ArtifactManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
                size = sum(item.stat().st_size for item in directory.rglob("*") if item.is_file())
                access_path = self.access / f"{manifest.fingerprint}.txt"
                try:
                    last_used = int(access_path.read_text(encoding="ascii"))
                except (OSError, ValueError):
                    last_used = manifest.last_used_at_epoch
                records.append((last_used, size, manifest.fingerprint, directory))
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                self._quarantine(directory, directory.name)
                self.metrics.corruptions += 1
        removed: list[str] = []
        total = sum(size for _, size, _, _ in records)
        for last_used, size, fingerprint, directory in sorted(records):
            expired = now - last_used > self.policy.ttl_seconds
            over_quota = total > self.policy.quota_bytes
            if fingerprint in pinned or (not expired and not over_quota):
                continue
            shutil.rmtree(directory)
            (self.access / f"{fingerprint}.txt").unlink(missing_ok=True)
            removed.append(fingerprint)
            total -= size
            self.metrics.evictions += 1
        return tuple(removed)

    def _record_access(self, fingerprint: str) -> None:
        path = self.access / f"{fingerprint}.txt"
        temporary = self.access / f".{fingerprint}-{uuid.uuid4().hex}.tmp"
        temporary.write_text(str(int(self.clock())), encoding="ascii")
        temporary.replace(path)

    def _quarantine(self, directory: Path, fingerprint: str) -> None:
        if not directory.exists():
            return
        destination = self.quarantine / f"{fingerprint}-{uuid.uuid4().hex}"
        try:
            directory.replace(destination)
        except OSError:
            shutil.rmtree(directory, ignore_errors=True)


class ProjectResolver(Protocol):
    def resolve(self, project_root: Path, plan: DependencyPlan, venv_dir: Path, *, network_allowed: bool) -> None: ...

    def check(self, venv_dir: Path) -> None: ...

    def inventory(self, venv_dir: Path) -> tuple[PackageRecord, ...]: ...


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    maximum_attempts: int = 3
    base_delay_seconds: float = 0.25
    maximum_delay_seconds: float = 5.0
    deadline_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.maximum_attempts < 1:
            raise ValueError("maximum_attempts must be positive")
        if min(self.base_delay_seconds, self.maximum_delay_seconds, self.deadline_seconds) < 0:
            raise ValueError("retry delays and deadline cannot be negative")


class UvProjectResolver:
    """Resolve a DependencyPlan into a venv without arbitrary shell input."""

    def __init__(self, *, uv: str = "uv", poetry: str = "poetry", index_urls=None, runner=None):
        self.uv = uv
        self.poetry = poetry
        self.index_urls = dict(index_urls or {})
        self.runner = runner or subprocess.run

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path,
        network_allowed: bool,
        sources: tuple[str, ...] = (),
        extra_environment: dict[str, str] | None = None,
    ) -> str:
        environment = os.environ.copy()
        environment["PROMPTOPT_NETWORK_PHASE"] = "resolve" if network_allowed else "disabled"
        environment.update(extra_environment or {})
        try:
            completed = self.runner(
                command,
                cwd=cwd,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=900,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            diagnostic = classify_resolver_failure("dependency resolution timed out")
            raise SandboxBuildError(
                diagnostic.error_code,
                "Dependency resolver exceeded its command deadline",
                retryable=diagnostic.retryable,
                diagnostic=diagnostic,
                sources=sources,
            ) from exc
        except OSError as exc:
            diagnostic = classify_resolver_failure(str(exc))
            raise SandboxBuildError(
                diagnostic.error_code,
                "Dependency resolver process could not be started",
                retryable=diagnostic.retryable,
                diagnostic=diagnostic,
                sources=sources,
            ) from exc
        if completed.returncode:
            output = "\n".join(
                part for part in (completed.stdout or "", getattr(completed, "stderr", "") or "") if part
            )[-10 * 1024 * 1024 :]
            for secret in (extra_environment or {}).values():
                if secret:
                    output = output.replace(secret, "<redacted-package-index>")
            output = redact_sensitive_text(output)
            diagnostic = classify_resolver_failure(output)
            raise SandboxBuildError(
                diagnostic.error_code,
                output or f"Command failed with exit code {completed.returncode}",
                retryable=diagnostic.retryable,
                diagnostic=diagnostic,
                sources=sources,
            )
        return completed.stdout or ""

    def resolve(self, project_root: Path, plan: DependencyPlan, venv_dir: Path, *, network_allowed: bool) -> None:
        if not network_allowed:
            raise SandboxBuildError("BUILD_NETWORK_POLICY", "Dependency resolution requires build-stage network policy")
        sources = tuple(item for item in (plan.manifest, plan.lock_file) if item)
        self._run(
            [self.uv, "venv", "--python", sys.executable, str(venv_dir)],
            cwd=project_root,
            network_allowed=False,
            sources=sources,
        )
        python = _venv_python(venv_dir)
        if plan.source == DependencySource.NONE:
            return
        requirements = project_root / (plan.manifest or "")
        if plan.source == DependencySource.UV_LOCK:
            exported = venv_dir.parent / "locked-requirements.txt"
            command = [self.uv, "export", "--frozen", "--no-emit-project", "--format", "requirements-txt"]
            for group in plan.groups:
                command.extend(["--group", group])
            for extra in plan.extras:
                command.extend(["--extra", extra])
            command.extend(["--output-file", str(exported)])
            self._run(command, cwd=project_root, network_allowed=False, sources=sources)
            requirements = exported
        elif plan.source == DependencySource.POETRY_LOCK:
            exported = venv_dir.parent / "locked-requirements.txt"
            command = [self.poetry, "export", "--without-hashes", "--output", str(exported)]
            if plan.groups:
                command.extend(["--with", ",".join(plan.groups)])
            if plan.extras:
                command.extend(["--extras", " ".join(plan.extras)])
            self._run(command, cwd=project_root, network_allowed=False, sources=sources)
            requirements = exported
        elif plan.source in {DependencySource.PYPROJECT, DependencySource.SETUP_CFG, DependencySource.SETUP_PY}:
            generated = venv_dir.parent / "declared-requirements.txt"
            generated.write_text("".join(f"{item}\n" for item in plan.declared_requirements), encoding="utf-8")
            requirements = generated
        command = [self.uv, "pip", "install", "--python", str(python), "-r", str(requirements)]
        missing_refs = tuple(reference for reference in plan.package_index_refs if reference not in self.index_urls)
        if missing_refs:
            raise SandboxBuildError(
                "PACKAGE_INDEX_NOT_CONFIGURED",
                "A selected package index reference is not configured in the builder",
                sources=missing_refs,
            )
        index_environment: dict[str, str] = {}
        selected_indexes = [self.index_urls[reference] for reference in plan.package_index_refs]
        if selected_indexes:
            index_environment["UV_INDEX_URL"] = selected_indexes[0]
        if len(selected_indexes) > 1:
            index_environment["UV_EXTRA_INDEX_URL"] = " ".join(selected_indexes[1:])
        self._run(
            command,
            cwd=project_root,
            network_allowed=True,
            sources=sources,
            extra_environment=index_environment,
        )

    def check(self, venv_dir: Path) -> None:
        self._run(
            [self.uv, "pip", "check", "--python", str(_venv_python(venv_dir))],
            cwd=venv_dir.parent,
            network_allowed=False,
        )

    def inventory(self, venv_dir: Path) -> tuple[PackageRecord, ...]:
        output = self._run(
            [self.uv, "pip", "list", "--python", str(_venv_python(venv_dir)), "--format", "json"],
            cwd=venv_dir.parent,
            network_allowed=False,
        )
        try:
            packages = json.loads(output)
            return tuple(
                sorted(
                    (PackageRecord(item["name"].casefold(), item["version"]) for item in packages),
                    key=lambda item: item.name,
                )
            )
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise SandboxBuildError("PACKAGE_INVENTORY_INVALID", "Resolver returned invalid package inventory") from exc


class EnvironmentArtifactBuilder:
    def __init__(
        self,
        cache: FileArtifactCache,
        resolver: ProjectResolver,
        *,
        retry_policy: RetryPolicy | None = None,
        sleep=time.sleep,
        random_source=random.random,
        clock=time.time,
    ):
        self.cache = cache
        self.resolver = resolver
        self.retry_policy = retry_policy or RetryPolicy()
        self.sleep = sleep
        self.random_source = random_source
        self.clock = clock

    def build(
        self,
        project_root: Path,
        plan: DependencyPlan,
        image: ImageIdentity,
        runner: RunnerIdentity,
    ) -> CachedArtifact:
        project_root = project_root.resolve()
        if not project_root.is_dir():
            raise SandboxBuildError("PROJECT_ROOT_NOT_FOUND", "Project root does not exist")
        if plan.python.python_version != image.python_minor:
            raise SandboxBuildError(
                "INCOMPATIBLE_PYTHON",
                f"Dependency plan requests Python {plan.python.python_version}, image provides {image.python_minor}",
            )
        fingerprint = environment_fingerprint(plan, image, runner)
        cached = self.cache.get(fingerprint)
        if cached is not None:
            return cached
        with self.cache.acquire(fingerprint):
            cached = self.cache.get(fingerprint, count_metrics=False)
            if cached is not None:
                return cached
            staging = self.cache.create_staging(fingerprint)
            started = self.clock()
            try:
                venv_dir = staging / "venv"
                self._resolve_with_retry(project_root, plan, venv_dir)
                self.resolver.check(venv_dir)
                inventory = tuple(sorted(self.resolver.inventory(venv_dir), key=lambda item: (item.name, item.version)))
                inventory_sha256 = _inventory_sha256(inventory)
                archive = staging / "environment.tar.gz"
                _archive_venv(venv_dir, archive)
                now = int(self.clock())
                manifest = ArtifactManifest(
                    fingerprint=fingerprint,
                    artifact_sha256=_sha256_file(archive),
                    artifact_size=archive.stat().st_size,
                    dependency_plan_fingerprint=plan.fingerprint,
                    image=image,
                    runner=runner,
                    inventory=inventory,
                    inventory_sha256=inventory_sha256,
                    created_at_epoch=now,
                    last_used_at_epoch=now,
                )
                artifact = self.cache.publish(fingerprint, staging, manifest)
                return artifact
            except Exception:
                self.cache.discard_staging(staging)
                raise
            finally:
                self.cache.metrics.build_duration_seconds.append(max(0.0, self.clock() - started))

    def _resolve_with_retry(self, project_root: Path, plan: DependencyPlan, venv_dir: Path) -> None:
        policy = self.retry_policy
        started = self.clock()
        for attempt in range(1, policy.maximum_attempts + 1):
            if attempt > 1:
                shutil.rmtree(venv_dir, ignore_errors=True)
                for generated in ("declared-requirements.txt", "locked-requirements.txt"):
                    (venv_dir.parent / generated).unlink(missing_ok=True)
            try:
                self.resolver.resolve(project_root, plan, venv_dir, network_allowed=True)
                return
            except SandboxBuildError as exc:
                elapsed = self.clock() - started
                if not exc.retryable or attempt >= policy.maximum_attempts:
                    raise
                delay = min(policy.maximum_delay_seconds, policy.base_delay_seconds * (2 ** (attempt - 1)))
                delay *= 0.5 + self.random_source()
                if elapsed + delay > policy.deadline_seconds:
                    raise SandboxBuildError(
                        "DEPENDENCY_RETRY_DEADLINE",
                        "Dependency resolution retry deadline exceeded",
                        retryable=True,
                        diagnostic=exc.diagnostic,
                    ) from exc
                self.cache.metrics.retry_count += 1
                self.sleep(delay)


def environment_fingerprint(plan: DependencyPlan, image: ImageIdentity, runner: RunnerIdentity) -> str:
    return _identity_fingerprint(plan.fingerprint, image, runner)


def _identity_fingerprint(
    dependency_plan_fingerprint: str,
    image: ImageIdentity,
    runner: RunnerIdentity,
) -> str:
    payload = {
        "artifact_manifest_version": ARTIFACT_MANIFEST_VERSION,
        "dependency_plan_fingerprint": dependency_plan_fingerprint,
        "image": asdict(image),
        "runner": asdict(runner),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _validate_fingerprint(fingerprint: str) -> None:
    if len(fingerprint) != 64:
        raise ValueError("fingerprint must be a lowercase SHA-256 digest")
    try:
        int(fingerprint, 16)
    except ValueError as exc:
        raise ValueError("fingerprint must be a lowercase SHA-256 digest") from exc
    if fingerprint != fingerprint.lower():
        raise ValueError("fingerprint must be a lowercase SHA-256 digest")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_sha256(inventory: tuple[PackageRecord, ...]) -> str:
    payload = [asdict(item) for item in inventory]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _venv_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _archive_venv(venv_dir: Path, destination: Path) -> None:
    if not venv_dir.is_dir() or not _venv_python(venv_dir).is_file():
        raise SandboxBuildError("ENVIRONMENT_NOT_USABLE", "Resolver did not create a usable Python environment")
    with tarfile.open(destination, "w:gz", dereference=False) as archive:
        archive.add(venv_dir, arcname="venv", recursive=True)
