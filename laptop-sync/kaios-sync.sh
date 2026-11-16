#!/usr/bin/env bash
# kaios-sync.sh — Digit 4G <-> laptop over USB (MTP / "file transfer" mode)
#
#   bash kaios-sync.sh --dry-run   # show what would happen, change nothing
#   bash kaios-sync.sh             # do it
#
# 1) Moves .ogg recordings from the phone's digit4g folder to the laptop.
#    A phone file is deleted only after its laptop copy is complete and the same size.
# 2) Copies new/changed songs from ~/Music/Family to the phone's music/Family folder.
#    Never deletes anything on the phone.
#
# Installed by install.sh, it also runs by itself every time the phone is plugged in.
set -uo pipefail

# ---- settings ---------------------------------------------------------------
# These are the author's folders. To use your own, don't edit this file — put any
# of these lines in ~/.config/kaios-sync.conf (see kaios-sync.conf.example).
PHONE_STORAGE="Internal"                              # phone storage name as shown in the file manager
PHONE_RECORDINGS_DIR="digit4g"                        # phone folder the recordings are saved in
LAPTOP_RECORDINGS="$HOME/Documents/Digit 4G Recordings"
LAPTOP_MUSIC="$HOME/Music/Family"
PHONE_MUSIC_DIR="music/Family"                        # where songs go on the phone
CONF="${XDG_CONFIG_HOME:-$HOME/.config}/kaios-sync.conf"
# shellcheck source=/dev/null
[ -f "$CONF" ] && . "$CONF"
# -----------------------------------------------------------------------------

DRY_RUN=0; [ "${1:-}" = "--dry-run" ] && DRY_RUN=1
run() { if [ "$DRY_RUN" = 1 ]; then echo "  would: $*"; else "$@"; fi; }
notify() { command -v notify-send >/dev/null && notify-send -i phone "Digit 4G sync" "$1"; true; }

# --- find the phone (any MTP phone that has the recordings folder) ----------
# Phone may take a while to unlock / switch to file transfer, so keep trying ~90 s.
GVFS="/run/user/$(id -u)/gvfs"
find_phone() {
  local d
  for d in "$GVFS"/mtp:host=*/"$PHONE_STORAGE"; do
    [ -d "$d/$PHONE_RECORDINGS_DIR" ] && { echo "$d"; return 0; }
  done
  return 1
}
PHONE=""
for _ in $(seq 1 30); do
  PHONE=$(find_phone) && break
  for uri in $(gio mount -li 2>/dev/null | grep -oE 'mtp://[^ ]+' | sort -u); do
    gio mount "$uri" 2>/dev/null
  done
  sleep 3
done
if [ -z "$PHONE" ]; then
  echo "Phone not found. Plug it in, unlock it, make sure it's in file-transfer mode, then retry."
  exit 0
fi
echo "Phone found at: $PHONE"
PHONE_RECORDINGS="$PHONE/$PHONE_RECORDINGS_DIR"
PHONE_MUSIC="$PHONE/$PHONE_MUSIC_DIR"

failed=0

# --- 1) phone -> laptop: move recordings ----------------------------------
echo "== Recordings: phone -> laptop"
mkdir -p "$LAPTOP_RECORDINGS"
pulled=0
now=$(date +%s)
# Fingerprint (md5) of every recording already on the laptop, so duplicates are caught by content, not name.
declare -A known
while IFS= read -r -d '' f; do
  known[$(md5sum < "$f" | cut -d' ' -f1)]=$(basename "$f")
done < <(find "$LAPTOP_RECORDINGS" -maxdepth 1 -type f ! -name '.*' -print0)
shopt -s nullglob nocaseglob
for src in "$PHONE_RECORDINGS"/*.ogg; do
  name=$(basename "$src")
  dest="$LAPTOP_RECORDINGS/$name"
  size=$(stat -c%s "$src" 2>/dev/null) || { echo "  can't read: $name"; ((failed++)); continue; }

  # Don't grab a file the phone may still be writing to.
  mtime=$(stat -c%Y "$src" 2>/dev/null || echo 0)
  if [ $(( now - mtime )) -lt 120 ]; then echo "  skip (too new, maybe still recording): $name"; continue; fi

  tmp="$LAPTOP_RECORDINGS/.$name.part"
  if ! run cp "$src" "$tmp"; then
    echo "  FAILED: $name (left on phone)"; rm -f "$tmp"; ((failed++)); continue
  fi
  if [ "$DRY_RUN" = 0 ]; then
    if [ "$(stat -c%s "$tmp")" != "$size" ]; then
      echo "  FAILED (incomplete copy): $name (left on phone)"; rm -f "$tmp"; ((failed++)); continue
    fi
    hash=$(md5sum < "$tmp" | cut -d' ' -f1)
    if [ -n "${known[$hash]:-}" ]; then
      # Identical audio already on the laptop (whatever its name) — don't keep a second copy.
      echo "  duplicate of ${known[$hash]}: $name (not kept)"
      rm -f "$tmp"
    else
      touch -d "@$mtime" "$tmp"                 # keep the original recording date
      # Same name but DIFFERENT audio already on laptop? Keep both; old one becomes name.~1~
      mv --backup=numbered "$tmp" "$dest"
      known[$hash]="$name"
      echo "  saved: $name"
    fi
  fi
  if run rm "$src"; then ((pulled++)); else echo "  copied but couldn't delete from phone: $name"; fi
done
shopt -u nocaseglob

# --- 2) laptop -> phone: add music ----------------------------------------
echo "== Music: laptop -> phone"
pushed=0; same=0
while IFS= read -r -d '' src; do
  rel="${src#"$LAPTOP_MUSIC"/}"
  dest="$PHONE_MUSIC/$rel"
  size=$(stat -c%s "$src")
  if [ -f "$dest" ] && [ "$(stat -c%s "$dest" 2>/dev/null)" = "$size" ]; then ((same++)); continue; fi
  echo "  send: $rel"
  run mkdir -p "$(dirname "$dest")"
  [ -e "$dest" ] && run rm -f "$dest"        # half-sent from an interrupted run
  if run cp "$src" "$dest"; then ((pushed++)); else echo "  FAILED: $rel"; ((failed++)); fi
done < <(find "$LAPTOP_MUSIC" -type f ! -name '.*' -print0)

echo
echo "Recordings moved: $pulled | Songs sent: $pushed | Already there: $same | Problems: $failed"
[ "$DRY_RUN" = 1 ] && echo "(dry run — nothing was changed)"
[ "$failed" -gt 0 ] && echo "Anything that failed is untouched; just run the script again."
msg="Recordings moved: $pulled · Songs sent: $pushed"
[ "$failed" -gt 0 ] && msg="$msg · $failed problem(s) — replug to retry"
[ "$DRY_RUN" = 0 ] && notify "$msg"
exit 0
