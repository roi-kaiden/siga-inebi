# Keyless continuous deployment from GitHub Actions through Workload Identity Federation.
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "${local.name}-github"
  display_name              = "SIGA INEBI QA GitHub"
  description               = "GitHub Actions deploys to QA"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions"
  display_name                       = "GitHub Actions"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  # Only this repository on the deploy branch; PRs and forks get no token.
  attribute_condition = "assertion.repository == \"${var.github_repository}\" && assertion.ref == \"refs/heads/${var.deploy_branch}\""
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "deployer" {
  account_id   = "${local.name}-deployer"
  display_name = "SIGA INEBI QA GitHub Actions deployer"
  depends_on   = [google_project_service.apis]
}

resource "google_artifact_registry_repository_iam_member" "deployer_push" {
  project    = var.project_id
  location   = google_artifact_registry_repository.qa.location
  repository = google_artifact_registry_repository.qa.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

# gcloud waits on project-scoped Cloud Run operations, so resource-level grants are not enough.
resource "google_project_iam_member" "deployer_run" {
  project    = var.project_id
  role       = "roles/run.developer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
  depends_on = [google_project_service.apis]
}

# Deploy revisions and job executions that run as the runtime account, nothing else.
resource "google_service_account_iam_member" "deployer_act_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "github_impersonate_deployer" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}
