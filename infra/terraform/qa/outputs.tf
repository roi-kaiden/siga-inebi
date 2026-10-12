output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.qa.repository_id}"
}

output "database_connection_name" {
  value = google_sql_database_instance.qa.connection_name
}

output "media_bucket" {
  value = google_storage_bucket.media.name
}

output "service_url" {
  value = var.deploy_service ? google_cloud_run_v2_service.qa[0].uri : null
}

output "maintenance_jobs" {
  value = { for name, job in google_cloud_run_v2_job.maintenance : name => job.name }
}
