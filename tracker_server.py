import socket
import threading
from tracker import Tracker

def handle_connection(conn, addr):
    conn.send("Hello client, i'm tracker".encode())
    conn.close()

def start_tracker_server():
    host = '192.168.1.139'
    port = 9090
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    
    print("Tracker server is running...")
    try:
        tracker = Tracker()
        threading.Thread(target=tracker.run).start()
        
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_connection, args=(conn, addr)).start()
            pass
    finally:
        server.close()

# Start the master server in a background thread
start_tracker_server()
