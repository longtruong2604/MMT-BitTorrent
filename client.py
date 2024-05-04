import socket
import time
import threading
from node import Node, config, generate_random_port, free_socket, set_socket, log, parse_command

def connect_to_master(master_host, master_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((master_host, master_port))
        peer_list = eval(s.recv(1024).decode())
    return peer_list

def send_message(peer, message):
    success = False
    attempts = 0
    while not success and attempts < 5:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(peer)
                s.send(message.encode())
                success = True
        except ConnectionRefusedError:
            time.sleep(2)  # Wait for 2 seconds before retrying
            attempts += 1
    if not success:
        print(f"Failed to connect to {peer} after {attempts} attempts.")

def peer_client(my_port, is_messenger=False):
    # Server
    master_host, master_port = '192.168.1.119', 6001
    peers = connect_to_master(master_host, master_port)
    peers = [peer for peer in peers if peer[1] != my_port]
    
    # Delay to allow other servers to start up
    time.sleep(10)

    # Send hello to all peers
    for peer in peers:
        send_message(peer, f"Con me may Long")
    
    # If this is the designated messenger peer, send an additional message
    if is_messenger:
        for peer in peers:
            send_message(peer, f"Special message from Peer {my_port}")

    # Creating and running a Node instance for BitTorrent functionality
    node = Node(node_id=my_port, rcv_port=generate_random_port(), send_port=generate_random_port())
    node.enter_torrent()

    # We create a thread to periodically inform the tracker to tell it is still in the torrent.
    timer_thread = threading.Thread(target=node.inform_tracker_periodically, args=(config.constants.NODE_TIME_INTERVAL,))
    timer_thread.setDaemon(True)
    timer_thread.start()

    print("ENTER YOUR COMMAND!")
    while True:
        command = input()
        mode, filename = parse_command(command)

        #################### send mode ####################
        if mode == 'send':
            node.set_send_mode(filename=filename)
        #################### download mode ####################
        elif mode == 'download':
            t = threading.Thread(target=node.set_download_mode, args=(filename,))
            t.setDaemon(True)
            t.start()
        #################### exit mode ####################
        elif mode == 'exit':
            node.exit_torrent()
            exit(0)

def start_peer(my_port, is_messenger=False):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('192.168.1.119', my_port))
    server.listen(10)
    
    # Start the client functionality in a separate thread
    threading.Thread(target=peer_client, args=(my_port, is_messenger)).start()

    # Accept messages from other peers
    try:
        while True:
            conn, addr = server.accept()
            message = conn.recv(1024).decode()
            print(f"Received on port {my_port}: {message}")
            conn.close()
    finally:
        server.close()

# Example usage: start peers sequentially or ensure a delay in client connection attempts
threading.Thread(target=start_peer, args=(6002, True)).start()