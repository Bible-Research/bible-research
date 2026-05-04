variable "project_id" {
  type    = string
  default = "bible-research-489314"
}

variable "region" {
  type        = string
  default     = "europe-west3"
  description = "Default provider region. App Engine and Artifact Registry use europe-west3; audio resources follow Artifact Registry (see main.tf app_engine_region)."
}

# GitHub repository allowed to authenticate via WIF (e.g. Bible-Research/bible-research).
variable "github_repo" {
  type    = string
  default = "Bible-Research/bible-research"
}
