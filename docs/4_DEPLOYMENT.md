# EC2 Deployment Guide

## 1. Prerequisites
- An AWS EC2 Instance (Ubuntu 22.04 LTS)
- Security Group inbound rules:
  - Port 22 (SSH)
  - Port 80 (HTTP)
  - Port 443 (HTTPS)
- Docker and Docker Compose installed on the instance

## 2. Server Setup

SSH into your EC2 instance and install Docker:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker ubuntu
```

## 3. Clone & Configure

```bash
git clone <your-repo-url> rental-house
cd rental-house

# Create .env
cp .env.example .env
nano .env # Update with production values
```

Make sure `DEBUG=False` in your `.env`.

## 4. Deploy

Build and start the containers in detached mode:

```bash
docker compose up -d --build
```

Check logs:
```bash
docker compose logs -f
```

## 5. Reverse Proxy & SSL (Optional but Recommended)
For production, you should use Let's Encrypt to get an SSL certificate. You can set up an Nginx container specifically for Certbot, or use a tool like Caddy/Nginx Proxy Manager.
