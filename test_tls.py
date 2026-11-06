import socket
import ssl
import certifi

host = "ac-oj3ovqb-shard-00-00.rgisopk.mongodb.net"
port = 27017

try:
    context = ssl.create_default_context(cafile=certifi.where())

    with socket.create_connection((host, port), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=host) as tls:
            print("TLS connection successful!")
            print("TLS Version:", tls.version())
            print("Cipher:", tls.cipher())

except Exception as e:
    print("TLS connection failed:")
    print(type(e).__name__, e)