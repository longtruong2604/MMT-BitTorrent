import socket
import threading
from peer import Node, config, log, parse_command

def nodeRun(my_ip, node_id, dest_ip, dest_port):
    node = Node(node_id=node_id,
                rcv_port=dest_port,
                send_port=node_id,
                my_ip = my_ip,
                dest_ip = dest_ip,
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
            t = threading.Thread(target=node.set_download_mode, args=(filename, ))
            t.setDaemon(True)
            t.start()
        #################### exit mode ####################
        elif mode == 'exit':
            node.exit_torrent()
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
    # Create a node
    nodeRun(my_ip, my_port, tracker_host, tracker_port)

def peer_client(my_ip, my_port, is_messenger=False):
    # Server
    master_host, master_port = config.constants.MASTER_ADDR[0], config.constants.MASTER_ADDR[1]
    connect_to_master(master_host, master_port, my_ip, my_port)
    
    # Delay to allow other servers to start up
    # time.sleep(10)
    
    # If this is the designated messenger peer, send an additional message
    if is_messenger:
        connect_tracker(my_ip, my_port)
    
def start_peer(my_port, is_messenger=False):
    client_ip = '10.230.81.18'
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((client_ip, my_port))
    server.listen(10)
    
    # Start the client functionality in a separate thread
    threading.Thread(target=peer_client, args=(client_ip, my_port, is_messenger)).start()

if __name__ == '__main__':
    # Example usage: start peers sequentially or ensure a delay in client connection attempts
    threading.Thread(target=start_peer, args=(6002, True)).start()