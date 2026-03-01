# GCP Enterprise Infrastructure Terraform
# Nexus CRM - SOC 2 Compliant Deployment

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
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
  description = "Cloud SQL password"
  type        = string
  sensitive   = true
}

variable "env" {
  description = "Environment (dev/staging/prod)"
  type        = string
  default     = "prod"
}

# VPC Network with private subnets
resource "google_compute_network" "vpc" {
  name                    = "nexus-crm-vpc-${var.env}"
  auto_create_subnetworks = false
  routing_mode            = "regional"
}

# Private Subnet for GKE
resource "google_compute_subnetwork" "gke" {
  name          = "nexus-crm-gke-${var.env}"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.0.0.0/24"
  secondary_ip_range {
    range_name    = "gke-pods"
    ip_cidr_range = "10.4.0.0/14"
  }
  secondary_ip_range {
    range_name    = "gke-services"
    ip_cidr_range = "10.5.0.0/16"
  }
  private_ip_google_access = true
}

# Cloud SQL Subnet
resource "google_compute_subnetwork" "cloudsql" {
  name                     = "nexus-crm-cloudsql-${var.env}"
  region                   = var.region
  network                  = google_compute_network.vpc.name
  ip_cidr_range            = "10.1.0.0/24"
  private_ip_google_access = true
}

# Cloud NAT for private traffic
resource "google_compute_router" "nat" {
  name    = "nexus-crm-nat-${var.env}"
  region  = var.region
  network = google_compute_network.vpc.name
}

resource "google_compute_router_nat" "nat" {
  name                               = "nexus-crm-nat-${var.env}"
  router                             = google_compute_router.nat.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Cloud Armor Security Policy
resource "google_compute_security_policy" "waf" {
  name        = "nexus-crm-waf-${var.env}"
  description = "WAF for Nexus CRM"

  # Rate limiting rule
  rule {
    action   = "throttle(1000)"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Rate limit requests"
  }

  # SQL injection protection
  rule {
    action   = "deny(403)"
    priority = "9000"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable')"
      }
    }
    description = "Block SQL injection"
  }

  # XSS protection  
  rule {
    action   = "deny(403)"
    priority = "9001"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
    description = "Block XSS"
  }

  # Local file inclusion protection
  rule {
    action   = "deny(403)"
    priority = "9002"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('lfi-v33-stable')"
      }
    }
    description = "Block LFI"
  }

  # Default deny
  rule {
    action   = "deny(403)"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default deny"
  }
}

# Cloud Load Balancer with Armor
resource "google_compute_global_forwarding_rule" "lb" {
  name       = "nexus-crm-lb-${var.env}"
  port_range = "443"
  target     = google_compute_target_https_proxy.https.id
}

resource "google_compute_target_https_proxy" "https" {
  name             = "nexus-crm-https-${var.env}"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.cert.id]
}

resource "google_compute_url_map" "default" {
  name            = "nexus-crm-url-map-${var.env}"
  default_service = google_compute_backend_service.backend.id
}

resource "google_compute_backend_service" "backend" {
  name                  = "nexus-crm-backend-${var.env}"
  protocol              = "HTTP"
  port_name             = "http"
  load_balancing_scheme = "EXTERNAL"
  enable_cdn            = true
  security_policy       = google_compute_security_policy.waf.id

  backend {
    group = google_container_cluster.main.node_pool_id
  }
}

resource "google_compute_managed_ssl_certificate" "cert" {
  name = "nexus-crm-cert-${var.env}"

  managed {
    domains = ["crm.nexus.internal"]
  }
}

# Cloud SQL - Enterprise
resource "google_sql_database_instance" "main" {
  name             = "nexus-crm-db-${var.env}"
  database_version = "POSTGRES_15"
  region           = var.region
  tier             = "db-custom-4-15360"

  settings {
    availability_type = "REGIONAL"

    ip_configuration {
      private_network  = google_compute_network.vpc.id
      enable_ssl_utils = true
    }

    backup_configuration {
      enabled               = true
      backup_retention_days = 30
      start_time            = "03:00"
    }

    database_flags {
      name  = "max_connections"
      value = "500"
    }

    insights_config {
      query_insights_enabled = true
    }
  }

  deletion_protection = true
}

# Read Replica for reporting
resource "google_sql_database_instance" "replica" {
  name             = "nexus-crm-db-replica-${var.env}"
  database_version = "POSTGRES_15"
  region           = var.region
  tier             = "db-custom-2-7680"

  settings {
    availability_type = "REGIONAL"

    ip_configuration {
      private_network = google_compute_network.vpc.id
    }
  }

  master_instance_name = google_sql_database_instance.main.name
  deletion_protection  = true
}

# GKE Cluster - Enterprise
resource "google_container_cluster" "main" {
  name               = "nexus-crm-gke-${var.env}"
  location           = var.region
  min_master_version = "1.28"

  network    = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.gke.name
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "10.2.0.0/28"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods"
    services_secondary_range_name = "gke-services"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  database_encryption {
    state    = "ENCRYPTED"
    key_name = google_kms_crypto_key.db_key.id
  }

  node_pool {
    name       = "default-pool"
    node_count = 3

    node_config {
      machine_type = "n2-standard-4"
      disk_size_gb = 100
      preemptible  = false

      workload_metadata_config {
        mode = "GKE_METADATA"
      }
    }
  }
}

# Service Account
resource "google_service_account" "gke" {
  account_id   = "nexus-crm-gke-${var.env}"
  display_name = "Nexus CRM GKE SA"
}

# IAM Roles
resource "google_project_iam_member" "gke_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/bigquery.dataEditor",
    "roles/pubsub.publisher",
  ])
  role   = each.value
  member = "serviceAccount:${google_service_account.gke.email}"
}

# Cloud KMS for encryption
resource "google_kms_key_ring" "keyring" {
  name     = "nexus-crm-${var.env}"
  location = var.region
}

resource "google_kms_crypto_key" "db_key" {
  name     = "db-encryption-key"
  key_ring = google_kms_key_ring.keyring.id

  rotation_period = "7776000s"
}

# Cloud Storage with versioning
resource "google_storage_bucket" "data" {
  name          = "${var.project_id}-nexus-crm-data-${var.env}"
  location      = var.region
  storage_class = "STANDARD"

  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# Pub/Sub for async messaging
resource "google_pubsub_topic" "events" {
  name = "nexus-crm-events-${var.env}"
}

resource "google_pubsub_subscription" "events" {
  name  = "nexus-crm-events-sub-${var.env}"
  topic = google_pubsub_topic.events.name

  ack_deadline_seconds = 30

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

# Redis for caching
resource "google_redis_instance" "cache" {
  name           = "nexus-crm-cache-${var.env}"
  tier           = "STANDARD_HA"
  memory_size_gb = 10

  location_id        = var.region
  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_configs {
    maxmemory_policy = "allkeys-lru"
  }
}

output "vpc_network" {
  value = google_compute_network.vpc.id
}

output "gke_cluster_name" {
  value = google_container_cluster.main.name
}

output "database_connection" {
  value = google_sql_database_instance.main.connection_name
}

output "redis_host" {
  value = google_redis_instance.cache.host
}
