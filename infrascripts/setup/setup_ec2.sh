#!/bin/bash
# setup_ec2.sh - Initial server provisioning

set -e

echo "Updating system..."
sudo apt-get update && sudo apt-get upgrade -y

echo "Installing core dependencies..."
sudo apt-get install -y build-essential curl git wget libpq-dev

echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo "Server provisioning complete!"
