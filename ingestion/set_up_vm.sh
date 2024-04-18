#!/bin/bash

# Update the package list
sudo apt-get update

# Install required packages
sudo apt-get install apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release -y

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up the stable repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update the package list again
sudo apt-get update

# Install Docker Engine, CLI, and Containerd
sudo apt-get install docker-ce docker-ce-cli containerd.io -y

# Initialize Airflow (optional, based on your use case)
sudo docker compose up airflow-init

# Start Docker containers in detached mode (optional, based on your use case)
sudo docker compose up -d

