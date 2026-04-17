data "google_storage_bucket" "appspot_default" {
  name = "${var.project_id}.appspot.com"
}

data "google_storage_bucket" "appspot_staging" {
  name = "staging.${var.project_id}.appspot.com"
}
