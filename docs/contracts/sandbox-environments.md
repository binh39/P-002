# Optimizer sandbox environments file

`--sandbox-environments-file` activates the Phase 5 execution path. The JSON
object must have exactly one entry for every project present in the dataset.
Paths are resolved relative to the JSON file.

```json
{
  "uploaded-project": {
    "image_digest": "sha256:<64 lowercase hex characters>",
    "artifact_archive": "artifacts/environment.tar.gz",
    "artifact_manifest": "artifacts/manifest.json",
    "source_root": "project",
    "source_directory": "src/package_name",
    "requested_python": "3.12",
    "runner_profile": "project_native"
  }
}
```

`runner_profile` is either `project_native` or `sandbox_managed` and must match
the runner identity stored in the artifact manifest. The manifest image digest
must match `image_digest`; the optimizer refuses to start the execution when
they differ.

When this file is supplied:

- CoverUp still runs in the optimizer environment only to generate tests;
- every diagnostic, baseline and candidate pytest/coverage execution uses a
  versioned `RunSpec` and the project's immutable environment artifact;
- generated tests are mounted separately from the read-only project source;
- evaluation cache and reports include the environment fingerprint;
- paired scoring rejects a baseline/candidate fingerprint mismatch.

Omitting this option retains the legacy local evaluator for existing developer
benchmarks. Uploaded-project production jobs should always supply the file.
