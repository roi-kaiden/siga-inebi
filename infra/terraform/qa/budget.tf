data "google_project" "budget" {
  count      = var.monthly_budget_usd == null ? 0 : 1
  project_id = var.project_id
}

resource "google_project_service" "budget_api" {
  count              = var.monthly_budget_usd == null ? 0 : 1
  project            = var.project_id
  service            = "billingbudgets.googleapis.com"
  disable_on_destroy = false
}

resource "google_billing_budget" "qa" {
  count           = var.monthly_budget_usd == null ? 0 : 1
  billing_account = var.billing_account_id
  display_name    = "SIGA INEBI QA ${var.project_id}"
  budget_filter {
    projects = ["projects/${data.google_project.budget[0].number}"]
  }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = floor(var.monthly_budget_usd)
      nanos         = floor((var.monthly_budget_usd - floor(var.monthly_budget_usd)) * 1000000000)
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }
  depends_on = [google_project_service.budget_api]
}
