# Originals: full-resolution user-uploaded images. App Engine runtime
# writes; thumbnail worker reads.
resource "google_storage_bucket" "images_originals" {
  name                        = "${var.project_id}-images-originals"
  location                    = local.app_engine_region
  project                     = var.project_id
  force_destroy               = false
  uniform_bucket_level_access = true

  versioning { enabled = true }

  lifecycle_rule {
    condition { with_state = "ARCHIVED", age = 30 }
    action    { type = "Delete" }
  }
  lifecycle_rule {
    condition { age = 7 }
    action    { type = "AbortIncompleteMultipartUpload" }
  }
}

# Thumbnails: written later by an async worker. Empty in this
# iteration, but provisioned now so IAM is in place.
resource "google_storage_bucket" "images_thumbnails" {
  name                        = "${var.project_id}-images-thumbnails"
  location                    = local.app_engine_region
  project                     = var.project_id
  force_destroy               = false
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition { age = 7 }
    action    { type = "AbortIncompleteMultipartUpload" }
  }
}

# App Engine runtime — write originals, read thumbnails (to sign URLs
# for clients).
resource "google_storage_bucket_iam_member" "appspot_originals_admin" {
  bucket = google_storage_bucket.images_originals.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${local.appspot_email}"
}
resource "google_storage_bucket_iam_member" "appspot_thumbnails_reader" {
  bucket = google_storage_bucket.images_thumbnails.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${local.appspot_email}"
}

# Future thumbnail worker — service account created now so IAM
# bindings already exist when the Cloud Function lands. No deploy
# follows from this alone; the worker is a later PR.
resource "google_service_account" "thumbnail_worker" {
  account_id   = "thumbnail-worker"
  display_name = "thumbnail-worker"
  description  = "Async worker that generates image thumbnails."
  project      = var.project_id

  depends_on = [google_project_service.enabled]
}

resource "google_storage_bucket_iam_member" "thumbnail_worker_originals_reader" {
  bucket = google_storage_bucket.images_originals.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.thumbnail_worker.email}"
}
resource "google_storage_bucket_iam_member" "thumbnail_worker_thumbnails_admin" {
  bucket = google_storage_bucket.images_thumbnails.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.thumbnail_worker.email}"
}
