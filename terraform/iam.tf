locals {
  appspot_email = "${var.project_id}@appspot.gserviceaccount.com"
}

resource "google_service_account" "github_deployer" {
  account_id   = "github-deployer"
  display_name = "github-deployer"
  description  = "Account that manages deployments"
  project      = var.project_id

  depends_on = [google_project_service.enabled]
}

# Existing bindings (addresses must match remote state for zero-drift plan).
resource "google_project_iam_member" "github_deployer_appengine_app_admin" {
  project = var.project_id
  role    = "roles/appengine.appAdmin"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_project_iam_member" "github_deployer_cloudbuild_editor" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_project_iam_member" "github_deployer_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_project_iam_member" "github_deployer_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_project_iam_member" "github_deployer_artifactregistry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_project_iam_member" "github_deployer_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

# secretAccessor alone does not include secretmanager.secrets.get; Terraform
# data.google_secret_manager_secret needs metadata reads for plan/apply.
resource "google_project_iam_member" "github_deployer_secret_viewer" {
  project = var.project_id
  role    = "roles/secretmanager.viewer"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

# Enables google_project_service (API activation) in CI.
resource "google_project_iam_member" "github_deployer_service_usage_admin" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageAdmin"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_project_iam_member" "github_deployer_logging_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_project_iam_member" "github_deployer_project_iam_admin" {
  project = var.project_id
  role    = "roles/resourcemanager.projectIamAdmin"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_project_iam_member" "appspot_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${local.appspot_email}"

  depends_on = [google_project_service.enabled]
}

resource "google_service_account_iam_member" "github_deployer_act_as_runtime" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${local.appspot_email}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_service_account_iam_member" "appspot_self_token_creator" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${local.appspot_email}"
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${local.appspot_email}"
}
