"""
nat64_proxy.py - Lightweight local forward proxy for IPv6-only environments.

Runs an HTTP CONNECT proxy on 127.0.0.1:8089. For any CONNECT request to a host
without reachable IPv4, it queries public DNS64 servers (nat64.net) and routes
TCP traffic through IPv6 NAT64 gateways.
"""

import ipaddress
import select
import socket
import struct
import sys
import threading

DNS64_SERVERS = ["2a00:1098:2b::1", "2a01:4f9:c010:3f02::1", "2a00:1098:2c::1"]
CACHE: dict[str, str] = {
    "github.com": "2a01:4f9:c010:3f02:64:0:141a:9cd7",
    "api.github.com": "2a00:1098:2b::1:141a:9cd2",
    "objects.githubusercontent.com": "2a00:1098:2b::1:8c52:724f",
    "raw.githubusercontent.com": "2a00:1098:2b::1:b9c7:6d85",
}


def resolve_nat64(host: str) -> str | None:
    if host in CACHE:
        return CACHE[host]

    # Construct standard DNS AAAA query packet
    header = struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)
    qname = b"".join(bytes([len(p)]) + p.encode() for p in host.split(".")) + b"\x00"
    q = header + qname + struct.pack(">HH", 28, 1)

    for dns_server in DNS64_SERVERS:
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            sock.settimeout(2.5)
            sock.sendto(q, (dns_server, 53))
            data, _ = sock.recvfrom(2048)
            ans_count = struct.unpack(">H", data[6:8])[0]
            if ans_count == 0:
                continue

            idx = 12 + len(qname) + 4
            for _ in range(ans_count):
                if idx >= len(data):
                    break
                if data[idx] & 0xC0 == 0xC0:
                    idx += 2
                else:
                    while idx < len(data) and data[idx] != 0:
                        idx += data[idx] + 1
                    idx += 1
                if idx + 10 > len(data):
                    break
                atype, _, _, rdlen = struct.unpack(">HHIH", data[idx : idx + 10])
                idx += 10
                if atype == 28 and rdlen == 16 and idx + 16 <= len(data):
                    ipv6 = str(ipaddress.IPv6Address(data[idx : idx + 16]))
                    CACHE[host] = ipv6
                    return ipv6
                idx += rdlen
        except Exception:
            continue
    return None


def handle_client(client_sock: socket.socket) -> None:
    try:
        req = b""
        while b"\r\n\r\n" not in req:
            chunk = client_sock.recv(4096)
            if not chunk:
                break
            req += chunk

        lines = req.split(b"\r\n")
        if not lines or not lines[0].startswith(b"CONNECT"):
            client_sock.close()
            return

        target = lines[0].split()[1].decode("utf-8", "ignore")
        if ":" in target:
            host, port_s = target.split(":", 1)
            port = int(port_s)
        else:
            host, port = target, 443

        remote_ip = resolve_nat64(host)
        if not remote_ip:
            client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            return

        remote_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        remote_sock.settimeout(10.0)
        remote_sock.connect((remote_ip, port))
        remote_sock.settimeout(None)

        client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

        sockets = [client_sock, remote_sock]
        while True:
            r, _, _ = select.select(sockets, [], [], 60)
            if not r:
                break
            closed = False
            for s in r:
                other = remote_sock if s is client_sock else client_sock
                try:
                    data = s.recv(32768)
                    if not data:
                        closed = True
                        break
                    other.sendall(data)
                except Exception:
                    closed = True
                    break
            if closed:
                break
    except Exception:
        pass
    finally:
        try:
            client_sock.close()
        except Exception:
            pass


def main(port: int = 8089) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(128)
    print(f"NAT64 proxy running on 127.0.0.1:{port}", flush=True)

    while True:
        try:
            client_sock, _ = srv.accept()
            t = threading.Thread(target=handle_client, args=(client_sock,), daemon=True)
            t.start()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Accept error: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8089
    main(port)
