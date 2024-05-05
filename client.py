import socket
import threading
from node import Node, config, generate_random_port, free_socket, set_socket, log, parse_command

def nodeRun(node_id, ip, dest_port):
    node = Node(node_id=node_id,
                rcv_port=generate_random_port(),
                send_port=generate_random_port(),
                ip = ip,
                dest_port=dest_port)
    log_content = f"***************** Node program started just right now! *****************"
    log(node_id=node.node_id, content=log_content)
    node.enter_torrent()

    # We create a thread to periodically informs the tracker to tell it is still in the torrent.
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

def connect_to_master(master_host, master_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((master_host, master_port))
        s.send("123".encode())
        peer_list = eval(s.recv(1024).decode())
        print(peer_list)
    return peer_list

def send_message(master_host, master_port, message, my_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((master_host, master_port))
        s.send(message.encode())
        response = s.recv(1024).decode()
        print("Server response:", response)
        if response.startswith("You are tracking at URL:"):
            # Connect to another server
            tracker_host = '192.168.1.139'
            tracker_port = 9090
            # Create a node
            nodeRun(my_port, tracker_host, tracker_port)

def peer_client(my_port, is_messenger=False):
    # Server
    master_host, master_port = '192.168.1.139', 8080
    peers = connect_to_master(master_host, master_port)
    peers = [peer for peer in peers if peer[1] == my_port]
    
    # Delay to allow other servers to start up
    # time.sleep(10)

    # Send hello to all peers
    # for peer in peers:
        # send_message(peer, f"Con me may Long")
    
    # If this is the designated messenger peer, send an additional message
    if is_messenger:
        send_message(master_host, master_port, "decode", my_port)
    
def start_peer(my_port, is_messenger=False):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('192.168.1.139', my_port))
    server.listen(10)
    
    # Start the client functionality in a separate thread
    threading.Thread(target=peer_client, args=(my_port, is_messenger)).start()

    # Accept messages from other peers
    # try:
    #     while True:
    #         conn, addr = server.accept()
    #         message = conn.recv(1024).decode()
    #         print(f"Received on port {my_port}: {message}")
    #         conn.close()
    # finally:
    #     server.close()

# Example usage: start peers sequentially or ensure a delay in client connection attempts
threading.Thread(target=start_peer, args=(6002, True)).start()