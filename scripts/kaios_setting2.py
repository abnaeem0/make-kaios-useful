import socket, json, sys, traceback

HOST = "127.0.0.1"
PORT = 6000

def send_msg(sock, obj):
    payload = json.dumps(obj).encode("utf-8")
    frame = str(len(payload)).encode("ascii") + b":" + payload
    print(">>> " + json.dumps(obj)[:300])
    sock.sendall(frame)

def recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError(f"socket closed while expecting {n} bytes, got {len(buf)}")
        buf += chunk
    return buf

def recv_msg(sock, timeout=20):
    sock.settimeout(timeout)
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
    print("<<< " + text[:300] + ("..." if len(text) > 300 else ""))
    return json.loads(text)

def get_actor(sock):
    greeting = recv_msg(sock)
    send_msg(sock, {"to": "root", "type": "listTabs"})
    tabs = recv_msg(sock)
    sa = tabs.get("settingsActor")
    if not sa:
        raise RuntimeError("no settingsActor in listTabs reply")
    return sa

def get_setting(sock, actor, key):
    # include "value": None so the validator accepts the packet
    send_msg(sock, {"to": actor, "type": "getSetting",
                    "name": key, "value": None})
    return recv_msg(sock)

def set_setting(sock, actor, key, value):
    send_msg(sock, {"to": actor, "type": "setSetting",
                    "name": key, "value": value})
    return recv_msg(sock)

def clear_setting(sock, actor, key):
    send_msg(sock, {"to": actor, "type": "clearUserSetting",
                    "name": key, "value": None})
    return recv_msg(sock)

def main():
    if len(sys.argv) < 3:
        print("usage:")
        print("  python kaios_setting2.py read  <key>")
        print("  python kaios_setting2.py write <key> <json-value>")
        print("  python kaios_setting2.py clear <key>")
        sys.exit(1)

    cmd = sys.argv[1]
    key = sys.argv[2]
    value = sys.argv[3] if len(sys.argv) >= 4 else None

    s = socket.create_connection((HOST, PORT), timeout=15)
    print(f"connected to {HOST}:{PORT}")
    try:
        actor = get_actor(s)
        print("\nsettingsActor:", actor)

        print("\n--- current value ---")
        cur = get_setting(s, actor, key)
        print(json.dumps(cur, indent=2))

        if cmd == "read":
            print("\n(done, no write)")
        elif cmd == "write":
            print(f"\n--- writing {key} = {value!r} ---")
            r = set_setting(s, actor, key, value)
            print("write reply:", json.dumps(r, indent=2))
            print("\n--- verify ---")
            after = get_setting(s, actor, key)
            print(json.dumps(after, indent=2))
        elif cmd == "clear":
            print(f"\n--- clearing user value for {key} ---")
            r = clear_setting(s, actor, key)
            print("clear reply:", json.dumps(r, indent=2))
            print("\n--- verify ---")
            after = get_setting(s, actor, key)
            print(json.dumps(after, indent=2))
    finally:
        s.close()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
