# Remote state bucket (same backend as backend.tf). Kept in state to avoid accidental drift.
resource "google_storage_bucket" "terraform_state" {
  name                        = "bible-research-tf-state"
  location                    = "US-CENTRAL1"
  project                     = var.project_id
  force_destroy               = false
  uniform_bucket_level_access = false

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }
}
