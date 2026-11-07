import os, re, subprocess, sys, json, textwrap

ROOT = r"C:\Users\abuba\Downloads\platform-tools-latest-windows (1)\platform-tools"
OUT  = os.path.join(ROOT, "findings.txt")
ADB  = os.path.join(ROOT, "adb.exe")

lines = []
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)

# ---------- 1. Search app.bundle.js ----------
log("=" * 70)
log("1. app.bundle.js search")
log("=" * 70)

bundle_candidates = []
for p in (os.path.join(ROOT, "app.bundle.js"),
          os.path.join(ROOT, "launcher_extracted", "app.bundle.js"),
          os.path.join(ROOT, "launcher_extracted", "js", "app.bundle.js")):
    if os.path.exists(p):
        bundle_candidates.append(p)

if not bundle_candidates:
    log("app.bundle.js not found in expected locations; searching tree...")
    for dirpath, _, files in os.walk(ROOT):
        for f in files:
            if f == "app.bundle.js":
                bundle_candidates.append(os.path.join(dirpath, f))

log("found bundles:", bundle_candidates)

NEEDLES = ["customEvtentKey", "home.customization", "customEvtent",
           "longpress", "longPressDuration", "launchStore",
           "LaunchStore"]

for bpath in bundle_candidates:
    log("\n--- file:", bpath, "size:", os.path.getsize(bpath), "---")
    with open(bpath, "rb") as fh:
        data = fh.read()
    for needle in NEEDLES:
        b = needle.encode()
        idxs = []
        i = 0
        while True:
            i = data.find(b, i)
            if i < 0: break
            idxs.append(i)
            i += 1
        log(f"\n=== needle {needle!r}: {len(idxs)} hit(s) ===")
        for off in idxs[:40]:
            snip = data[max(0,off-200):off+400].decode("utf-8","replace")
            log(f"  offset {off}  context: ...{snip}...")
        if len(idxs) > 40:
            log(f"  ... {len(idxs)-40} more hits suppressed")

# ---------- 2. Search extracted omni ----------
log("\n" + "=" * 70)
log("2. omni_extracted search")
log("=" * 70)

omni_dirs = []
for cand in ("omni_extracted", "omni", "omni_ja"):
    p = os.path.join(ROOT, cand)
    if os.path.isdir(p):
        omni_dirs.append(p)

for od in omni_dirs:
    log(f"\n--- searching {od} ---")
    for dirpath, _, files in os.walk(od):
        for f in files:
            fp = os.path.join(dirpath, f)
            try:
                sz = os.path.getsize(fp)
                if sz > 8_000_000:  # skip huge binaries
                    continue
                with open(fp, "rb") as fh:
                    d = fh.read()
            except Exception:
                continue
            for needle in ("customEvtentKey","home.customization","customEvtent"):
                if needle.encode() in d:
                    log(f"  HIT {needle!r} in {fp}")

# ---------- 3. ADB probing ----------
log("\n" + "=" * 70)
log("3. ADB probing for shared.gaiamobile.org and settings")
log("=" * 70)

def adb(*args, timeout=20):
    try:
        r = subprocess.run([ADB, "shell"] + list(args),
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout + ("\n[stderr] " + r.stderr if r.stderr else "")
    except Exception as e:
        return f"[adb error] {e}"

if not os.path.exists(ADB):
    log("adb.exe not found at", ADB, "- skipping adb section")
else:
    log("\n-- adb devices --")
    try:
        r = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=20)
        log(r.stdout + r.stderr)
    except Exception as e:
        log("devices error", e)

    cmds = [
        ["ls", "/system/b2g/webapps/"],
        ["ls", "-la", "/system/b2g/webapps/shared.gaiamobile.org/"],
        ["ls", "-la", "/system/b2g/webapps/shared.gaiamobile.org/js/"],
        ["ls", "-la", "/system/b2g/webapps/shared.gaiamobile.org/scripts/"],
        ["ls", "-la", "/system/b2g/webapps/system.gaiamobile.org/"],
        ["ls", "-la", "/data/b2g/webapps/"],
        ["find", "/system/b2g/webapps/shared.gaiamobile.org", "-type", "f", "-name", "*.js"],
        ["find", "/system/b2g/webapps", "-type", "f", "-name", "custom*.js"],
        ["find", "/system/b2g/webapps", "-type", "f", "-name", "*launch*.js"],
        ["find", "/system/b2g/webapps", "-type", "f", "-name", "*custom*.js"],
    ]
    for c in cmds:
        log(f"\n$ adb shell {' '.join(c)}")
        log(adb(*c))

    # grep on device for the string across webapps (may not have grep)
    log("\n$ adb shell grep -R -l customEvtentKey /system/b2g/webapps")
    log(adb("grep", "-R", "-l", "customEvtentKey", "/system/b2g/webapps"))

    log("\n$ adb shell busybox grep -R -l customEvtentKey /system/b2g/webapps")
    log(adb("busybox", "grep", "-R", "-l", "customEvtentKey", "/system/b2g/webapps"))

    log("\n$ adb shell grep -R -l home.customization /system/b2g/webapps")
    log(adb("grep", "-R", "-l", "home.customization", "/system/b2g/webapps"))

    log("\n$ adb shell busybox grep -R -l home.customization /system/b2g/webapps")
    log(adb("busybox", "grep", "-R", "-l", "home.customization", "/system/b2g/webapps"))

# ---------- write out ----------
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("\nWrote:", OUT)
