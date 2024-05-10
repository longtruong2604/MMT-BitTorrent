import threading
from peer import Peer, config, log, parse_command

thread_lock = threading.Lock()

def peerRun(my_ip, peer_id, dest_ip, dest_port):
    
    print("Enter 'join' to connect Tracker server or 'exit' to exit!")
    
    while True:
        command = input()
        if command.lower() == 'join':
            peer = Peer(peer_id=peer_id,
                rcv_port=dest_port,
                send_port=peer_id,
                my_ip = my_ip,
                dest_ip = dest_ip,
                dest_port=dest_port)
            log_content = f"***************** CLIENT START! *****************"
            log(peer_id=peer.peer_id, content=log_content)
            
            # print(peer.files)
            peer.enter_torrent()
            
            # We create a thread to periodically informs the tracker to tell it is still in the torrent.
            timer_thread = threading.Thread(target=peer.inform_tracker_periodically, args=(config.constants.PEER_TIME_INTERVAL,))
            timer_thread.setDaemon(True)
            timer_thread.start()

            print("ENTER YOUR COMMAND (ex: <mode> <fileName>!")
            while True:
                peerCommand = input()
                mode, filename = parse_command(peerCommand)

                #################### send mode ####################
                if mode == 'send':
                    peer.set_send_mode(filename=filename, file_path=(str(config.directory.peers_dir) + "peer" + str(peer.peer_id)), output_path=(config.directory.torrents_dir), flag=True)
                #################### download mode ####################
                elif mode == 'download':
                    t = threading.Thread(target=peer.set_download_mode, args=(filename, ))
                    t.setDaemon(True)
                    t.start()
                #################### exit mode ####################
                elif mode == 'exit':
                    peer.exit_torrent()
                    exit(0)
        elif command.lower() == 'exit':
            break
        else: 
            print("Enter 'join' to connect Tracker server or 'exit' to exit!")

def connect_tracker(my_ip, my_port):
    # Connect to another server
    tracker_host = config.constants.TRACKER_ADDR[0]
    tracker_port = config.constants.TRACKER_ADDR[1]
    # Create a peer
    peerRun(my_ip, my_port, tracker_host, tracker_port)
    
def start_peer(my_port):
    client_ip = '172.20.71.253'
    connect_tracker(client_ip, my_port)

if __name__ == '__main__':
    # Example usage: start peers sequentially or ensure a delay in client connection attempts
    threading.Thread(target=start_peer, args=(6002,)).start()