# Terraform Configuration for GCP Virtual Machine with secure SSH access and a static IP address. 

# The configuration includes:

# SSH Key Generation
# Compute Engine API Activation
# Static IP Configuration
# Firewall rules for allowing access to Airflow webservice
# GCE Instance Provisioning**: Deploys a GCE instance configured with the generated SSH key for
# access, and sets up various provisioning steps to prepare the instance for running the data
# pipeline. This includes file transfers for setup scripts, Docker Compose configurations, environment 
# variables, and custom shell scripts to finalize the setup.

# generate ssh keys
resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}
output "private_ssh_key" {
  value     = tls_private_key.ssh_key.private_key_pem
  sensitive = true
}
resource "local_file" "private_key_file" {
  content  = tls_private_key.ssh_key.private_key_pem
  filename = "../ssh/ssh_private_key.pem"
  file_permission = "0600"
}


# enable Compute Engine API
resource "google_project_service" "compute" {
  project                    = var.project_id
  service                    = "compute.googleapis.com"
  disable_on_destroy         = true
  disable_dependent_services = true
}


# setup external static IP
resource "google_compute_address" "static_ip" {
  name    = var.gce_static_ip_name
  depends_on = [google_project_service.compute]
}
output "allocated_static_ip" {
  value = google_compute_address.static_ip.address
}

# setup allowed ports for airflow webservice
resource "google_compute_firewall" "git_proj_ssh" {
  name          = "git-proj-ssh"
  network       = "default"
  target_tags   = ["ssh-access"]
  source_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }
  depends_on = [google_project_service.compute]
}

# setup GCE
resource "google_compute_instance" "default" {
  project                   = var.project_id
  zone                      = var.zone
  name                      = var.gce_name
  machine_type              = "e2-standard-4"
  tags                      = ["ssh-access"]
  allow_stopping_for_update = true

  boot_disk {
    initialize_params {
      image = "ubuntu-2004-focal-v20230302"
      size  = "30"
    }
  }
  
  network_interface {
    network = "default"

    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  metadata = {
    ssh-keys = "user1:${tls_private_key.ssh_key.public_key_openssh}"
  }

  service_account {
    scopes = ["cloud-platform"]
    email  = google_service_account.service_account.email
  }
  
  provisioner "file" {
    source      = "../ingestion/set_up_vm.sh"
    destination = "/tmp/step1_set_up_vm.sh"
  }
  provisioner "file" {
    source      = "../ingestion/docker-compose.yaml"
    destination = "/tmp/docker-compose.yaml"
  }
  provisioner "file" {
    source      = "../ingestion/.env"
    destination = "/tmp/.env"
  }
  provisioner "file" {
    source      = "../ingestion/dags/ingestion.py"
    destination = "/tmp/ingestion.py"
  }
  
  provisioner "remote-exec" {
    inline = [
      "cd /tmp",
      "chmod +x ./step1_set_up_vm.sh",
      "sudo ./step1_set_up_vm.sh",
      "sudo mv ./ingestion.py ./dags/ingestion.py",
    ]
  }
  connection {
    type        = "ssh"
    user        = "user1"
    private_key = tls_private_key.ssh_key.private_key_pem
    host        = google_compute_instance.default.network_interface[0].access_config[0].nat_ip
  }
  depends_on = [google_project_service.compute]

}
