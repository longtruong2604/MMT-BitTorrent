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
    create_torrent(source_path, trackers=tracker_urls, output="./torrent/my_torrent_file.torrent")

def handle_peer(conn, peers):
    try:
        while True:
            data = conn.recv(1024).decode()
            if data.startswith("build"):
                build_torrent()
                conn.send("Torrent built successfully!".encode())
                break
            elif data.startswith("decode"):
                torrent_file_path = './torrent/my_torrent_file.torrent'
                tracker_url = get_tracker_url(torrent_file_path)
                if tracker_url:
                    result = "You are tracking at URL: " + tracker_url.decode('utf-8')
                    print(result)
                    conn.send(result.encode())
                else:
                    print("Tracker URL not found in the torrent file.")
                break
            else:
                print(f"Received message: {data}")
                conn.send(str(peers).encode())
                break
    except Exception as e:
        print(f"Error handling client input: {e}")
    finally:
        conn.close()

def connect_to_tracker(tracker_host, tracker_port):
    try:
        tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tracker_socket.connect((tracker_host, tracker_port))
        return tracker_socket
    except Exception as e:
        print(f"Error connecting to tracker server: {e}")
        return None

def start_master_server():
    host = config.constants.MASTER_ADDR[0]
    port = config.constants.MASTER_ADDR[1]
    print(host, port)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    
    peers = [(config.constants.MASTER_ADDR[0], 6002), ('192.168.1.118', 6003)]
    server_running = True
    
    print("Master server is running...")
    
    try:
        while server_running:
            conn, addr = server.accept()
            threading.Thread(target=handle_peer, args=(conn, peers)).start()
    finally:
        server.close()

# Start the master server
start_master_server()