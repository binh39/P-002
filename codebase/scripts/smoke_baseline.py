import asyncio
import io
import zipfile
from pathlib import Path

from dotenv import load_dotenv

from src.modules.experiments.executor import DockerCoverUpExecutor
from src.modules.experiments.prompts import baseline_prompt


def fixture_archive() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        bundle.writestr(
            "calculator/__init__.py",
            "def classify(value):\n    if value > 0:\n        return 'positive'\n    return 'non-positive'\n",
        )
    return output.getvalue()


async def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    executor = DockerCoverUpExecutor(
        "promptopt-coverup-runner:local",
        timeout_seconds=300,
        memory_mb=2048,
        cpu=1,
        max_files=20,
        max_uncompressed_bytes=1024 * 1024,
        network_mode="bridge",
    )
    result = await executor.execute(fixture_archive(), "calculator", ["classify"], baseline_prompt())
    print(
        {
            "score": result.coverage_score,
            "statement": result.statement_coverage,
            "branch": result.branch_coverage,
            "artifacts": sorted(result.artifacts),
        }
    )
    if result.coverage_score == 0:
        for name in ("coverup.stdout.log", "coverup.log"):
            print(f"--- {name} ---")
            print(result.artifacts.get(name, b"").decode("utf-8", errors="replace")[-4000:])


if __name__ == "__main__":
    asyncio.run(main())
