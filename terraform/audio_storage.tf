resource "google_storage_bucket" "bible_audio" {
  name                        = "${var.project_id}-bible-audio"
  location                    = local.app_engine_region
  project                     = var.project_id
  force_destroy               = false
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket_iam_member" "appspot_audio_reader" {
  bucket = google_storage_bucket.bible_audio.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${local.appspot_email}"
}

resource "google_storage_bucket_iam_member" "audio_generator_writer" {
  bucket = google_storage_bucket.bible_audio.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.audio_generator.email}"
}
