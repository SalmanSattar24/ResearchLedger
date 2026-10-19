variable "project" {
  description = "GCP project (created for ResearchLedger, billed to the education billing account)"
  type        = string
  default     = "researchledger-2026"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "github_repository" {
  description = "owner/name of the repository whose main branch may deploy"
  type        = string
  default     = "SalmanSattar24/ResearchLedger"
}

variable "invokers" {
  description = "IAM members allowed to call the services, e.g. [\"user:you@example.com\"]. Set in terraform.tfvars (not committed)."
  type        = list(string)
}
