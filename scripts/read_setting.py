import socket, json, sys

HOST = "127.0.0.1"
PORT = 6000

def send(sock, obj):
    data = json.dumps(obj).encode("utf-8")
    # length-prefixed: "N:json"
    sock.sendall(str(len(data)).encode("ascii") + b":" + data)

def recv_one(sock, buf):
    while True:
        # try to parse: digits, then ':'
        while b":" not in buf[0]:
            chunk = sock.recv(65536)
            if not chunk:
                raise EOFError("socket closed")
            buf[0] += chunk
        col = buf[0].index(b":")
        try:
            n = int(buf[0][:col])
        except ValueError:
            # not a length prefix; keep reading
            chunk = sock.recv(65536)
            if not chunk:
                raise EOFError("socket closed")
            buf[0] += chunk
            continue
        if len(buf[0]) - col - 1 < n:
            chunk = sock.recv(65536)
            if not chunk:
                raise EOFError("socket closed")
            buf[0] += chunk
            continue
        payload = buf[0][col+1:col+1+n]
        rest = buf[0][col+1+n:]
        buf[0] = rest
        return json.loads(payload.decode("utf-8"))

def main():
    s = socket.create_connection((HOST, PORT), timeout=15)
    buf = [b""]

    # 1. listTabs to get actors
    send(s, {"to": "root", "type": "listTabs"})
    reply = recv_one(s, buf)
    print("listTabs keys:", list(reply.keys()))
    print("settingsActor:", reply.get("settingsActor"))
    print("deviceActor:", reply.get("deviceActor"))
    print("webappsActor:", reply.get("webappsActor"))

    sa = reply.get("settingsActor")
    if not sa:
        print("no settingsActor — aborting")
        return

    # 2. ask the settingsActor to get our key
    send(s, {"to": sa, "type": "get", "request": {"home.customization.longpress": None}})
    reply2 = recv_one(s, buf)
    print("\nsettingsActor get reply:")
    print(json.dumps(reply2, indent=2, sort_keys=True))

    # 3. ask the settingsActor for its description to see what it supports
    send(s, {"to": sa, "type": "requestTypes"})
    try:
        reply3 = recv_one(s, buf)
        print("\nsettingsActor requestTypes reply:")
        print(json.dumps(reply3, indent=2, sort_keys=True))
    except Exception as e:
        print("requestTypes error:", e)

    s.close()

if __name__ == "__main__":
    main()
