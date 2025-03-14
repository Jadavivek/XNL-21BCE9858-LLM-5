# Multi-cloud Terraform configuration
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
  backend "s3" {
    bucket = "llm-cicd-terraform-state"
    key    = "terraform.tfstate"
    region = "us-west-2"
  }
}

# AWS Provider Configuration
provider "aws" {
  region = "us-west-2"
}

# GCP Provider Configuration
provider "google" {
  project = "llm-cicd-project"
  region  = "us-central1"
}

# Azure Provider Configuration
provider "azurerm" {
  features {}
}

# AWS EKS Cluster
module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "18.0.0"
  cluster_name    = "llm-eks-cluster"
  cluster_version = "1.24"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    default = {
      min_size       = 1
      max_size       = 5
      desired_size   = 2
      instance_types = ["t3.large"]
    }
    gpu = {
      min_size       = 0
      max_size       = 3
      desired_size   = 1
      instance_types = ["g4dn.xlarge"]
      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }
}

# GCP GKE Cluster
resource "google_container_cluster" "primary" {
  name     = "llm-gke-cluster"
  location = "us-central1"

  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "primary-node-pool"
  location   = "us-central1"
  cluster    = google_container_cluster.primary.name
  node_count = 2

  node_config {
    machine_type = "e2-standard-4"
  }
}

resource "google_container_node_pool" "gpu_nodes" {
  name       = "gpu-node-pool"
  location   = "us-central1"
  cluster    = google_container_cluster.primary.name
  node_count = 1

  node_config {
    machine_type = "n1-standard-4"
    guest_accelerator {
      type  = "nvidia-tesla-t4"
      count = 1
    }
  }
}

# Azure AKS Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "llm-aks-cluster"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "llm-aks"

  default_node_pool {
    name       = "default"
    node_count = 2
    vm_size    = "Standard_DS2_v2"
  }

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  name                  = "gpu"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_NC6s_v3"
  node_count            = 1
}

# MinIO Distributed Storage
resource "helm_release" "minio" {
  name             = "minio"
  repository       = "https://charts.min.io/"
  chart            = "minio"
  version          = "4.0.2"
  namespace        = "minio-system"
  create_namespace = true

  set {
    name  = "mode"
    value = "distributed"
  }

  set {
    name  = "replicas"
    value = "4"
  }

  set {
    name  = "persistence.size"
    value = "100Gi"
  }
}

# CockroachDB Multi-Region Deployment
resource "helm_release" "cockroachdb" {
  name             = "cockroachdb"
  repository       = "https://charts.cockroachdb.com/"
  chart            = "cockroachdb"
  version          = "6.0.0"
  namespace        = "cockroachdb"
  create_namespace = true

  set {
    name  = "statefulset.replicas"
    value = "3"
  }

  set {
    name  = "conf.cache"
    value = "0.25"
  }

  set {
    name  = "conf.cluster-name"
    value = "llm-cockroachdb-cluster"
  }
# }
# provider "aws" {
#   region = "us-east-1" # Change this to your region
# }

# resource "aws_s3_bucket" "example" {
#   bucket = "jadavivek-fintech-llm-bucket"
#   acl    = "private"
# }
