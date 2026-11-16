# Make KaiOS Useful

Notes, scripts, and a homebrew app from poking at a KaiOS feature phone and
making it do more than it ships with. Everything here was done on my own
device, over USB, using the KaiOS/Firefox OS developer tooling and the
public-domain [BananaHackers](https://bananahackers.net) community tools.

The headline result: a small sideloaded **Toolbox** app that can record audio
(and is wired up for a few other shortcuts), plus a set of Python helpers that
talk to the phone's settings over the Marionette debugging socket.

> ⚠️ This is a personal lab notebook, not a polished guide. Some exact steps
> (the URL I used to flip on debug mode, a couple of ADB invocations) are
> reconstructed from memory and marked **`TODO: confirm`** — I'll fill them in
> from my chat history. Treat version-specific details as "worked on my phone,
> your mileage may vary." KaiOS behaviour changes a lot between 2.5.x builds.

---

## What's in here

| Path | What it is |
|------|------------|
| [`toolbox/`](toolbox/) | My own app — audio recorder + menu of shortcuts. Sideloaded, runs as a `privileged` app. |
| [`laptop-sync/`](laptop-sync/) | Plug the phone into a Linux laptop → recordings move off the phone, family music goes onto it. Runs by itself on plug-in. |
| [`scripts/`](scripts/) | Python helpers that talk to the phone over ADB + the Marionette socket (read/write hidden settings, dump the settings actor, search the launcher bundle). |
| [`notes/`](notes/) | Raw output dumps from the reverse-engineering sessions (launcher bundle search, settings actor, etc.). |
| [`reference/crosstweak/`](reference/crosstweak/) | A copy of BananaHackers **CrossTweak** (public domain) — the unprivileged tweaker I used to open the dev menu. Kept here for convenience. |

---

## The journey, start to finish

### 1. Turn on debugging / developer mode

KaiOS hides developer mode, but you can unlock it without rooting.

- **What I did:** opened a web link on the phone's browser that flipped the
  device into debug mode. **`TODO: confirm exact URL`** — this was a page that
  triggers the hidden developer settings.
- **The reliable community way** (if the link trick doesn't work on your build):
  use **CrossTweak** ([`reference/crosstweak/`](reference/crosstweak/)) or
  Wallace Toolbox. CrossTweak option `5` is *"Enable developer menu in
  settings."* These are unprivileged apps you sideload the same way as the
  Toolbox below.
- Once dev mode is on, go to **Settings → Device → Developer** (menu name
  varies) and enable **Debugger → ADB and DevTools** (or **ADB only**).

The end state you want: the phone shows up when you run `adb devices` from a PC.

### 2. Look around with ADB

I used Google's `platform-tools` (`adb.exe`) on Windows.

```sh
adb devices            # confirm the phone is listed as "device", not "unauthorized"
adb shell              # poke around the filesystem
```

KaiOS is Gecko/Firefox OS underneath, so the interesting bits live in Gecko's
debugging surface rather than normal Android paths. The two things worth
knowing:

- **Marionette** (Gecko's automation/debug protocol) listens on a local port
  inside the phone. Forward it to your PC:

  ```sh
  adb forward tcp:6000 localfilesystem:/data/local/debugger-socket   # TODO: confirm socket path for your build
  ```

  Then you can speak the Marionette wire protocol to `127.0.0.1:6000`. The
  framing is dead simple: `<length>:<json-payload>`. See the scripts below.

- The launcher / system apps are shipped as minified JS bundles. I searched
  through `app.bundle.js` / `vendors.js` to find setting keys and launch
  internals — those dumps are in [`notes/`](notes/).

### 3. Read & write hidden settings over Marionette

The [`scripts/`](scripts/) folder is the result of figuring out how to drive
`MozSettings` from the PC through that forwarded port 6000:

- **`read_setting.py` / `read_setting2.py`** — connect, do the Marionette
  handshake, and read a setting value.
- **`kaios_setting.py` / `kaios_setting2.py` / `kaios_setting3.py`** — iterations
  on getting/setting arbitrary setting keys (booleans auto-convert).
- **`probe_getset.py`** — round-trips a single key (example used
  `home.customization.longpress`) to confirm get-then-set works.
- **`dump_settings_actor.py`** — dumps the settings actor so you can see what's
  queryable.
- **`find_module9.py` / `find_launch_store.py` / `find_customEvtentKey_body.py`
  / `searchFIles.py`** — grep helpers for digging through the launcher bundle
  for setting names, the app-launch store, and key-event handling.

> These point at `127.0.0.1:6000` and assume you've done the `adb forward`
> above. They're throwaway lab scripts — paths and keys are hardcoded; edit to
> taste. CrossTweak option `9` ("View or modify any system setting accessible
> via MozSettings") does the same thing interactively on the phone if you'd
> rather not script it.

### 4. Sideload a custom app with WebIDE (Pale Moon)

KaiOS 2.5 apps are just packaged web apps (HTML/JS/CSS + a `manifest.webapp`).
To push your own, you need an **old Gecko WebIDE** that can still speak to the
phone. Current Firefox dropped it; the community uses:

- **Pale Moon**, or old Firefox (~v59), or **Waterfox Classic** — all still
  have WebIDE.

Rough flow (this is what worked for me with Pale Moon):

1. Phone in debug mode with ADB/DevTools on (step 1), plugged in.
2. In WebIDE: **Connect** → it finds the phone as a runtime over USB
   (DevTools remote). **`TODO: confirm — did I adb forward the DevTools port
   first?`**
3. **Open Packaged App** → point it at the [`toolbox/`](toolbox/) folder.
4. **Install and Run** → it packages the folder and pushes it to the phone.

The app shows up in the launcher.

> Alternative installers the community uses: **gdeploy**, or OmniSD-style
> packages. CrossTweak option `4` can install a package too (but not on
> KaiOS 2.5.3+).

### 5. The permissions problem → make it `privileged`

This was the gotcha. My Toolbox needs the microphone (`audio-capture`) and to
write recordings to storage (`device-storage:*`). As a plain **web** app those
permission requests are silently denied — recording never starts, or
`getUserMedia` throws.

KaiOS (like Firefox OS) has three app trust levels set by `"type"` in the
manifest:

| `type` | Can use |
|--------|---------|
| `web` | basic web APIs only |
| `privileged` | `audio-capture`, `device-storage`, `geolocation`, etc. (what I needed) |
| `certified` | reserved for system apps (what CrossTweak/Wallace declare) |

**The fix:** set `"type": "privileged"` in
[`toolbox/manifest.webapp`](toolbox/manifest.webapp) and declare each
permission explicitly, then reinstall via WebIDE. After that, the recorder's
`getUserMedia({audio:true})` and `getDeviceStorage(...).addNamed(...)` calls
work.

```json
{
  "type": "privileged",
  "permissions": {
    "audio-capture":        { "description": "Required to record audio" },
    "device-storage:sdcard": { "access": "readwrite", "description": "Save recordings to SD card" },
    "device-storage:music":  { "access": "readwrite", "description": "Save recordings" }
  }
}
```

> Notes / things that bit me:
> - A privileged app must be **installed as privileged** — editing the type of
>   an already-installed web app isn't enough; reinstall the package.
> - Privileged packages normally expect to be signed for the real app store,
>   but for local dev/sideload via WebIDE that's bypassed.
> - The app probes several storage area names (`sdcard`, `music`, `internal`…)
>   because which one is writable varies by device — see `probeStorage()` in
>   [`toolbox/app.js`](toolbox/app.js).

---

## The Toolbox app

[`toolbox/`](toolbox/) is a single-screen KaiOS app built for the T9 keypad
(arrow-key focus navigation, center/Enter to activate, SoftLeft/Back to go
back). Current menu:

- **Record** — records mic audio with `MediaRecorder` (OGG/Opus where
  supported) and saves to device storage. ✅ working once privileged.
- **Alarms** — launches the system Clock app via a `MozActivity`.
- **Hotspot / Tethering** — opens the tethering settings section.
- **Transcribe site** — opens a URL (placeholder — point it at whatever
  transcription endpoint you want).
- **Device settings** — launches the Settings app.

It's deliberately dependency-free (one `app.js`, one `index.html`) so it's easy
to reason about on-device. Lots of `console.log` left in for DevTools.

### Ideas / next steps

- [ ] Fill in the real **Transcribe** flow (upload the recording somewhere, get
      text back).
- [ ] Confirm & document the exact debug-unlock URL and ADB forward commands.
- [ ] A proper recordings browser (list/play/delete what's on storage).
- [ ] Icon (`manifest` references `/icon.png` which isn't in the package yet).

---

## Living with it: laptop sync

Using the phone day to day as a carry-along backup phone means two chores: getting the
voice recordings off it, and getting music onto it. [`laptop-sync/`](laptop-sync/) does both
whenever the phone is plugged into my Linux laptop (no ADB or debug mode needed — it uses the
normal USB file-transfer / MTP connection):

- `.ogg` recordings are **moved** to the laptop — deleted from the phone only after a verified
  copy, and never kept twice even if renamed.
- New songs from a laptop folder are **copied** to the phone; nothing on the phone is deleted.

Setup, safety details and how to point it at your own folders:
[`laptop-sync/README.md`](laptop-sync/README.md).

---

## Credits & licensing

- **CrossTweak** and **Wallace Toolbox** are by **Luxferre** / the
  [BananaHackers](https://bananahackers.net) group. CrossTweak is released into
  the **public domain** (see [`reference/crosstweak/LICENSE`](reference/crosstweak/LICENSE)).
  Wallace Toolbox isn't bundled here — grab it from BananaHackers directly.
- My own code (`toolbox/`, `scripts/`) — do whatever you want with it. Consider
  it MIT / public domain, no warranty. It talks to debug interfaces on a phone;
  if you brick something that's on you.

This whole thing stands on the shoulders of the BananaHackers community and
their documentation. If you're getting into KaiOS homebrew, start there.
