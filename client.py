import threading
from peer import Node, config, log, parse_command

thread_lock = threading.Lock()

def nodeRun(my_ip, node_id, dest_ip, dest_port):
    
    print("Enter 'join' to connect Tracker server or 'exit' to exit!")
    
    while True:
        command = input()
        if command.lower() == 'join':
            node = Node(node_id=node_id,
                rcv_port=dest_port,
                send_port=node_id,
                my_ip = my_ip,
                dest_ip = dest_ip,
                dest_port=dest_port)
            log_content = f"***************** CLIENT START! *****************"
            log(node_id=node.node_id, content=log_content)
            
            # print(node.files)
            node.enter_torrent()
            
            # We create a thread to periodically informs the tracker to tell it is still in the torrent.
            timer_thread = threading.Thread(target=node.inform_tracker_periodically, args=(config.constants.NODE_TIME_INTERVAL,))
            timer_thread.setDaemon(True)
            timer_thread.start()

            print("ENTER YOUR COMMAND (ex: <mode> <fileName>!")
            while True:
                nodeCommand = input()
                mode, filename = parse_command(nodeCommand)

                #################### send mode ####################
                if mode == 'send':
                    node.set_send_mode(filename=filename, file_path=(str(config.directory.node_files_dir) + "node" + str(node.node_id)), output_path=(config.directory.torrents_dir), flag=True)
                #################### download mode ####################
                elif mode == 'download':
                    t = threading.Thread(target=node.set_download_mode, args=(filename, ))
                    t.setDaemon(True)
                    t.start()
                #################### exit mode ####################
                elif mode == 'exit':
                    node.exit_torrent()
                    exit(0)
        elif command.lower() == 'exit':
            break
        else: 
            print("Enter 'join' to connect Tracker server or 'exit' to exit!")

def connect_tracker(my_ip, my_port):
    # Connect to another server
    tracker_host = config.constants.TRACKER_ADDR[0]
    tracker_port = config.constants.TRACKER_ADDR[1]
    # Create a node
    nodeRun(my_ip, my_port, tracker_host, tracker_port)
    
def start_peer(my_port):
    client_ip = '172.20.71.253'
    connect_tracker(client_ip, my_port)

if __name__ == '__main__':
    # Example usage: start peers sequentially or ensure a delay in client connection attempts
    threading.Thread(target=start_peer, args=(6002,)).start()