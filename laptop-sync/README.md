# Laptop sync — recordings off the phone, music onto it

**Use case:** the KaiOS phone is a carry-along backup phone. Voice recordings pile up on it, and family
music needs to get onto it. Plug the phone into the Linux laptop and this happens by itself:

| Direction | What | From → To | Phone copy |
|---|---|---|---|
| Phone → laptop | `.ogg` recordings | `Internal/digit4g/` → `~/Documents/Digit 4G Recordings/` | **Deleted** after a verified copy |
| Laptop → phone | Songs (any files, subfolders kept) | `~/Music/Family/` → `Internal/music/Family/` | Nothing on the phone is ever deleted |

A desktop notification says what was done, e.g. *"Recordings moved: 3 · Songs sent: 5"*.

Tested with a Jazz **Digit 4G / Digit Lite** (Unisoc chip) on Linux with Thunar (XFCE). It should work on any
KaiOS phone that shows up in the file manager as an `mtp://` device.

## Files

| File | What it is |
|---|---|
| `kaios-sync.sh` | The sync itself. Default folders are at the top. |
| `kaios-sync.conf.example` | Template for using your own folders (see below). |
| `install.sh` | One-time setup so the sync runs on plug-in. `--uninstall` removes it. |
| `kaios-sync.service` | systemd user service that runs the script. |
| `90-kaios-sync.rules` | udev rule: "phone plugged in → start the service". |

## Using your own folders

The folder names in the table are mine. If yours differ, don't edit the script — create
`~/.config/kaios-sync.conf` with just the lines you want to change:

```bash
cp kaios-sync.conf.example ~/.config/kaios-sync.conf
nano ~/.config/kaios-sync.conf
```

That file lives outside the repo, so it's never committed and `git pull` never touches it.

## Setup

Run it from your clone of this repo — `install.sh` links to the script here rather than copying it,
so a `git pull` updates the sync too. (Don't move or delete the clone afterwards; if you do, re-run
`install.sh` from the new place.)

```bash
cd make-kaios-useful/laptop-sync

# 1. Try it by hand first — dry run changes nothing, just lists what it would do
bash kaios-sync.sh --dry-run
bash kaios-sync.sh

# 2. Make it automatic (phone plugged in; asks for your password once)
bash install.sh
```

Then: plug in the phone, unlock it, and wait for the notification.

Useful later:

```bash
kaios-sync.sh --dry-run                      # run by hand any time
journalctl --user -u kaios-sync -n 50        # what the last automatic run did
git pull                                     # get updates — no reinstall needed
bash install.sh --uninstall                  # stop the automatic sync
```

## How it stays safe

- **Nothing is deleted from the phone until the laptop copy is complete** (same size). If the cable drops,
  the phone keeps the file and the next plug-in tries again.
- **No duplicate recordings.** Every recording is fingerprinted (md5 of its content). If the same audio is
  already on the laptop under *any* name, the extra copy is not kept.
- **Name clashes keep both.** A different recording with an existing name is saved and the older one becomes
  `name.ogg.~1~`.
- **Recordings under 2 minutes old are skipped** in case the phone is still recording; they come next time.
- Recordings keep their original date.
- Songs half-sent by an interrupted run are replaced on the next run.

## Notes on MTP (internal storage)

The phone's internal storage is only reachable over MTP ("file transfer"), not as a USB drive. That's fine,
but:

- The phone must be **unlocked** and in file-transfer mode. The script waits up to ~90 s for it.
- MTP is slower than a USB drive, and some phones drop the connection mid-copy — just replug.
- A recording made *while* plugged in may not be visible until you replug.
- The phone's music player may need a restart to see new songs. MP3 / M4A are the safe formats.
- Linux sees the phone through `/run/user/<uid>/gvfs/mtp:host=…`. If that folder is empty, install
  `gvfs-fuse` (Arch/Manjaro); on Debian/Ubuntu it's part of `gvfs`.

## Troubleshooting

- **Nothing happens on plug-in:** run `lsusb` with the phone connected and check the `ID xxxx:` vendor matches
  `/etc/udev/rules.d/90-kaios-sync.rules`; re-run `bash install.sh` to fix it.
- **"Phone not found":** open the phone once in Thunar; check the storage is called `Internal` and the folder
  `digit4g` exists (change `PHONE_STORAGE` / `PHONE_RECORDINGS_DIR` at the top of the script if not).
