output "service_urls" {
  value = { for env, s in google_cloud_run_v2_service.app : env => s.uri }
}

output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${var.project}/${google_artifact_registry_repository.images.repository_id}"
}

output "workload_identity_provider" {
  description = "For the deploy workflow (GitHub repository variable WIF_PROVIDER)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account" {
  description = "For the deploy workflow (GitHub repository variable DEPLOYER_SA)"
  value       = google_service_account.deployer.email
}
