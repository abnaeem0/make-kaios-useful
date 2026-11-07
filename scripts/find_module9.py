import os, sys, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH   = os.path.join(SCRIPT_DIR, "findings_module9.txt")

# default: the dist folder we know about
DEFAULT_DIST = r"C:\Users\abuba\Downloads\platform-tools-latest-windows (1)\platform-tools\launcher\dist"

dist_dir = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_DIST

log_lines = []
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log_lines.append(s)

log("script dir:", SCRIPT_DIR)
log("dist dir:", dist_dir)

if not os.path.isdir(dist_dir):
    log("not a directory:", dist_dir)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines))
    sys.exit(1)

# collect all .js files in the dist dir (recursively, in case of subchunks)
js_files = []
for dirpath, _, files in os.walk(dist_dir):
    for f in files:
        if f.lower().endswith(".js"):
            js_files.append(os.path.join(dirpath, f))

js_files.sort(key=lambda p: os.path.getsize(p), reverse=True)

log("\nJS files found:")
for p in js_files:
    log(f"  {os.path.getsize(p):>10}  {p}")

# For each file: search for the definition of customEvtentKey.
# A "definition" looks like:
#   customEvtentKey:function(...)
#   customEvtentKey=function(...)
#   customEvtentKey: customEvtentKey
#   function customEvtentKey(...)
# A "call" looks like:
#   .customEvtentKey(
# We want files that contain the definition.
DEF_PATTERNS = [
    re.compile(rb"customEvtentKey\s*[:=]\s*function"),
    re.compile(rb"function\s+customEvtentKey"),
    re.compile(rb"customEvtentKey\s*[:=]\s*\w"),   # alias binding
]

for path in js_files:
    log("\n" + "=" * 78)
    log("FILE:", path, os.path.getsize(path), "bytes")
    log("=" * 78)

    data = open(path, "rb").read()

    # 1) every occurrence of the string, with context
    hits = []
    i = 0
    while True:
        i = data.find(b"customEvtentKey", i)
        if i < 0:
            break
        hits.append(i)
        i += 1
    log("raw 'customEvtentKey' occurrences:", len(hits))

    # 2) definitional occurrences
    def_hits = []
    for pat in DEF_PATTERNS:
        for m in pat.finditer(data):
            def_hits.append((m.start(), pat.pattern.decode()))
    log("definition-style matches:", len(def_hits))
    for off, pat in def_hits:
        log(f"  - definition match at {off}  (pattern {pat!r})")
        start = max(0, off - 400)
        end = min(len(data), off + 3000)
        chunk = data[start:end].decode("utf-8", "replace")
        log("")
        log(f"----- definition context around {off} -----")
        log(chunk)
        log("----- end context -----\n")

    # 3) also dump the first few raw hits with context, in case the definition
    #    uses a different pattern we didn't foresee
    if not def_hits and hits:
        log("no definition matches; showing first 3 raw hits:")
        for off in hits[:3]:
            start = max(0, off - 300)
            end = min(len(data), off + 1200)
            chunk = data[start:end].decode("utf-8", "replace")
            log("")
            log(f"----- raw context around {off} -----")
            log(chunk)
            log("----- end raw context -----\n")

with open(OUT_PATH, "w", encoding="utf-8") as fh:
    fh.write("\n".join(log_lines))
print("\nwrote:", OUT_PATH)
