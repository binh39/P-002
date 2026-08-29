from pathlib import Path


def test_production_deploy_publishes_workers_before_the_shared_coordinator():
    workflow = Path(".github/workflows/backend-deploy.yml").read_text(encoding="utf-8")

    sample_worker = workflow.index("- name: Deploy bundled-sample evaluation worker")
    runtime_workers = workflow.index("- name: Deploy isolated runtime preparation job")
    runtime_factory = workflow.index("- name: Deploy trusted runtime image factory")
    coordinator = workflow.index("- name: Deploy isolated GEPA coordinator")
    api = workflow.index("- name: Deploy Cloud Run")
    assert sample_worker < runtime_workers < runtime_factory < coordinator < api

    runtime_step = workflow[runtime_workers:runtime_factory]
    assert runtime_step.index('gcloud run jobs deploy "$VERSIONED_EVALUATION_JOB"') < runtime_step.index(
        'gcloud run jobs deploy "$JOB_NAME"'
    )


def test_production_workers_and_coordinator_are_pinned_by_registry_digest():
    workflow = Path(".github/workflows/backend-deploy.yml").read_text(encoding="utf-8")

    assert 'GEPA_IMMUTABLE_IMAGE="${GEPA_IMAGE%:*}@${GEPA_DIGEST}"' in workflow
    assert 'IMMUTABLE_RUNTIME_IMAGE="${RUNTIME_IMAGE%:*}@${RUNTIME_DIGEST}"' in workflow
    assert 'JOB_VERSION="${GITHUB_SHA:0:20}"' in workflow
    assert "GITHUB_SHA:0:8" not in workflow
    for version in ("3.10", "3.11", "3.12", "3.13"):
        assert version in workflow


def test_production_deploy_includes_trusted_project_image_factory():
    workflow = Path(".github/workflows/backend-deploy.yml").read_text(encoding="utf-8")

    assert 'if: env.DEPLOY_RUNTIME_FACTORY == \'true\'' in workflow
    assert "cloud/Dockerfile.runtime-factory" in workflow
    assert 'gcloud run jobs deploy "$RUNTIME_FACTORY_JOB"' in workflow
    assert '--service-account "$RUNTIME_FACTORY_SERVICE_ACCOUNT"' in workflow
    assert "cloud.runtime_image_factory" in workflow


def test_production_deploy_defaults_to_generic_workers_without_factory_build():
    workflow = Path(".github/workflows/backend-deploy.yml").read_text(encoding="utf-8")

    assert 'DEPLOY_RUNTIME_FACTORY: "false"' in workflow
    build_step = workflow[workflow.index("- name: Build and push images") : workflow.index("- name: Build and push legacy runtime")]
    assert "Dockerfile.runtime-factory" not in build_step
    assert 'docker push "$FACTORY_IMAGE"' not in build_step


def test_provisioning_keeps_build_privileges_out_of_untrusted_preparer():
    provisioning = Path("app/infra/provision-production.ps1").read_text(encoding="utf-8")

    assert 'RuntimeFactoryAccountName = "promptopt-runtime-factory"' in provisioning
    assert 'RuntimeBuilderAccountName = "promptopt-runtime-builder"' in provisioning
    assert '"serviceAccount:$RuntimeFactoryAccount" "roles/cloudbuild.builds.editor"' in provisioning
    assert '"serviceAccount:$RuntimeFactoryAccount" "roles/run.admin"' in provisioning
    assert '"serviceAccount:$RuntimeBuilderAccount" "roles/logging.logWriter"' in provisioning
    assert '"serviceAccount:$RuntimeAccount" "roles/cloudbuild.builds.editor"' not in provisioning


def test_dev_runtime_mode_defaults_to_generic_worker_bundle():
    environment = Path("app/infra/cloud-run-env.dev.yaml").read_text(encoding="utf-8")

    assert "RUNTIME_PROJECT_IMAGE_MODE: generic_worker_bundle" in environment
