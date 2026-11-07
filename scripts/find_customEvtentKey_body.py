import os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH   = os.path.join(SCRIPT_DIR, "findings_customEvtentKey.txt")

DEFAULT = r"C:\Users\abuba\Downloads\platform-tools-latest-windows (1)\platform-tools\launcher\dist\vendors.js"
path = sys.argv[1] if len(sys.argv) >= 2 else DEFAULT

lines = []
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)

log("reading:", path, os.path.getsize(path), "bytes")
data = open(path, "rb").read()

# find the export line and the definition of 'w'
anchor = data.find(b"t.customEvtentKey=w")
log("export anchor offset:", anchor)

# dump 8000 bytes before the anchor and 500 after
start = max(0, anchor - 8000)
end   = min(len(data), anchor + 500)
chunk = data[start:end].decode("utf-8", "replace")
log(f"\n----- chunk [{start}:{end}] -----")
log(chunk)
log("----- end chunk -----\n")

# also: find every  'function w('  and  'w=function'  in the file,
# and dump each one's body.  There may be more than one `w` local name.
import re
for m in re.finditer(rb"function w\(", data):
    off = m.start()
    # dump 4000 bytes from the definition
    s = max(0, off - 100)
    e = min(len(data), off + 4000)
    log(f"\n==== function w() candidate at {off} ====")
    log(data[s:e].decode("utf-8", "replace"))
    log("==== end function w() candidate ====\n")

for m in re.finditer(rb"\bw=function\(", data):
    off = m.start()
    s = max(0, off - 100)
    e = min(len(data), off + 4000)
    log(f"\n==== w=function() candidate at {off} ====")
    log(data[s:e].decode("utf-8", "replace"))
    log("==== end w=function() candidate ====\n")

with open(OUT_PATH, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("\nwrote:", OUT_PATH)
