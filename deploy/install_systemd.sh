#!/usr/bin/env bash
# deploy/install_systemd.sh
# Installs the daily crawler run as a systemd timer (10:00 UTC).
#
# Usage on the VM, from the repo root:
#   bash deploy/install_systemd.sh
#
# Re-running is safe: unit files are overwritten, timer re-enabled.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$USER}"

# ── Find the virtualenv ──────────────────────────────────────
PYTHON=""
for v in venv .venv env; do
    if [ -x "$REPO_DIR/$v/bin/python" ]; then
        PYTHON="$REPO_DIR/$v/bin/python"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "ERROR: no virtualenv found in $REPO_DIR (venv/, .venv/ or env/)." >&2
    echo "Create it first: python3 -m venv venv && venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

# italo launches a headed Chromium (Playwright) -> needs a virtual X server
XVFB_RUN="$(command -v xvfb-run || true)"
if [ -z "$XVFB_RUN" ]; then
    echo "ERROR: xvfb-run not found (needed by the italo crawler)." >&2
    echo "Install: sudo apt-get install -y xvfb && sudo venv/bin/playwright install-deps chromium && venv/bin/playwright install chromium" >&2
    exit 1
fi

if [ ! -f "$REPO_DIR/.env" ]; then
    echo "WARNING: $REPO_DIR/.env not found – DB credentials will be missing." >&2
fi

echo "Repo:   $REPO_DIR"
echo "User:   $RUN_USER"
echo "Python: $PYTHON"

# ── Service (one run) ────────────────────────────────────────
sudo tee /etc/systemd/system/rdh-crawlers.service > /dev/null <<EOF
[Unit]
Description=Rail Data Hub - daily crawler run
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
User=$RUN_USER
WorkingDirectory=$REPO_DIR
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONIOENCODING=utf-8
ExecStart=$XVFB_RUN -a $PYTHON $REPO_DIR/scheduler/run_crawlers.py
TimeoutStartSec=5h
Nice=5
EOF

# ── Timer (daily 10:00 UTC, catch up missed runs) ────────────
sudo tee /etc/systemd/system/rdh-crawlers.timer > /dev/null <<EOF
[Unit]
Description=Rail Data Hub - daily crawler timer (10:00 UTC)

[Timer]
OnCalendar=*-*-* 10:00:00 UTC
Persistent=true
Unit=rdh-crawlers.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now rdh-crawlers.timer

echo
systemctl list-timers rdh-crawlers.timer --no-pager
echo
echo "Done. Manual test run:   sudo systemctl start rdh-crawlers.service"
echo "Follow logs:             journalctl -u rdh-crawlers.service -f"