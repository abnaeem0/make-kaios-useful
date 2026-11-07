import socket, json, sys, time, traceback

HOST = "127.0.0.1"
PORT = 6000

def send_msg(sock, obj):
    payload = json.dumps(obj).encode("utf-8")
    frame = str(len(payload)).encode("ascii") + b":" + payload
    print(">>> " + json.dumps(obj)[:200])
    sock.sendall(frame)

def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError(f"socket closed while expecting {n} bytes, got {len(buf)}")
        buf += chunk
    return buf

def recv_msg(sock, timeout=15):
    sock.settimeout(timeout)
    # read digits until ':'
    length_bytes = b""
    while True:
        ch = recv_exact(sock, 1)
        if ch == b":":
            break
        if not ch.isdigit():
            raise ValueError(f"unexpected byte in length prefix: {ch!r}")
        length_bytes += ch
        if len(length_bytes) > 10:
            raise ValueError("length prefix too long")
    n = int(length_bytes.decode("ascii"))
    payload = recv_exact(sock, n)
    text = payload.decode("utf-8", "replace")
    print("<<< " + text[:200] + ("..." if len(text) > 200 else ""))
    return json.loads(text)

def main():
    print(f"connecting to {HOST}:{PORT} ...")
    s = socket.create_connection((HOST, PORT), timeout=15)
    print("connected")

    try:
        # --- 1. read server greeting ---
        greeting = recv_msg(s, timeout=15)
        print("\n=== greeting ===")
        print(json.dumps(greeting, indent=2)[:2000])
    except Exception as e:
        print("greeting failed:", e)
        s.close()
        return

    try:
        # --- 2. ask for tabs + actors ---
        send_msg(s, {"to": "root", "type": "listTabs"})
        tabs = recv_msg(s, timeout=15)
        print("\n=== listTabs ===")
        print(json.dumps(tabs, indent=2)[:2000])
    except Exception as e:
        print("listTabs failed:", e)
        s.close()
        return

    sa = tabs.get("settingsActor")
    print("\nsettingsActor:", sa)

    if not sa:
        print("no settingsActor in reply; aborting")
        s.close()
        return

    try:
        # --- 3. read our setting ---
        send_msg(s, {
            "to": sa,
            "type": "get",
            "request": {"home.customization.longpress": None}
        })
        got = recv_msg(s, timeout=15)
        print("\n=== get reply ===")
        print(json.dumps(got, indent=2))
    except Exception as e:
        print("get failed:", e)

    try:
        # --- 4. ask what requests it supports ---
        send_msg(s, {"to": sa, "type": "requestTypes"})
        rt = recv_msg(s, timeout=15)
        print("\n=== requestTypes ===")
        print(json.dumps(rt, indent=2))
    except Exception as e:
        print("requestTypes failed:", e)

    s.close()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
