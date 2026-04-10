output "cloud_run_url" {
  description = "HTTPS URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.bible_research.uri
}

output "cicd_sa_email" {
  description = "CI/CD service account email for GitHub Actions"
  value       = google_service_account.cicd.email
}

output "cicd_sa_key" {
  description = "Decoded JSON service account key for GitHub secret GCP_SA_KEY (paste raw)"
  value       = base64decode(google_service_account_key.cicd.private_key)
  sensitive   = true
}
