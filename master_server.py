import socket
import threading
from py3createtorrent import create_torrent
import bencodepy
from configs import CFG, Config
config = Config.from_json(CFG)

def get_tracker_url(torrent_file_path):
    with open(torrent_file_path, 'rb') as f:
        torrent_data = f.read()

        decoded_torrent = bencodepy.decode(torrent_data)
        
        if b'announce' in decoded_torrent:
            tracker_url = decoded_torrent[b'announce']
            return tracker_url
        else:
            return None

def build_torrent():
    source_path = "./"
    tracker_urls = ["udp://172.20.41.134:9090"]
    create_torrent(source_path, trackers=tracker_urls, output="./torrents/my_torrent_file.torrent")

def handle_peer(conn, addr):
    try:
        while True:
            data = conn.recv(1024).decode()
            print(data)
            result = "You are connecting at server http://" + str(config.constants.MASTER_ADDR[0]) + ":" + str(config.constants.MASTER_ADDR[1])
            conn.send(result.encode())
            break
    except Exception as e:
        print(f"Error handling client input: {e}")
    finally:
        conn.close()

def start_master_server():
    host = config.constants.MASTER_ADDR[0]
    port = config.constants.MASTER_ADDR[1]
    print(host, port)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    
    # peers = [(config.constants.MASTER_ADDR[0], 6002), ('192.168.1.118', 6003)]
    server_running = True
    
    print("Master server is running...")
    
    try:
        while server_running:
            conn, addr = server.accept()
            threading.Thread(target=handle_peer, args=(conn, addr)).start()
    finally:
        server.close()

if __name__ == '__main__':
    # Start the master server
    start_master_server()