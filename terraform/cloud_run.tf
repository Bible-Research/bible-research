resource "google_cloud_run_v2_service" "bible_research" {
  name     = "bible-research"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.dockerhub_proxy.repository_id}/${var.dockerhub_username}/bible-research:${var.image_tag}"

      ports {
        container_port = 8080
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
    }
  }

  depends_on = [
    google_project_service.enabled,
    google_artifact_registry_repository.dockerhub_proxy,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.bible_research.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
