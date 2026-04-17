# App Engine Standard created this repository; we track it to avoid drift.
resource "google_artifact_registry_repository" "gae_standard" {
  # App Engine Standard uses the regional repo in the app region (not var.region / tfvars).
  location      = "europe-west3"
  repository_id = "gae-standard"
  description   = "Repository to store images related to App Engine Standard deployments."
  format        = "DOCKER"

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.enabled]
}
