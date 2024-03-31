variable "project_id" {
  type        = string
  description = "The name of the project"
  default     = "github-activities-412623"
}

variable "account_id" {
  description = "account_id (source: terraform.tfvars)"
  type        = string
}

variable "region" {
  type        = string
  description = "The default compute region"
  default     = "us-west2"
}

variable "zone" {
  type        = string
  description = "The default compute zone"
  default     = "us-west2-a"
}

#gcs
variable "storage_class" {
  description = "storage_class (source: terraform.tfvars)"
  type        = string
}

#gcs
variable "data_lake_bucket" {
  description = "data_lake_bucket (source: terraform.tfvars)"
  type        = string
}

#gce
variable "gce_name" {
  description = "gce_name (source: terraform.tfvars)"
  type        = string
}

#vpc
/*
variable "vpc_network_name" {
  description = "vpc_network_name (source: terraform.tfvars)"
  type        = string
}*/

#static_ip name
variable "gce_static_ip_name" {
  description = "gce_static_ip_name (source: terraform.tfvars)"
  type        = string
}

#bigQuery dataset name
variable "bq_dataset" {
  description = "bq_dataset (source: terraform.tfvars)"
  type        = string
}

#bigQuery table name
variable "bq_table_id" {
  description = "table_id for today's github activities (source: terraform.tfvars)"
  type        = string
}
