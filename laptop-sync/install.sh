#!/usr/bin/env bash
# Sets up automatic sync whenever the phone is plugged in.
# Run from inside your clone of the repo, with the phone plugged in:   bash install.sh
# Undo:                                                                  bash install.sh --uninstall
#
# The installed command is a *link* to kaios-sync.sh in this folder, so a `git pull`
# updates it — no need to reinstall. Don't move or delete this folder afterwards.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
RULE=/etc/udev/rules.d/90-kaios-sync.rules

if [ "${1:-}" = "--uninstall" ]; then
  sudo rm -f "$RULE" && sudo udevadm control --reload-rules
  rm -f ~/.config/systemd/user/kaios-sync.service ~/.local/bin/kaios-sync.sh
  systemctl --user daemon-reload
  echo "Removed. The phone will no longer sync by itself."
  exit 0
fi

vendor=$(lsusb 2>/dev/null | grep -iE 'unisoc|spreadtrum' | head -1 | sed -E 's/.*ID ([0-9a-fA-F]{4}):.*/\1/' || true)
if [ -z "$vendor" ]; then
  echo "Couldn't spot the phone in 'lsusb' (is it plugged in?). Using the usual Unisoc ID 1782."
  vendor=1782
fi
echo "Phone USB vendor ID: $vendor"

chmod +x "$here/kaios-sync.sh"
mkdir -p ~/.local/bin
ln -sf "$here/kaios-sync.sh" ~/.local/bin/kaios-sync.sh
install -Dm644 "$here/kaios-sync.service" ~/.config/systemd/user/kaios-sync.service
systemctl --user daemon-reload

sed "s/\"1782\"/\"$vendor\"/" "$here/90-kaios-sync.rules" | sudo tee "$RULE" >/dev/null
sudo udevadm control --reload-rules

echo
echo "Done. From now on, plugging in the phone runs the sync and shows a notification."
echo "Runs from:                $here/kaios-sync.sh"
echo "Run it by hand any time:  kaios-sync.sh --dry-run   (or without --dry-run)"
echo "See what it did:          journalctl --user -u kaios-sync -n 50"
