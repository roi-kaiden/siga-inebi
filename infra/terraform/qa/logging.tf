# Cloud Run stores the full request URL, query string included, in its request
# log. Document downloads carry a temporary token in `?token=`; Nginx and
# Gunicorn already log paths only, so drop the platform entries that would
# keep that token. Other request entries are kept.
resource "google_logging_project_exclusion" "run_request_tokens" {
  name        = "${local.name}-request-tokens"
  project     = var.project_id
  description = "SIGA INEBI QA: Cloud Run request logs with download tokens in the query string"
  filter      = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="${local.name}"
    logName="projects/${var.project_id}/logs/run.googleapis.com%2Frequests"
    httpRequest.requestUrl=~"[?&]token="
  EOT
}
