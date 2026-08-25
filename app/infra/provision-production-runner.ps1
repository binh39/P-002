param(
    [string]$ProjectId = "project-7df9f963-9fe0-4b76-b3d",
    [string]$ModelProjectId = "project-a2f7084e-90ac-4bfc-84b",
    [string]$Region = "asia-southeast1",
    [string]$Bucket = "project-7df9f963-9fe0-4b76-b3d-promptopt-sources",
    [string]$Queue = "promptopt-baseline"
)

Write-Warning "This compatibility script provisions only runner-specific resources. For a new project, run app/infra/provision-production.ps1 first."

$ErrorActionPreference = "Stop"
$RunnerAccountName = "promptopt-runner"
$RunnerAccount = "$RunnerAccountName@$ProjectId.iam.gserviceaccount.com"
$RuntimeAccountName = "promptopt-runtime"
$RuntimeAccount = "$RuntimeAccountName@$ProjectId.iam.gserviceaccount.com"
$ApiAccount = "promptopt-api@$ProjectId.iam.gserviceaccount.com"
$DeployAccount = "github-backend-deploy@$ProjectId.iam.gserviceaccount.com"
$RunnerObjectRole = "promptoptRunnerObjectIO"
$RunnerObjectRoleResource = "projects/$ProjectId/roles/$RunnerObjectRole"
$RoleFile = Join-Path $PSScriptRoot "runner-object-role.yaml"
$ApiOperationRole = "promptoptJobOperationPoller"
$ApiOperationRoleResource = "projects/$ProjectId/roles/$ApiOperationRole"
$ApiOperationRoleFile = Join-Path $PSScriptRoot "api-job-operation-role.yaml"
$ProviderSecretRole = "promptoptProviderSecretManager"
$ProviderSecretRoleResource = "projects/$ProjectId/roles/$ProviderSecretRole"
$ProviderSecretRoleFile = Join-Path $PSScriptRoot "provider-secret-role.yaml"

function Invoke-Gcloud {
    & gcloud @args
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud command failed: gcloud $($args -join ' ')"
    }
}

function Test-GcloudResource {
    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & gcloud @args *> $null
    $Exists = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $PreviousErrorActionPreference
    return $Exists
}

Invoke-Gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudtasks.googleapis.com secretmanager.googleapis.com --project $ProjectId
Invoke-Gcloud services enable aiplatform.googleapis.com --project $ModelProjectId

if (-not (Test-GcloudResource iam service-accounts describe $RunnerAccount --project $ProjectId)) {
    Invoke-Gcloud iam service-accounts create $RunnerAccountName --project $ProjectId --display-name "PromptOpt isolated runner"
}
if (-not (Test-GcloudResource iam service-accounts describe $RuntimeAccount --project $ProjectId)) {
    Invoke-Gcloud iam service-accounts create $RuntimeAccountName --project $ProjectId --display-name "PromptOpt untrusted project runtime"
}

if (-not (Test-GcloudResource iam roles describe $RunnerObjectRole --project $ProjectId)) {
    Invoke-Gcloud iam roles create $RunnerObjectRole --project $ProjectId --file $RoleFile
}
else {
    Invoke-Gcloud iam roles update $RunnerObjectRole --project $ProjectId --file $RoleFile
}

if (-not (Test-GcloudResource iam roles describe $ApiOperationRole --project $ProjectId)) {
    Invoke-Gcloud iam roles create $ApiOperationRole --project $ProjectId --file $ApiOperationRoleFile
}
else {
    Invoke-Gcloud iam roles update $ApiOperationRole --project $ProjectId --file $ApiOperationRoleFile
}
if (-not (Test-GcloudResource iam roles describe $ProviderSecretRole --project $ProjectId)) {
    Invoke-Gcloud iam roles create $ProviderSecretRole --project $ProjectId --file $ProviderSecretRoleFile
}
else {
    Invoke-Gcloud iam roles update $ProviderSecretRole --project $ProjectId --file $ProviderSecretRoleFile
}

$PrefixCondition = "expression=resource.name.startsWith('projects/_/buckets/$Bucket/objects/runner-jobs/'),title=PromptOptRunnerJobPrefix,description=Restrict runner access to opaque execution objects"
Invoke-Gcloud storage buckets add-iam-policy-binding "gs://$Bucket" --member "serviceAccount:$RunnerAccount" --role $RunnerObjectRoleResource --condition $PrefixCondition
Invoke-Gcloud storage buckets add-iam-policy-binding "gs://$Bucket" --member "serviceAccount:$RuntimeAccount" --role $RunnerObjectRoleResource --condition $PrefixCondition
Invoke-Gcloud projects add-iam-policy-binding $ModelProjectId --member "serviceAccount:$RunnerAccount" --role roles/aiplatform.user --condition None
Invoke-Gcloud projects add-iam-policy-binding $ModelProjectId --member "serviceAccount:$RunnerAccount" --role roles/serviceusage.serviceUsageConsumer --condition None
Invoke-Gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$ApiAccount" --role $ApiOperationRoleResource --condition None
Invoke-Gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$ApiAccount" --role $ProviderSecretRoleResource --condition None
Invoke-Gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$RunnerAccount" --role roles/secretmanager.secretAccessor --condition None
Invoke-Gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$ApiAccount" --role roles/logging.viewer --condition None
Invoke-Gcloud iam service-accounts add-iam-policy-binding $RunnerAccount --project $ProjectId --member "serviceAccount:$DeployAccount" --role roles/iam.serviceAccountUser
Invoke-Gcloud iam service-accounts add-iam-policy-binding $RuntimeAccount --project $ProjectId --member "serviceAccount:$DeployAccount" --role roles/iam.serviceAccountUser

if (-not (Test-GcloudResource tasks queues describe $Queue --location $Region --project $ProjectId)) {
    Invoke-Gcloud tasks queues create $Queue --location $Region --project $ProjectId --max-concurrent-dispatches 1 --max-dispatches-per-second 1 --max-attempts 3 --max-retry-duration 3600s
}
else {
    Invoke-Gcloud tasks queues update $Queue --location $Region --project $ProjectId --max-concurrent-dispatches 1 --max-dispatches-per-second 1 --max-attempts 3 --max-retry-duration 3600s
}

Write-Host "Runner prerequisites are ready. Merge the deployment workflow to create/update the Cloud Run Job."
