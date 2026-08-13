param(
    [string]$ProjectId = "project-7df9f963-9fe0-4b76-b3d",
    [string]$ModelProjectId = "vinbuildphase",
    [string]$Region = "asia-southeast1",
    [string]$Repository = "promptopt",
    [string]$Bucket = "project-7df9f963-9fe0-4b76-b3d-promptopt-sources",
    [string]$GitHubRepository = "binh39/P-002",
    [string]$WorkloadIdentityPool = "github-actions",
    [string]$WorkloadIdentityProvider = "p002-main"
)

$ErrorActionPreference = "Stop"

$ApiAccountName = "promptopt-api"
$RunnerAccountName = "promptopt-runner"
$BackendDeployAccountName = "github-backend-deploy"
$FrontendDeployAccountName = "github-frontend-deploy"
$ApiAccount = "$ApiAccountName@$ProjectId.iam.gserviceaccount.com"
$RunnerAccount = "$RunnerAccountName@$ProjectId.iam.gserviceaccount.com"
$BackendDeployAccount = "$BackendDeployAccountName@$ProjectId.iam.gserviceaccount.com"
$FrontendDeployAccount = "$FrontendDeployAccountName@$ProjectId.iam.gserviceaccount.com"
$RunnerObjectRole = "promptoptRunnerObjectIO"
$RunnerObjectRoleResource = "projects/$ProjectId/roles/$RunnerObjectRole"
$ApiOperationRole = "promptoptJobOperationPoller"
$ApiOperationRoleResource = "projects/$ProjectId/roles/$ApiOperationRole"
$RunnerObjectRoleFile = Join-Path $PSScriptRoot "runner-object-role.yaml"
$ApiOperationRoleFile = Join-Path $PSScriptRoot "api-job-operation-role.yaml"
$StorageCorsFile = Join-Path $PSScriptRoot "storage-cors.json"

function Invoke-Gcloud {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    & gcloud @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "gcloud command failed: gcloud $($Arguments -join ' ')"
    }
}

function Test-GcloudResource {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & gcloud @Arguments *> $null
    $Exists = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $PreviousErrorActionPreference
    return $Exists
}

function Add-ProjectRole {
    param([string]$Member, [string]$Role)

    Invoke-Gcloud projects add-iam-policy-binding $ProjectId `
        --member $Member `
        --role $Role `
        --condition=None `
        --quiet
}

function Ensure-ServiceAccount {
    param([string]$Name, [string]$DisplayName)

    $Email = "$Name@$ProjectId.iam.gserviceaccount.com"
    if (-not (Test-GcloudResource iam service-accounts describe $Email --project $ProjectId)) {
        Invoke-Gcloud iam service-accounts create $Name `
            --project $ProjectId `
            --display-name $DisplayName
    }
}

Write-Host "[1/10] Verifying project and billing..."
Invoke-Gcloud projects describe $ProjectId --format="value(projectId)"
$BillingEnabled = (& gcloud billing projects describe $ProjectId --format="value(billingEnabled)").Trim()
if ($LASTEXITCODE -ne 0 -or $BillingEnabled -ne "True") {
    throw "Billing must be enabled for project $ProjectId before provisioning."
}

Write-Host "[2/10] Enabling Google Cloud APIs..."
Invoke-Gcloud services enable `
    artifactregistry.googleapis.com `
    cloudtasks.googleapis.com `
    datastore.googleapis.com `
    firebase.googleapis.com `
    firebasehosting.googleapis.com `
    firestore.googleapis.com `
    iam.googleapis.com `
    iamcredentials.googleapis.com `
    identitytoolkit.googleapis.com `
    run.googleapis.com `
    serviceusage.googleapis.com `
    storage.googleapis.com `
    sts.googleapis.com `
    --project $ProjectId
Invoke-Gcloud services enable aiplatform.googleapis.com --project $ModelProjectId

Write-Host "[3/10] Creating service accounts..."
Ensure-ServiceAccount $ApiAccountName "PromptOpt API runtime"
Ensure-ServiceAccount $RunnerAccountName "PromptOpt isolated runner"
Ensure-ServiceAccount $BackendDeployAccountName "GitHub backend production deploy"
Ensure-ServiceAccount $FrontendDeployAccountName "GitHub frontend production deploy"

Write-Host "[4/10] Creating Artifact Registry and private storage..."
if (-not (Test-GcloudResource artifacts repositories describe $Repository --project $ProjectId --location $Region)) {
    Invoke-Gcloud artifacts repositories create $Repository `
        --project $ProjectId `
        --location $Region `
        --repository-format docker `
        --description "PromptOpt production container images"
}

if (-not (Test-GcloudResource storage buckets describe "gs://$Bucket" --project $ProjectId)) {
    Invoke-Gcloud storage buckets create "gs://$Bucket" `
        --project $ProjectId `
        --location $Region `
        --uniform-bucket-level-access `
        --public-access-prevention
}
Invoke-Gcloud storage buckets update "gs://$Bucket" --cors-file $StorageCorsFile

Write-Host "[5/10] Creating the default Firestore database..."
if (-not (Test-GcloudResource firestore databases describe --database="(default)" --project $ProjectId)) {
    Invoke-Gcloud firestore databases create `
        --database="(default)" `
        --location $Region `
        --type firestore-native `
        --project $ProjectId `
        --quiet
}

Write-Host "[6/10] Creating custom least-privilege roles..."
if (-not (Test-GcloudResource iam roles describe $RunnerObjectRole --project $ProjectId)) {
    Invoke-Gcloud iam roles create $RunnerObjectRole --project $ProjectId --file $RunnerObjectRoleFile --quiet
}
else {
    Invoke-Gcloud iam roles update $RunnerObjectRole --project $ProjectId --file $RunnerObjectRoleFile --quiet
}
if (-not (Test-GcloudResource iam roles describe $ApiOperationRole --project $ProjectId)) {
    Invoke-Gcloud iam roles create $ApiOperationRole --project $ProjectId --file $ApiOperationRoleFile --quiet
}
else {
    Invoke-Gcloud iam roles update $ApiOperationRole --project $ProjectId --file $ApiOperationRoleFile --quiet
}

Write-Host "[7/10] Assigning runtime and deployment IAM..."
Add-ProjectRole "serviceAccount:$ApiAccount" "roles/cloudtasks.enqueuer"
Add-ProjectRole "serviceAccount:$ApiAccount" "roles/datastore.user"
Add-ProjectRole "serviceAccount:$ApiAccount" "roles/firebaseauth.viewer"
Add-ProjectRole "serviceAccount:$ApiAccount" $ApiOperationRoleResource
Invoke-Gcloud projects add-iam-policy-binding $ModelProjectId `
    --member "serviceAccount:$RunnerAccount" `
    --role roles/aiplatform.user `
    --condition=None `
    --quiet
Invoke-Gcloud projects add-iam-policy-binding $ModelProjectId `
    --member "serviceAccount:$RunnerAccount" `
    --role roles/serviceusage.serviceUsageConsumer `
    --condition=None `
    --quiet
Add-ProjectRole "serviceAccount:$BackendDeployAccount" "roles/run.admin"
Add-ProjectRole "serviceAccount:$BackendDeployAccount" "roles/serviceusage.serviceUsageConsumer"
Add-ProjectRole "serviceAccount:$FrontendDeployAccount" "roles/firebasehosting.admin"
Add-ProjectRole "serviceAccount:$FrontendDeployAccount" "roles/run.viewer"

Invoke-Gcloud artifacts repositories add-iam-policy-binding $Repository `
    --project $ProjectId `
    --location $Region `
    --member "serviceAccount:$BackendDeployAccount" `
    --role roles/artifactregistry.writer `
    --quiet
Invoke-Gcloud storage buckets add-iam-policy-binding "gs://$Bucket" `
    --member "serviceAccount:$ApiAccount" `
    --role roles/storage.objectAdmin `
    --condition=None
$PrefixCondition = "expression=resource.name.startsWith('projects/_/buckets/$Bucket/objects/runner-jobs/'),title=PromptOptRunnerJobPrefix,description=Restrict runner access to opaque execution objects"
Invoke-Gcloud storage buckets add-iam-policy-binding "gs://$Bucket" `
    --member "serviceAccount:$RunnerAccount" `
    --role $RunnerObjectRoleResource `
    --condition $PrefixCondition

Invoke-Gcloud iam service-accounts add-iam-policy-binding $ApiAccount `
    --project $ProjectId `
    --member "serviceAccount:$ApiAccount" `
    --role roles/iam.serviceAccountUser
Invoke-Gcloud iam service-accounts add-iam-policy-binding $ApiAccount `
    --project $ProjectId `
    --member "serviceAccount:$ApiAccount" `
    --role roles/iam.serviceAccountTokenCreator
Invoke-Gcloud iam service-accounts add-iam-policy-binding $ApiAccount `
    --project $ProjectId `
    --member "serviceAccount:$BackendDeployAccount" `
    --role roles/iam.serviceAccountUser
Invoke-Gcloud iam service-accounts add-iam-policy-binding $RunnerAccount `
    --project $ProjectId `
    --member "serviceAccount:$BackendDeployAccount" `
    --role roles/iam.serviceAccountUser

Write-Host "[8/10] Creating Cloud Tasks queues..."
if (-not (Test-GcloudResource tasks queues describe promptopt-analysis --location $Region --project $ProjectId)) {
    Invoke-Gcloud tasks queues create promptopt-analysis `
        --location $Region `
        --project $ProjectId `
        --max-concurrent-dispatches 2 `
        --max-dispatches-per-second 2 `
        --max-attempts 5 `
        --min-backoff 10s `
        --max-backoff 60s
}
else {
    Invoke-Gcloud tasks queues update promptopt-analysis `
        --location $Region `
        --project $ProjectId `
        --max-concurrent-dispatches 2 `
        --max-dispatches-per-second 2 `
        --max-attempts 5 `
        --min-backoff 10s `
        --max-backoff 60s
}
if (-not (Test-GcloudResource tasks queues describe promptopt-baseline --location $Region --project $ProjectId)) {
    Invoke-Gcloud tasks queues create promptopt-baseline `
        --location $Region `
        --project $ProjectId `
        --max-concurrent-dispatches 1 `
        --max-dispatches-per-second 1 `
        --max-attempts 3 `
        --max-retry-duration 3600s
}
else {
    Invoke-Gcloud tasks queues update promptopt-baseline `
        --location $Region `
        --project $ProjectId `
        --max-concurrent-dispatches 1 `
        --max-dispatches-per-second 1 `
        --max-attempts 3 `
        --max-retry-duration 3600s
}

Write-Host "[9/10] Configuring GitHub Workload Identity Federation..."
if (-not (Test-GcloudResource iam workload-identity-pools describe $WorkloadIdentityPool --project $ProjectId --location global)) {
    Invoke-Gcloud iam workload-identity-pools create $WorkloadIdentityPool `
        --project $ProjectId `
        --location global `
        --display-name "GitHub Actions" `
        --description "OIDC identities for GitHub Actions"
}
if (-not (Test-GcloudResource iam workload-identity-pools providers describe $WorkloadIdentityProvider --workload-identity-pool $WorkloadIdentityPool --project $ProjectId --location global)) {
    Invoke-Gcloud iam workload-identity-pools providers create-oidc $WorkloadIdentityProvider `
        --project $ProjectId `
        --location global `
        --workload-identity-pool $WorkloadIdentityPool `
        --display-name "P-002 main deploy" `
        --description "Only $GitHubRepository main may federate" `
        --issuer-uri "https://token.actions.githubusercontent.com" `
        --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref,attribute.actor=assertion.actor" `
        --attribute-condition "assertion.repository == '$GitHubRepository' && assertion.ref == 'refs/heads/main'"
}

$ProjectNumber = (& gcloud projects describe $ProjectId --format="value(projectNumber)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $ProjectNumber) {
    throw "Could not resolve the project number for $ProjectId."
}
$GitHubPrincipal = "principalSet://iam.googleapis.com/projects/$ProjectNumber/locations/global/workloadIdentityPools/$WorkloadIdentityPool/attribute.repository/$GitHubRepository"
foreach ($DeployAccount in @($BackendDeployAccount, $FrontendDeployAccount)) {
    Invoke-Gcloud iam service-accounts add-iam-policy-binding $DeployAccount `
        --project $ProjectId `
        --member $GitHubPrincipal `
        --role roles/iam.workloadIdentityUser
}

Write-Host "[10/10] Verifying provisioned resources..."
Invoke-Gcloud artifacts repositories describe $Repository --project $ProjectId --location $Region --format="value(name)"
Invoke-Gcloud storage buckets describe "gs://$Bucket" --format="value(name)"
Invoke-Gcloud firestore databases describe --database="(default)" --project $ProjectId --format="value(name)"
Invoke-Gcloud tasks queues describe promptopt-analysis --location $Region --project $ProjectId --format="value(name)"
Invoke-Gcloud tasks queues describe promptopt-baseline --location $Region --project $ProjectId --format="value(name)"

Write-Host "Production infrastructure is ready for $ProjectId."
Write-Host "GitHub provider: projects/$ProjectNumber/locations/global/workloadIdentityPools/$WorkloadIdentityPool/providers/$WorkloadIdentityProvider"
Write-Host "Next: run the backend deployment workflow, then deploy Firebase Auth and the frontend."
