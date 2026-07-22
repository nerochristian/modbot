# ModBot VPS Auto-Update

This repo has two VPS update paths:

1. `modbot-autoupdate.timer` polls GitHub every minute from the VPS.
2. `.github/workflows/deploy-vps.yml` deploys immediately on push when SSH secrets are configured.

## Install on the VPS

Run this once on the VPS:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip
sudo git clone --branch main https://github.com/nerochristian/modbot.git /opt/modbot
cd /opt/modbot
sudo bash deploy/install_vps_autoupdate.sh
```

Keep the live environment in `/opt/modbot/.env`. The deploy script preserves `.env`, `.venv`, `data/`, `backups/`, and the dashboard session database at `dashboard/dev.db`.

## Multiple bots on one VPS

Every bot must have its own app directory, bot service, auto-update service,
timer, env file, and deploy lock. If two bots share `modbot-autoupdate.service`
or `/etc/modbot-autoupdate.env`, one bot can deploy/restart the other bot.

Install each bot with unique names:

```bash
# Main moderation bot
sudo MODBOT_APP_DIR=/opt/modbot \
  MODBOT_SERVICE=modbot \
  MODBOT_UPDATE_SERVICE=modbot-autoupdate \
  MODBOT_ENTRYPOINT=bot.py \
  bash /opt/modbot/deploy/install_vps_autoupdate.sh

# Example second bot from a different checkout/path
sudo MODBOT_APP_DIR=/opt/lifesim \
  MODBOT_SERVICE=lifesim \
  MODBOT_UPDATE_SERVICE=lifesim-autoupdate \
  MODBOT_ENTRYPOINT=bot.py \
  MODBOT_REPO_URL=https://github.com/yourusername/lifesimbot.git \
  bash /opt/lifesim/deploy/install_vps_autoupdate.sh
```

This creates isolated units like:

```text
modbot.service              -> /opt/modbot/.env      -> /opt/modbot/bot.py
modbot-autoupdate.service   -> /etc/modbot-autoupdate.env
modbot-autoupdate.timer

lifesim.service             -> /opt/lifesim/.env     -> /opt/lifesim/bot.py
lifesim-autoupdate.service  -> /etc/lifesim-autoupdate.env
lifesim-autoupdate.timer
```

## Repair mixed-up services on a VPS

If bots are running each other, first inspect what each unit really starts:

```bash
systemctl cat modbot --no-pager
systemctl cat lifesim --no-pager
systemctl cat modbot-autoupdate --no-pager
systemctl cat lifesim-autoupdate --no-pager
cat /etc/modbot-autoupdate.env
cat /etc/lifesim-autoupdate.env
```

Then reinstall each service with unique names and paths:

```bash
sudo systemctl disable --now modbot-autoupdate.timer lifesim-autoupdate.timer 2>/dev/null || true
sudo systemctl disable --now modbot-autoupdate.service lifesim-autoupdate.service 2>/dev/null || true

sudo MODBOT_APP_DIR=/opt/modbot MODBOT_SERVICE=modbot MODBOT_UPDATE_SERVICE=modbot-autoupdate MODBOT_ENTRYPOINT=bot.py \
  bash /opt/modbot/deploy/install_vps_autoupdate.sh

sudo MODBOT_APP_DIR=/opt/lifesim MODBOT_SERVICE=lifesim MODBOT_UPDATE_SERVICE=lifesim-autoupdate MODBOT_ENTRYPOINT=bot.py \
  bash /opt/lifesim/deploy/install_vps_autoupdate.sh

sudo systemctl daemon-reload
sudo systemctl restart modbot lifesim
```

Finally verify:

```bash
systemctl status modbot lifesim --no-pager
journalctl -u modbot -n 50 --no-pager
journalctl -u lifesim -n 50 --no-pager
```

## Check it

```bash
systemctl status modbot --no-pager
systemctl status modbot-autoupdate.timer --no-pager
journalctl -u modbot-autoupdate.service -n 80 --no-pager
```

Force an update check:

```bash
sudo systemctl start modbot-autoupdate.service
```

## GitHub push deploy

Set these GitHub repository secrets:

- `VPS_HOST`
- `VPS_USER` (optional, defaults to `root`)
- `VPS_PORT` (optional, defaults to `22`)
- `VPS_SSH_KEY`
- `VPS_KNOWN_HOSTS`

Optional GitHub repository variables:

- `MODBOT_APP_DIR` (defaults to `/opt/modbot`)
- `MODBOT_SERVICE` (defaults to `modbot`)

The workflow runs `/opt/modbot/scripts/vps_deploy.sh` on the VPS. If the secrets are missing, the workflow exits cleanly and the VPS timer still handles polling.
