import os, sys, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH   = os.path.join(SCRIPT_DIR, "findings_launchstore.txt")

DEFAULT = r"C:\Users\abuba\Downloads\platform-tools-latest-windows (1)\platform-tools\launcher\dist\app.bundle.js"
path = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT

lines = []
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)

log("reading:", path, os.path.getsize(path), "bytes")
data = open(path, "rb").read()

# LaunchStore uses .launch(type, url).  Find all "launch:function(" occurrences
# and dump each one.
pat = re.compile(rb"launch\s*:\s*function\s*\(")
for m in pat.finditer(data):
    off = m.start()
    s = max(0, off - 200)
    e = min(len(data), off + 2500)
    log(f"\n==== launch:function at {off} ====")
    log(data[s:e].decode("utf-8", "replace"))
    log("==== end ====\n")

# Also look for the class that owns it: "name=\"LaunchStore\"" or similar
for needle in [b"LaunchStore", b"isLaunching", b"refreshLaunchStateTimer"]:
    log("\n" + "=" * 70)
    log("NEEDLE:", needle.decode())
    log("=" * 70)
    i = 0
    hits = 0
    while True:
        i = data.find(needle, i)
        if i < 0:
            break
        hits += 1
        s = max(0, i - 300)
        e = min(len(data), i + 900)
        log(f"\n--- hit {hits} at {i} ---")
        log(data[s:e].decode("utf-8", "replace"))
        i += 1
        if hits >= 6:
            log("(more suppressed)")
            break

with open(OUT_PATH, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("\nwrote:", OUT_PATH)
