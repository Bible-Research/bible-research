resource "google_app_engine_application" "main" {
  project       = var.project_id
  location_id   = "europe-west3"
  database_type = "CLOUD_DATASTORE_COMPATIBILITY"

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.enabled]
}
