import socket, json, sys, traceback

HOST = "127.0.0.1"
PORT = 6000
KEY = "home.customization.longpress"

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

def recv_msg(sock, timeout=20):
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
    print("<<< " + text[:400] + ("..." if len(text) > 400 else ""))
    return json.loads(text)

def get_actor(sock):
    recv_msg(sock)
    send_msg(sock, {"to": "root", "type": "listTabs"})
    tabs = recv_msg(sock)
    return tabs["settingsActor"]

# Try several candidate packet shapes for getSetting
CANDIDATES = [
    ("A. flat, key=name, value=null",
     {"type": "getSetting", "name": KEY, "value": None}),
    ("B. flat, only value (the string)",
     {"type": "getSetting", "value": KEY}),
    ("C. nested request.value",
     {"type": "getSetting", "request": {"value": KEY}}),
    ("D. nested request.name + value",
     {"type": "getSetting", "request": {"name": KEY, "value": None}}),
    ("E. flat, key=key",
     {"type": "getSetting", "key": KEY}),
    ("F. flat, args array",
     {"type": "getSetting", "args": [KEY]}),
    ("G. nested request with single arg 'name'",
     {"type": "getSetting", "request": {"name": KEY}}),
    ("H. nested request with 'value' plus empty response",
     {"type": "getSetting", "request": {"value": KEY}, "response": {}}),
]

def main():
    for label, payload in CANDIDATES:
        print("\n" + "=" * 70)
        print("Trying:", label)
        print("=" * 70)
        s = socket.create_connection((HOST, PORT), timeout=15)
        try:
            actor = get_actor(s)
            msg = {"to": actor}
            msg.update(payload)
            send_msg(s, msg)
            reply = recv_msg(s)
            if "error" in reply:
                print("  >>> FAILED:", reply.get("message"))
            else:
                print("  >>> SUCCESS:", json.dumps(reply))
                print("\n*** found the working shape:", label)
                print(json.dumps(msg, indent=2))
                s.close()
                return
        except Exception as e:
            print("  >>> EXCEPTION:", e)
        finally:
            try:
                s.close()
            except Exception:
                pass

    print("\nNone of the candidates worked. Need to look at source again.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
