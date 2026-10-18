# ResearchLedger on GCP: everything the service and its deploy pipeline need, in project researchledger-2026.
#
# No secrets exist anywhere in this setup: the service authenticates to Vertex AI and BigQuery as its own service
# account, and GitHub Actions authenticates by Workload Identity Federation (keyless). So there is no Secret
# Manager secret to create. The $10 billing alert budget was created in step 3 and is not managed here.

terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.10"
    }
  }
}

provider "google" {
  project               = var.project
  region                = var.region
  billing_project       = var.project
  user_project_override = true # bill API calls to this project, not the caller's default quota project
}

data "google_project" "this" {}

locals {
  services = [
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "cloudtrace.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "sts.googleapis.com",
  ]
  environments = toset(["staging", "prod"])
}

resource "google_project_service" "apis" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false
}

# ---------------------------------------------------------------- images

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "researchledger"
  format        = "DOCKER"
  description   = "ResearchLedger service images (one corpus at one commit per image)"

  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }
  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30 days
    }
  }
  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------- data

resource "google_bigquery_dataset" "marin" {
  dataset_id                 = "researchledger_marin"
  location                   = "US"
  description                = "Index of the public demo corpus (Marin at its pinned commit): chunks, vectors, lines, tables."
  delete_contents_on_destroy = true
  depends_on                 = [google_project_service.apis]
}

# ---------------------------------------------------------------- identities

# The service's identity: call Gemini, read (never write) the dataset, run queries, write traces.
resource "google_service_account" "runtime" {
  account_id   = "rl-runtime"
  display_name = "ResearchLedger service (Cloud Run)"
}

resource "google_project_iam_member" "runtime" {
  for_each = toset(["roles/aiplatform.user", "roles/bigquery.jobUser", "roles/cloudtrace.agent"])
  project  = var.project
  role     = each.value
  member   = google_service_account.runtime.member
}

resource "google_bigquery_dataset_iam_member" "runtime_reads" {
  dataset_id = google_bigquery_dataset.marin.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = google_service_account.runtime.member
}

# The deploy pipeline's identity (GitHub Actions, main branch only): build and push images, load the dataset,
# deploy the services, and run the evaluation (Gemini calls for the judge) against staging.
resource "google_service_account" "deployer" {
  account_id   = "rl-deployer"
  display_name = "ResearchLedger deploy pipeline (GitHub Actions)"
}

resource "google_project_iam_member" "deployer" {
  for_each = toset(["roles/aiplatform.user", "roles/bigquery.jobUser", "roles/run.developer"])
  project  = var.project
  role     = each.value
  member   = google_service_account.deployer.member
}

resource "google_bigquery_dataset_iam_member" "deployer_loads" {
  dataset_id = google_bigquery_dataset.marin.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.deployer.member
}

resource "google_artifact_registry_repository_iam_member" "deployer_pushes" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.name
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.deployer.member
}

# Deploying a service that runs as rl-runtime requires acting as it.
resource "google_service_account_iam_member" "deployer_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.deployer.member
}

# ---------------------------------------------------------------- GitHub Actions, keyless

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  # Only this repository's main branch can get credentials at all.
  attribute_condition = "assertion.repository == '${var.github_repository}' && assertion.ref == 'refs/heads/main'"
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_is_deployer" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

# ---------------------------------------------------------------- services

resource "google_cloud_run_v2_service" "app" {
  for_each            = local.environments
  name                = "researchledger-${each.key}"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL" # reachable, but every request needs an IAM identity token
  deletion_protection = false

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 8
    scaling {
      min_instance_count = 0 # no idle cost; the evaluation wakes the service before timing anything
      max_instance_count = 2
    }
    containers {
      # Placeholder until the deploy workflow pushes the first image; later image changes are the workflow's.
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle = true
      }
      env {
        name  = "RL_GCP_PROJECT"
        value = var.project
      }
      env {
        name  = "RL_SQL_BACKEND"
        value = "bigquery"
      }
      env {
        name  = "RL_BQ_DATASET"
        value = google_bigquery_dataset.marin.dataset_id
      }
      env {
        name  = "RL_TRACE"
        value = "1"
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }
  depends_on = [google_project_service.apis]
}

# No allUsers: only the listed people, and the pipeline (to evaluate staging), may call the services.
resource "google_cloud_run_v2_service_iam_member" "invokers" {
  for_each = { for pair in setproduct(tolist(local.environments), var.invokers) : "${pair[0]}/${pair[1]}" => pair }
  name     = google_cloud_run_v2_service.app[each.value[0]].name
  location = var.region
  role     = "roles/run.invoker"
  member   = each.value[1]
}

resource "google_cloud_run_v2_service_iam_member" "deployer_invokes_staging" {
  name     = google_cloud_run_v2_service.app["staging"].name
  location = var.region
  role     = "roles/run.invoker"
  member   = google_service_account.deployer.member
}
