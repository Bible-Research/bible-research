variable "project_id" {
  type    = string
  default = "bible-research-489314"
}

variable "region" {
  type    = string
  default = "europe-west3"
}

# GitHub repository allowed to authenticate via WIF (e.g. Bible-Research/bible-research).
variable "github_repo" {
  type    = string
  default = "Bible-Research/bible-research"
}
