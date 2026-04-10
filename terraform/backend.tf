terraform {
  backend "gcs" {
    bucket = "bible-research-tf-state"
    prefix = "terraform/state"
  }
}
