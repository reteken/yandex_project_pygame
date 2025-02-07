import socket
import json
import threading


class NetworkClient:
    def __init__(self, server_ip, port=5000):
        self.server_ip = server_ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((server_ip, port))
        self.sock.setblocking(False)
        self.received_messages = []
        self.running = True
        self.thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.thread.start()

    def receive_loop(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if data:
                    buffer += data.decode("utf-8")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if line:
                            self.received_messages.append(json.loads(line))
            except BlockingIOError:
                continue
            except Exception as e:
                print("Receive error:", e)
                self.running = False

    def send(self, message):
        try:
            self.sock.sendall((json.dumps(message) + "\n").encode("utf-8"))
        except Exception as e:
            print("Send error:", e)

    def close(self):
        self.running = False
        self.sock.close()
