# GCP Infrastructure Terraform Configuration
# Nexus CRM - Salesforce Replacement

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west2"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Cloud SQL Database
resource "google_sql_database_instance" "nexus_crm" {
  name             = "nexus-crm-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = "REGIONAL"
  }
}

resource "google_sql_database" "nexus_crm_db" {
  name     = "nexus_crm"
  instance = google_sql_database_instance.nexus_crm.name
}

resource "google_sql_user" "nexus_crm_user" {
  name     = "nexus_user"
  instance = google_sql_database_instance.nexus_crm.name
  password = var.db_password
}

# GKE Cluster
resource "google_container_cluster" "nexus_crm_cluster" {
  name                     = "nexus-crm-cluster"
  location                 = var.region
  remove_default_node_pool = true
  initial_node_count       = 3

  node_pool {
    name       = "default-node-pool"
    node_count = 3

    node_config {
      machine_type = "n2-standard-2"
      disk_size_gb = 100
    }
  }
}

# Service Account
resource "google_service_account" "nexus_crm_sa" {
  account_id   = "nexus-crm-sa"
  display_name = "Nexus CRM Service Account"
  description  = "Service account for Nexus CRM running on GKE"
}

# Project IAM
resource "google_project_iam_binding" "nexus_crm_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  members = ["serviceAccount:${google_service_account.nexus_crm_sa.email}"]
}

resource "google_project_iam_binding" "nexus_crm_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  members = ["serviceAccount:${google_service_account.nexus_crm_sa.email}"]
}

resource "google_project_iam_binding" "nexus_crm_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  members = ["serviceAccount:${google_service_account.nexus_crm_sa.email}"]
}

# Cloud Storage Bucket
resource "google_storage_bucket" "nexus_crm_bucket" {
  name          = "${var.project_id}-nexus-crm-storage"
  location      = var.region
  storage_class = "STANDARD"
}

output "database_connection_string" {
  value = google_sql_database_instance.nexus_crm.connection_name
}

output "gke_cluster_endpoint" {
  value = google_container_cluster.nexus_crm_cluster.endpoint
}
