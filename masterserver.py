import socket
import threading
from tracker import Tracker

def handle_peer(conn, peers):
    # Send the list of peers to the connected peer
    conn.send(str(peers).encode())
    conn.close()

def start_master_server():
    host = '192.168.1.119'
    print(socket.gethostname())
    port = 6001
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    
    peers = [('192.168.1.119', 6002), ('192.168.1.118', 6003)]
    
    print("Master server is running...")
    try:
        tracker = Tracker()
        threading.Thread(target=tracker.run).start()
        
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_peer, args=(conn, peers)).start()
    finally:
        server.close()

# Start the master server in a background thread
threading.Thread(target=start_master_server).start()
