#!/bin/bash
# security_audit.sh - Quick diagnostic for security posture

set -e

echo "Checking firewall rules (UFW)..."
sudo ufw status verbose || echo "Firewall is NOT ACTIVE!"

echo "Checking for rootless Docker..."
docker context show | grep rootless || echo "Docker is running as ROOT!"

echo "Checking open ports..."
ss -tuln | grep -i listen

echo "Checking SSH logins..."
last | head -10

echo "Security audit complete!"
