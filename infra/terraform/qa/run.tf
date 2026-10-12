resource "google_cloud_run_v2_job" "maintenance" {
  for_each = var.deploy_jobs ? {
    migrate = ["migrate", "--noinput"]
    seed    = ["seed_demo_data"]
  } : {}
  name                = "${local.name}-${each.key}"
  location            = var.region
  deletion_protection = true
  labels              = local.labels
  template {
    task_count  = 1
    parallelism = 1
    template {
      service_account = google_service_account.runtime.email
      max_retries     = 0
      timeout         = "600s"
      volumes {
        name = "cloudsql"
        cloud_sql_instance { instances = [google_sql_database_instance.qa.connection_name] }
      }
      containers {
        name    = "backend"
        image   = var.backend_image
        command = ["python", "manage.py"]
        args    = each.value
        resources { limits = { cpu = "1", memory = "2Gi" } }
        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
        dynamic "env" {
          for_each = local.runtime_env
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = local.secrets
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.qa[env.key].secret_id
                version = google_secret_manager_secret_version.qa[env.key].version
              }
            }
          }
        }
      }
    }
  }
  # The GitHub Actions deploy owns image updates; Terraform keeps the rest.
  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version]
  }
  depends_on = [google_project_iam_member.cloudsql,
    google_secret_manager_secret_iam_member.runtime, google_storage_bucket_iam_member.media,
  google_service_account_iam_member.sign_self]
}

resource "google_cloud_run_v2_service" "qa" {
  count               = var.deploy_service ? 1 : 0
  name                = local.name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = true
  labels              = local.labels
  template {
    service_account                  = google_service_account.runtime.email
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"
    max_instance_request_concurrency = 8
    timeout                          = "120s"
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance { instances = [google_sql_database_instance.qa.connection_name] }
    }
    containers {
      name       = "frontend"
      image      = var.frontend_image
      depends_on = ["backend"]
      ports { container_port = 8080 }
      resources {
        limits            = { cpu = "1", memory = "128Mi" }
        cpu_idle          = true
        startup_cpu_boost = false
      }
      startup_probe {
        http_get {
          path = "/healthz"
          port = 8080
        }
        period_seconds    = 5
        failure_threshold = 24
      }
    }
    containers {
      name  = "backend"
      image = var.backend_image
      resources {
        limits            = { cpu = "1", memory = "2Gi" }
        cpu_idle          = true
        startup_cpu_boost = false
      }
      dynamic "env" {
        for_each = local.runtime_env
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = { for key, value in local.secrets : key => value if key != "DEMO_ADMIN_PASSWORD" }
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.qa[env.key].secret_id
              version = google_secret_manager_secret_version.qa[env.key].version
            }
          }
        }
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
      startup_probe {
        http_get {
          path = "/api/v1/health/database/"
          port = 8081
        }
        period_seconds    = 5
        failure_threshold = 24
      }
    }
  }
  # The GitHub Actions deploy owns image updates; Terraform keeps the rest.
  # Cloud Run reports the Cloud SQL mount on the ingress container whichever
  # container declares it, so the mounts would show a perpetual diff.
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image, template[0].containers[1].image, client, client_version,
      template[0].containers[0].volume_mounts, template[0].containers[1].volume_mounts,
    ]
  }
  depends_on = [google_project_iam_member.cloudsql,
    google_secret_manager_secret_iam_member.runtime, google_storage_bucket_iam_member.media,
  google_service_account_iam_member.sign_self]
}

resource "google_cloud_run_v2_service_iam_member" "public_web" {
  count    = var.deploy_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.qa[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
