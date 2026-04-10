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

variable "image_tag" {
  type    = string
  default = "latest"
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
