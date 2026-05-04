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

# Service account management for CI is split into two bindings to avoid
# granting project-wide ``serviceAccountAdmin``:
#
#  1) ``serviceAccountCreator`` is unconditional because project-level
#     ``iam.serviceAccounts.create`` cannot be constrained by a
#     resource-name IAM condition (the target is the project, not the
#     new SA). This still does not let CI modify existing SAs.
#
#  2) ``serviceAccountAdmin`` is applied conditionally, restricted to
#     the specific SAs this Terraform config manages (github-deployer,
#     audio-generator, audio-scheduler, appspot). This closes the
#     "compromised CI → setIamPolicy on appspot → full project
#     takeover" path that the previous unscoped grant exposed.
resource "google_project_iam_member" "github_deployer_service_account_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountCreator"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

resource "google_project_iam_member" "github_deployer_service_account_admin_scoped" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${google_service_account.github_deployer.email}"

  condition {
    title       = "Terraform-managed SAs only"
    description = "Limits serviceAccountAdmin to SAs defined in this Terraform config. Uses endsWith so it matches both project-id and project-number resource-name forms emitted by IAM."
    expression  = <<-EOT
      resource.name.endsWith("/serviceAccounts/audio-generator@${var.project_id}.iam.gserviceaccount.com") ||
      resource.name.endsWith("/serviceAccounts/audio-scheduler@${var.project_id}.iam.gserviceaccount.com") ||
      resource.name.endsWith("/serviceAccounts/github-deployer@${var.project_id}.iam.gserviceaccount.com") ||
      resource.name.endsWith("/serviceAccounts/${local.appspot_email}")
    EOT
  }

  depends_on = [
    google_project_service.enabled,
    google_service_account.github_deployer,
  ]
}

# Terraform only reads Workload Identity pools/providers (wif.tf) during
# refresh — no create/update in the steady state — so viewer suffices.
# If wif.tf ever manages pool/provider mutations from CI again, bump
# this back to ``roles/iam.workloadIdentityPoolAdmin``.
resource "google_project_iam_member" "github_deployer_workload_identity_pool_viewer" {
  project = var.project_id
  role    = "roles/iam.workloadIdentityPoolViewer"
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
