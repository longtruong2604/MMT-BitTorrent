import socket
import threading
from peer import Peer, config, log, parse_command

def peerRun(my_ip, peer_id, dest_ip, dest_port):
    peer = Peer(peer_id=peer_id,
                rcv_port=dest_port,
                send_port=peer_id,
                my_ip = my_ip,
                dest_ip = dest_ip,
                dest_port=dest_port)
    log_content = f"***************** Peer program started just right now! *****************"
    log(peer_id=peer.peer_id, content=log_content)
    peer.enter_torrent()

    # We create a thread to periodically informs the tracker to tell it is still in the torrent.
    timer_thread = threading.Thread(target=peer.inform_tracker_periodically, args=(config.constants.PEER_TIME_INTERVAL,))
    timer_thread.setDaemon(True)
    timer_thread.start()

    print("ENTER YOUR COMMAND!")
    while True:
        command = input()
        mode, filename = parse_command(command)

        #################### send mode ####################
        if mode == 'send':
            peer.set_send_mode(filename=filename)
        #################### download mode ####################
        elif mode == 'download':
            t = threading.Thread(target=peer.set_download_mode, args=(filename, ))
            t.setDaemon(True)
            t.start()
        #################### exit mode ####################
        elif mode == 'exit':
            peer.exit_torrent()
            exit(0)

def connect_to_master(master_host, master_port, my_ip, my_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((master_host, master_port))
        message = "Peer: " + str(my_ip) + ":" + str(my_port) + " is connected!"
        s.send(message.encode())
        response = s.recv(1024).decode()
        print("Server response:", response)
    return

def connect_tracker(my_ip, my_port):
    # Connect to another server
    tracker_host = config.constants.TRACKER_ADDR[0]
    tracker_port = config.constants.TRACKER_ADDR[1]
    # Create a peer
    peerRun(my_ip, my_port, tracker_host, tracker_port)

def peer_client(my_ip, my_port, is_messenger=False):
    # Server
    # master_host, master_port = config.constants.MASTER_ADDR[0], config.constants.MASTER_ADDR[1]
    # connect_to_master(master_host, master_port, my_ip, my_port)
    
    # Delay to allow other servers to start up
    # time.sleep(10)
    
    # If this is the designated messenger peer, send an additional message
    if is_messenger:
        connect_tracker(my_ip, my_port)
    
def start_peer(my_port, is_messenger=False):
    client_ip = '192.168.1.63'
    # server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # server.bind((client_ip, my_port))
    # server.listen(10)
    
    # Start the client functionality in a separate thread
    threading.Thread(target=peer_client, args=(client_ip, my_port, is_messenger)).start()

if __name__ == '__main__':
    # Example usage: start peers sequentially or ensure a delay in client connection attempts
    threading.Thread(target=start_peer, args=(6002, True)).start()