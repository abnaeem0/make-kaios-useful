# Settings / Marionette scripts

Lab scripts used to read and write KaiOS `MozSettings` from a PC, over the
phone's Marionette debug socket forwarded to `127.0.0.1:6000`.

Prereq: phone in debug mode (ADB + DevTools on), then forward the socket, e.g.
`adb forward tcp:6000 localfilesystem:/data/local/debugger-socket`
(confirm the socket path for your build).

Wire format is Marionette's `<length>:<json>` framing — see `send_msg` /
`recv_msg` in any of the files.

- `read_setting.py`, `read_setting2.py` — read a setting value
- `kaios_setting.py`, `kaios_setting2.py`, `kaios_setting3.py` — get/set arbitrary keys
- `probe_getset.py` — round-trip one key to verify set works
- `dump_settings_actor.py` — dump the settings actor
- `find_module9.py`, `find_launch_store.py`, `find_customEvtentKey_body.py`,
  `searchFIles.py` — grep helpers for the launcher JS bundle

These are hardcoded and throwaway — edit paths/keys before running. CrossTweak
option `9` does the same thing interactively on-device.
