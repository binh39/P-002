# Dev Cloud runtime isolation fixtures

These deliberately small projects exercise the generic worker smoke gate:

- `project_py311` requires Python 3.11 and `packaging==24.2`.
- `project_py312` requires Python 3.12 and `packaging==25.0`.

The projects are zipped before upload. Their source archives and prepared venv
bundles are content-addressed by the runtime preparer; the fixtures are not
used by production datasets.
