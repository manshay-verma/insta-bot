#!/bin/bash
# setup_nginx.sh - Configure Nginx as a reverse proxy

set -e

sudo apt-get install -y nginx

echo "Creating Nginx configuration..."
cat <<EOF | sudo tee /etc/nginx/sites-available/insta-bot
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:5173; # Frontend dev or Nginx dist
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000; # Backend API
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /ws/ {
        proxy_pass http://localhost:8000; # WebSockets
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/insta-bot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo "Nginx configuration complete!"
