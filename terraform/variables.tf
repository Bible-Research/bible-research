variable "project_id" {
  type    = string
  default = "bible-research-489314"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "dockerhub_username" {
  type    = string
  default = "tedisrozenfelds"
}

variable "dockerhub_token" {
  type      = string
  sensitive = true
}

# When true, Artifact Registry validates Docker Hub credentials (requires a real PAT).
# When false, the remote repo uses public Docker Hub only (avoids rate-limit auth during bootstrap).
variable "dockerhub_upstream_auth" {
  type    = bool
  default = false
}

variable "image_tag" {
  type    = string
  default = "latest"
}

# If set, Cloud Run uses this image directly (e.g. gcr.io/cloudrun/hello) until you push to Docker Hub.
# If empty, image is built from the Artifact Registry Docker Hub proxy path and image_tag.
variable "container_image" {
  type        = string
  description = "Optional full container URI; when empty, use dockerhub-proxy path"
  default     = ""
}

variable "django_secret_key" {
  type      = string
  sensitive = true
  default   = "bootstrap-placeholder"
}

variable "dbt_key" {
  type      = string
  sensitive = true
  default   = "bootstrap-placeholder"
}

variable "esv_key" {
  type      = string
  sensitive = true
  default   = "bootstrap-placeholder"
}

variable "database_url" {
  type      = string
  sensitive = true
  default   = "bootstrap-placeholder"
}

variable "db_ssl_cert" {
  type      = string
  sensitive = true
  default   = "bootstrap-placeholder"
}
