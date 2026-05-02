resource "google_service_account" "audio_generator" {
  account_id   = "audio-generator"
  display_name = "Audio Generator (Cloud Run Job)"
  project      = var.project_id
}

# The Job needs to read DATABASE_URL and DJANGO_SECRET_KEY at Django
# settings import time, even though it does not touch the DB. Reuse the
# existing Secret Manager entries via the same data sources used in
# secrets.tf.
resource "google_secret_manager_secret_iam_member" "audio_generator_db_url" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.app["DATABASE_URL"].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.audio_generator.email}"
}

resource "google_secret_manager_secret_iam_member" "audio_generator_django_secret" {
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.app["DJANGO_SECRET_KEY"].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.audio_generator.email}"
}

resource "google_cloud_run_v2_job" "audio_generator" {
  name     = "audio-generator"
  location = local.app_engine_region
  project  = var.project_id

  template {
    template {
      service_account = google_service_account.audio_generator.email
      timeout         = "3600s"
      max_retries     = 1

      containers {
        # Reuse the App Engine container image. Pin to a tag your CI
        # pipeline publishes; "latest" works for the sandbox project.
        image = "${local.app_engine_region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.gae_standard.repository_id}/bible-research:latest"

        command = [
          "python", "manage.py", "generate_chapter_audio",
          "--fileset-id", "LVSGLU8",
        ]

        env {
          name  = "FILESET_ID"
          value = "LVSGLU8"
        }
        env {
          name  = "GOOGLE_TTS_LANGUAGE_CODE"
          value = "lv-LV"
        }
        env {
          name  = "GOOGLE_TTS_VOICE_NAME"
          value = "lv-LV-Chirp3-HD-Sadachbia"
        }
        env {
          name  = "GOOGLE_TTS_SAMPLE_RATE_HERTZ"
          value = "24000"
        }
        env {
          name  = "AUDIO_BUCKET_NAME"
          value = google_storage_bucket.bible_audio.name
        }
        env {
          name  = "AUDIO_SIGNED_URL_TTL_SECONDS"
          value = "3600"
        }
        env {
          name  = "DJANGO_SETTINGS_MODULE"
          value = "bible_research.settings"
        }
        env {
          name  = "GOOGLE_CLOUD_PROJECT"
          value = var.project_id
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret.app["DATABASE_URL"].secret_id
              version = "latest"
            }
          }
        }

        env {
          name = "DJANGO_SECRET_KEY"
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret.app["DJANGO_SECRET_KEY"].secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.audio_generator_db_url,
    google_secret_manager_secret_iam_member.audio_generator_django_secret,
  ]
}
