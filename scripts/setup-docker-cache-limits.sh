#!/usr/bin/env bash
# One-time server setup: limit BuildKit cache size and schedule weekly prune.
# Run on the production host: sudo ./scripts/setup-docker-cache-limits.sh
set -euo pipefail

CACHE_LIMIT="${DOCKER_BUILD_CACHE_LIMIT:-2GB}"
DAEMON_JSON="/etc/docker/daemon.json"
CRON_LINE='0 4 * * 0 docker builder prune -af --filter "until=168h" >> /var/log/docker-prune.log 2>&1'
CRON_MARKER="docker-builder-prune-autoradar"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

mkdir -p /etc/docker

if [[ -f "$DAEMON_JSON" ]]; then
  cp "$DAEMON_JSON" "${DAEMON_JSON}.bak.$(date +%Y%m%d%H%M%S)"
  echo "Backed up existing $DAEMON_JSON"
fi

CACHE_LIMIT="$CACHE_LIMIT" python3 - "$DAEMON_JSON" <<'PY'
import json
import os
import sys

path = sys.argv[1]
limit = os.environ["CACHE_LIMIT"]

try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    data = {}
except json.JSONDecodeError as exc:
    print(f"Invalid JSON in {path}: {exc}", file=sys.stderr)
    sys.exit(1)

builder = data.setdefault("builder", {})
gc = builder.setdefault("gc", {})
gc["enabled"] = True
gc["defaultKeepStorage"] = limit

data["log-driver"] = data.get("log-driver", "json-file")
log_opts = data.setdefault("log-opts", {})
log_opts.setdefault("max-size", "10m")
log_opts.setdefault("max-file", "3")

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")

print(f"Updated {path} (builder.gc.defaultKeepStorage={limit})")
PY

if command -v systemctl >/dev/null 2>&1; then
  systemctl restart docker
  echo "Docker restarted."
else
  echo "systemctl not found — restart Docker manually." >&2
fi

existing_cron="$(crontab -l 2>/dev/null || true)"
if echo "$existing_cron" | grep -Fq "$CRON_MARKER"; then
  echo "Weekly builder prune cron already installed."
else
  {
    echo "$existing_cron" | sed '/^$/d'
    echo "# $CRON_MARKER"
    echo "$CRON_LINE"
  } | crontab -
  echo "Installed weekly builder prune cron (Sundays 04:00)."
fi

touch /var/log/docker-prune.log
chmod 644 /var/log/docker-prune.log

echo
echo "Build cache policy:"
docker builder du 2>/dev/null || true
echo
echo "Reclaiming cache older than 7 days (one-time cleanup)..."
docker builder prune -af --filter "until=168h" || true
echo
echo "Done. BuildKit will keep cache under ~${CACHE_LIMIT}; cron prunes weekly."
