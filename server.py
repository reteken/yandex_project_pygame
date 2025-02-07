import socket
import threading
import json

clients = []


def handle_client(client_socket, addr):
    print(f"Подключился: {addr}")
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            messages = data.decode("utf-8").strip().split("\n")
            for msg in messages:
                if msg:
                    message = json.loads(msg)
                    broadcast(message, client_socket)
        except Exception as e:
            print(f"Ошибка от {addr}: {e}")
            break
    client_socket.close()
    if client_socket in clients:
        clients.remove(client_socket)
    print(f"Отключился: {addr}")


def broadcast(message, sender):
    for client in clients:
        if client != sender:
            try:
                client.sendall((json.dumps(message) + "\n").encode("utf-8"))
            except Exception as e:
                print("Ошибка рассылки:", e)


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Прослушиваем все интерфейсы на порту 5000
    server.bind(("", 5000))
    server.listen(5)
    print("Сервер запущен, прослушивание порта 5000")
    while True:
        client_socket, addr = server.accept()
        clients.append(client_socket)
        thread = threading.Thread(
            target=handle_client, args=(client_socket, addr), daemon=True
        )
        thread.start()


if __name__ == "__main__":
    main()
