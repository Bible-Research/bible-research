resource "google_service_account" "audio_scheduler" {
  account_id   = "audio-scheduler"
  display_name = "Audio Scheduler (invokes Cloud Run Job)"
  project      = var.project_id
}

resource "google_cloud_run_v2_job_iam_member" "audio_scheduler_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_job.audio_generator.location
  name     = google_cloud_run_v2_job.audio_generator.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.audio_scheduler.email}"
}

resource "google_cloud_scheduler_job" "monthly_audio_generator" {
  name             = "monthly-audio-generator"
  description      = "Run audio-generator Cloud Run Job on the 3rd of each month."
  schedule         = "0 3 3 * *"
  time_zone        = "Europe/Riga"
  project          = var.project_id
  region           = local.app_engine_region
  attempt_deadline = "320s"

  retry_config {
    retry_count = 0
  }

  http_target {
    http_method = "POST"
    uri         = "https://${local.app_engine_region}-run.googleapis.com/v2/projects/${var.project_id}/locations/${local.app_engine_region}/jobs/${google_cloud_run_v2_job.audio_generator.name}:run"

    oauth_token {
      service_account_email = google_service_account.audio_scheduler.email
    }
  }

  depends_on = [
    google_cloud_run_v2_job_iam_member.audio_scheduler_invoker,
  ]
}
