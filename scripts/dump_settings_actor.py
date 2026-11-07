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
            raise EOFError(f"socket closed, wanted {n}, got {len(buf)}")
        buf += chunk
    return buf

def recv_msg(sock, timeout=30):
    sock.settimeout(timeout)
    length_bytes = b""
    while True:
        ch = recv_exact(sock, 1)
        if ch == b":":
            break
        if not ch.isdigit():
            raise ValueError(f"unexpected byte in prefix: {ch!r}")
        length_bytes += ch
    n = int(length_bytes.decode("ascii"))
    payload = recv_exact(sock, n)
    text = payload.decode("utf-8", "replace")
    print("<<< " + text[:300] + ("..." if len(text) > 300 else ""))
    return json.loads(text)

def main():
    s = socket.create_connection((HOST, PORT), timeout=15)
    print("connected")

    # greeting
    recv_msg(s)

    # listTabs to get settingsActor
    send_msg(s, {"to": "root", "type": "listTabs"})
    tabs = recv_msg(s)
    sa = tabs["settingsActor"]
    print("settingsActor:", sa)

    # 1. Try the actor's own introspection
    for probe in [
        {"to": sa, "type": "getRequestTypes"},
        {"to": sa, "type": "getActor"},
        {"to": sa, "type": "describe"},
        {"to": sa, "type": "getDefinition"},
        {"to": sa, "type": "help"},
    ]:
        try:
            send_msg(s, probe)
            r = recv_msg(s)
            print(f"  probe {probe['type']} ->", json.dumps(r)[:400])
        except Exception as e:
            print(f"  probe {probe['type']} failed: {e}")

    # 2. ask the device actor to list actors
    da = tabs.get("deviceActor")
    if da:
        print("\n--- deviceActor probe ---")
        send_msg(s, {"to": da, "type": "getDescription"})
        try:
            print(json.dumps(recv_msg(s), indent=2)[:1000])
        except Exception as e:
            print("device description err:", e)

    # 3. ask the webappsActor to describe the settings actor
    wa = tabs.get("webappsActor")
    if wa:
        print("\n--- webappsActor probe ---")
        send_msg(s, {"to": wa, "type": "listRunningApps"})
        try:
            print(json.dumps(recv_msg(s), indent=2)[:2000])
        except Exception as e:
            print("webapps err:", e)

    s.close()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
