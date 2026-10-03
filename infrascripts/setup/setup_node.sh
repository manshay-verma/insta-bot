#!/bin/bash
# setup_node.sh - Configure Node.js environment

set -e

echo "Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

echo "Verifying Node.js version..."
node -v

echo "Node.js environment setup complete!"
