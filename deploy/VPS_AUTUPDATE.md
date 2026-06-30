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

Keep the live environment in `/opt/modbot/.env`. The deploy script preserves `.env`, `.venv`, `data/`, `backups/`, and `website/dist/`.

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
