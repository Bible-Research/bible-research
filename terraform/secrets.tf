resource "google_secret_manager_secret" "django_secret_key" {
  secret_id = "DJANGO_SECRET_KEY"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "django_secret_key" {
  secret      = google_secret_manager_secret.django_secret_key.id
  secret_data = var.django_secret_key

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "dbt_key" {
  secret_id = "DBT_KEY"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "dbt_key" {
  secret      = google_secret_manager_secret.dbt_key.id
  secret_data = var.dbt_key

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "esv_key" {
  secret_id = "ESV_KEY"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "esv_key" {
  secret      = google_secret_manager_secret.esv_key.id
  secret_data = var.esv_key

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "DATABASE_URL"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = var.database_url

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_secret_manager_secret" "db_ssl_cert" {
  secret_id = "DB_SSL_CERT"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "db_ssl_cert" {
  secret      = google_secret_manager_secret.db_ssl_cert.id
  secret_data = var.db_ssl_cert

  lifecycle {
    ignore_changes = [secret_data]
  }
}
