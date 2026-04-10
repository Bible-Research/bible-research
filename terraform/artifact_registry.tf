resource "google_secret_manager_secret" "dockerhub_token" {
  secret_id = "dockerhub-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "dockerhub_token" {
  secret      = google_secret_manager_secret.dockerhub_token.id
  secret_data = var.dockerhub_token

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret_iam_member" "artifact_registry_dockerhub" {
  secret_id = google_secret_manager_secret.dockerhub_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-artifactregistry.iam.gserviceaccount.com"
}

resource "google_artifact_registry_repository" "dockerhub_proxy" {
  location      = var.region
  repository_id = "dockerhub-proxy"
  description   = "Remote repository proxying Docker Hub"
  format        = "DOCKER"
  mode          = "REMOTE_REPOSITORY"

  remote_repository_config {
    description = "Docker Hub"
    docker_repository {
      public_repository = "DOCKER_HUB"
    }
    upstream_credentials {
      username_password_credentials {
        username                = var.dockerhub_username
        password_secret_version = google_secret_manager_secret_version.dockerhub_token.name
      }
    }
  }

  depends_on = [
    google_project_service.enabled,
    google_secret_manager_secret_version.dockerhub_token,
  ]
}
