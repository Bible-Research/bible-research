output "workload_identity_provider" {
  description = "Full resource name for google-github-actions/auth (Workload Identity Federation)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_deployer_sa_email" {
  description = "Service account email for GitHub Actions (WIF)"
  value       = google_service_account.github_deployer.email
}

output "github_deployer_email" {
  description = "Same as github_deployer_sa_email (legacy output name)"
  value       = google_service_account.github_deployer.email
}

output "app_engine_default_hostname" {
  value = google_app_engine_application.main.default_hostname
}

output "app_engine_location_id" {
  value = google_app_engine_application.main.location_id
}

output "appspot_bucket" {
  value = "gs://${data.google_storage_bucket.appspot_default.name}"
}

output "appspot_staging_bucket" {
  value = "gs://${data.google_storage_bucket.appspot_staging.name}"
}

output "terraform_state_bucket" {
  value = google_storage_bucket.terraform_state.url
}

output "secret_ids_observed" {
  value = sort(keys({ for k, v in data.google_secret_manager_secret.app : k => true }))
}

output "bible_audio_bucket" {
  value = google_storage_bucket.bible_audio.name
}

output "audio_generator_sa_email" {
  value = google_service_account.audio_generator.email
}

output "audio_generator_job_name" {
  value = google_cloud_run_v2_job.audio_generator.name
}

output "audio_scheduler_job_name" {
  value = google_cloud_scheduler_job.monthly_audio_generator.name
}

# Base image path (without tag) for the audio-generator Cloud Run Job.
# The Deploy workflow appends ":<git-sha>" when building, pushing, and
# pinning the Cloud Run Job to the new immutable image.
output "audio_generator_image_base" {
  value = "${google_artifact_registry_repository.audio_generator.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.audio_generator.repository_id}/audio-generator"
}
