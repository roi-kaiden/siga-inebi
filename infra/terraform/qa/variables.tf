variable "project_id" {
  description = "Existing, explicitly selected project with billing enabled. Never creates a project."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Provide the existing Google Cloud project ID explicitly."
  }
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "deploy_jobs" {
  description = "Enable only after the backend image has been pushed; jobs are never auto-executed."
  type        = bool
  default     = false
}

variable "deploy_service" {
  description = "Enable only after migration and synthetic seed jobs succeeded."
  type        = bool
  default     = false
}

variable "backend_image" {
  description = "Immutable Artifact Registry digest of Dockerfile.cloud backend target."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = var.backend_image == null ? !var.deploy_jobs && !var.deploy_service : can(regex("^[a-z0-9-]+-docker\\.pkg\\.dev/[^/]+/[^/]+/[^@]+@sha256:[a-f0-9]{64}$", var.backend_image))
    error_message = "Deployment requires a real Artifact Registry backend image pinned by SHA-256 digest."
  }
}

variable "frontend_image" {
  description = "Immutable Artifact Registry digest of Dockerfile.cloud frontend target."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = var.frontend_image == null ? !var.deploy_service : can(regex("^[a-z0-9-]+-docker\\.pkg\\.dev/[^/]+/[^/]+/[^@]+@sha256:[a-f0-9]{64}$", var.frontend_image))
    error_message = "Web deployment requires a real Artifact Registry frontend image pinned by SHA-256 digest."
  }
}

variable "monthly_budget_usd" {
  description = "Optional alert threshold, not a spending cap. Null creates no budget."
  type        = number
  default     = null
  nullable    = true
  validation {
    condition     = var.monthly_budget_usd == null ? true : var.monthly_budget_usd > 0
    error_message = "The optional monthly budget must be greater than zero."
  }
}

variable "billing_account_id" {
  description = "Existing billing account ID required only when configuring a budget."
  type        = string
  default     = null
  nullable    = true
  validation {
    condition     = var.monthly_budget_usd == null || var.billing_account_id != null
    error_message = "Provide billing_account_id when monthly_budget_usd is set."
  }
}

variable "github_repository" {
  description = "GitHub repository (owner/name) allowed to deploy QA through Workload Identity Federation."
  type        = string
  default     = "siga-inebi/siga-inebi"
}

variable "deploy_branch" {
  description = "Only workflows running on this branch receive deploy credentials."
  type        = string
  default     = "develop"
}
