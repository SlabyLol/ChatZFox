import socket
import threading

HOST = "0.0.0.0"
PORT = 5555

clients = []

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print("Dein scheiß n-wort server läuft...")

def broadcast(data, sender=None):
    for c in clients[:]:
        try:
            c.sendall(data)
        except:
            clients.remove(c)

def handle_client(client):
    while True:
        try:
            data = client.recv(4096)
            if not data:
                break
            broadcast(data)
        except:
            break
    client.close()
    clients.remove(client)

while True:
    client, addr = server.accept()
    print(Gefunden:", addr)
    clients.append(client)
    threading.Thread(target=handle_client, args=(client,), daemon=True).start()


