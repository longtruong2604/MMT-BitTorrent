import socket
import threading
from tracker import Tracker
from configs import CFG, Config
config = Config.from_json(CFG)

# def handle_connection(conn, addr):
#     conn.send("Hello client, i'm tracker".encode())
#     conn.close()

def start_tracker_server():
    host = config.constants.TRACKER_ADDR[0]
    port = config.constants.TRACKER_ADDR[1]
    print(host, port)
    # server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # server.bind((host, port))
    # server.listen()
    
    print("Tracker server is running...")
    # try:
    tracker = Tracker()
    threading.Thread(target=tracker.run).start()
        
        # while True:
        #     conn, addr = server.accept()
        #     threading.Thread(target=handle_connection, args=(conn, addr)).start()
        #     pass
    # finally:
        # server.close()

if __name__ == '__main__':
    # Start the master server in a background thread
    start_tracker_server()
