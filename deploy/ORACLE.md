# Deploying to an Oracle Cloud VM

Run everything below **on the Oracle server** (over your own SSH session). Never paste private keys or passwords into chat.

## 1. Open ports in the Oracle console (one-time)

Networking → Virtual Cloud Networks → your VCN → Security Lists → Default → **Add Ingress Rules**:
source `0.0.0.0/0`, TCP, destination ports `80` and `443`.

## 2. Point your domain (optional but needed for HTTPS)

Create a DNS `A` record for your domain → the VM's public IP. Wait until `ping yourdomain.com` shows that IP.

## 3. Get the code onto the server

```sh
sudo apt-get update && sudo apt-get install -y git   # Oracle Linux: sudo dnf install -y git
git clone https://github.com/gaijwnna/omni-agent-hub-private.git
# Username: your GitHub username. Password: a GitHub personal access token
# (github.com/settings/tokens → fine-grained, read-only "Contents" on this repo).
cd omni-agent-hub-private
```

## 4. Run the setup

```sh
sudo bash deploy/oracle-setup.sh
```

It asks for your domain, operator name and contact email, then installs Docker/nginx/certbot, opens the host firewall, generates secrets **on the server**, starts the containers and requests an HTTPS certificate.

## Useful commands

```sh
cd /opt/omni-agent-hub/launch
sudo docker compose ps                 # what's running
sudo docker compose logs --tail=80     # recent logs
sudo docker compose up --build -d      # rebuild after updates
```

To update later: `git pull` in the clone, then re-run `sudo bash deploy/oracle-setup.sh` (it keeps your existing `.env`).

Payments (Stripe/x402) stay disabled. Add their keys to `/opt/omni-agent-hub/launch/.env` on the server only after test-mode checks (see `launch/docs/LAUNCH_STATUS.md` in the archive).
