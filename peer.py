# built-in libraries
from utils import *
import argparse
from threading import Thread, Timer
from operator import itemgetter
import datetime
import time
from itertools import groupby
import mmap
import warnings
import bencodepy
import hashlib

warnings.filterwarnings("ignore")

# implemented classes
from configs import CFG, Config
config = Config.from_json(CFG)
from messages.message import Message
from messages.node2tracker import Node2Tracker
from messages.node2node import Node2Node
from messages.chunk_sharing import ChunkSharing
from segment import UDPSegment

next_call = time.time()


class Node:
    def __init__(self, node_id: int, rcv_port: int, send_port: int, my_ip: str, dest_ip: str, dest_port: int):
        self.node_id = node_id
        # self.rcv_socket = set_socket(dest_ip, rcv_port)
        self.send_socket = set_socket(my_ip, send_port)
        self.check_nodes_file(config.directory.node_files_dir + 'node' + str(self.node_id))
        self.is_in_send_mode = False    # is thread uploading a file or not
        self.downloaded_files = {}
        self.running = True
        self.my_ip = my_ip
        self.dest_ip = dest_ip
        self.dest_port = dest_port
        
    def get_file_info(self, file_path: str):
        with open(file_path, 'rb') as f:
            file_data = f.read()
            file_hash = hashlib.sha1(file_data).digest()
            return {
                'name': os.path.basename(file_path),
                'length': os.path.getsize(file_path),
                'pieces': [file_hash]
            }

    def get_directory_info(self, directory_path: str):
        files_info = []
        for root, dirs, files in os.walk(directory_path):
            for file_name in files:
                file_name = os.path.join(root, file_name)
                file_info = self.get_file_info(file_name)
                file_info['path'] = os.path.relpath(file_name, directory_path)
                files_info.append(file_info)
        return {
            'name': os.path.basename(directory_path),
            'files': files_info,
            'piece length': 2**20  # 1 MB piece size (adjust as needed)
        }

    def create_torrent_from_info(self, info: str, output_path: str, flag: bool):
        # Calculate info hash
        info_bencoded = bencodepy.encode(info)
        info_hash = hashlib.sha1(info_bencoded).digest()

        if flag:
            # Create the torrent dictionary
            torrent_dict = {
                'info': info,
                'announce': 'udp://' + str(config.constants.TRACKER_ADDR[0]) + ":" + str(config.constants.TRACKER_ADDR[1]),  # Tracker URL
                'creation date': 1620123456,  # Unix timestamp of creation date
                'created by': 'My Torrent Creator',  # Your name or software name
                'comment': 'This is a test torrent file',  # Any comment
                'info_hash': info_hash
            }

            # Encode the torrent dictionary using bencode
            torrent_data = bencodepy.encode(torrent_dict)

            # Write the torrent data to the output file
            with open(output_path, 'wb') as f:
                f.write(torrent_data)
            
        return info_hash.hex()
    
    def decode_torrent_infohash(self, torrent_file: str):
        with open(torrent_file, 'rb') as f:
            torrent_data = f.read()
            torrent_info = bencodepy.decode(torrent_data)
            # Extract necessary information
            infoHash = torrent_info[b'info_hash']
        return infoHash.hex()
    
    def decode_torrent_name(self, torrent_file: str):
        with open(torrent_file, 'rb') as f:
            torrent_data = f.read()
            torrent_info = bencodepy.decode(torrent_data)

            # Extract necessary information
            name_bytes = torrent_info[b'info'][b'name']
            name = name_bytes.decode()
        return name
    
    def traverse_directory(self, directory_path: str):
        file_list = []

        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append(file_path)

        return file_list
    
    def check_file_in_nested_list(self, lst: list, target: str):
        for item in lst:
            if isinstance(item, list):
                if self.check_file_in_nested_list(item, target):
                    return True
            else:
                if item == target:
                    return True
        return False
    
    def check_extension(self, filename, extension):
        _, file_extension = os.path.splitext(filename)
        if file_extension == extension:
            return True
        return False

    def send_segment(self, sock: socket.socket, data: bytes, addr: tuple):
        ip, dest_port = addr
        segment = UDPSegment(src_port=sock.getsockname()[1],
                             dest_port=dest_port,
                             data=data)
        encrypted_data = segment.data
        sock.sendto(encrypted_data, addr)

    def split_file_to_chunks(self, file_path: str, rng: tuple) -> list:
        with open(file_path, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)[rng[0]: rng[1]]
            piece_size = config.constants.CHUNK_PIECES_SIZE
            return [mm[p: p + piece_size] for p in range(0, rng[1] - rng[0], piece_size)]

    def reassemble_file(self, chunks: list, file_path: str):
        with open(file_path, "bw+") as f:
            for ch in chunks:
                f.write(ch)
            f.flush()
            f.close()

    def send_chunk(self, filename: str, rng: tuple, dest_node_ip: str ,dest_node_id: int, dest_port: int, infoHash: str):
        file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        chunk_pieces = self.split_file_to_chunks(file_path=file_path,
                                                 rng=rng)
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        for idx, p in enumerate(chunk_pieces):
            msg = ChunkSharing(src_node_id=self.node_id,
                               dest_node_id=dest_node_id,
                               filename=filename,
                               range=rng,
                               idx=idx,
                               chunk=p)
            log_content = f"The {idx}/{len(chunk_pieces)} has been sent!"
            log(node_id=self.node_id, content=log_content)
            self.send_segment(sock=temp_sock,
                              data=Message.encode(msg),
                              addr=(dest_node_ip, dest_port))
        # now let's tell the neighboring peer that sending has finished (idx = -1)
        msg = ChunkSharing(src_node_id=self.node_id,
                           dest_node_id=dest_node_id,
                           filename=filename,
                           range=rng)
        self.send_segment(sock=temp_sock,
                          data=Message.encode(msg),
                          addr=(dest_node_ip, dest_port))

        log_content = "The process of sending a chunk to node{} of file {} has finished!".format(dest_node_id, filename)
        log(node_id=self.node_id, content=log_content)

        msg = Node2Tracker(node_id=self.node_id,
                           mode=config.tracker_requests_mode.UPDATE,
                           filename=filename,
                           infoHash=infoHash)

        self.send_segment(sock=temp_sock,
                          data=Message.encode(msg),
                          addr=tuple((self.dest_ip, self.dest_port)))

        free_socket(temp_sock)

    def handle_requests(self, msg: dict, addr: tuple, infoHash: str):
        # 1. asks the node about a file size
        if "size" in msg.keys() and msg["size"] == -1:
            self.tell_file_size(msg=msg, addr=addr)
        # 2. Wants a chunk of a file
        elif "range" in msg.keys() and msg["chunk"] is None:
            self.send_chunk(filename=msg["filename"],
                            rng=msg["range"],
                            dest_node_ip=addr[0],
                            dest_node_id=msg["src_node_id"],
                            dest_port=addr[1],
                            infoHash=infoHash)

    def listen(self, infoHash: str):
        while True:
            try:
                data, addr = self.send_socket.recvfrom(config.constants.BUFFER_SIZE)
                msg = Message.decode(data)
                self.handle_requests(msg=msg, addr=addr, infoHash=infoHash)
            except OSError as e:
                if e.errno == 10038:
                    break  # Exit the loop and terminate the thread
                else:
                    log_content = f"Socket error: {e}"
                    log(node_id=self.node_id, content=log_content)

    def set_send_mode(self, filename: str, file_path: str, output_path: str, flag: bool):
        if self.check_file_in_nested_list(self.files, filename) == False:
            log(node_id=self.node_id,
                content=f"You don't have {filename}")
            return

        # Check file or dir
        # LOOP - Hash to tracker of dir
        source_path = f"{file_path}\{filename}"
        
        if (os.path.isfile(source_path)):
            in_send_mode = False
            file_info = self.get_file_info(source_path)
            infoHash = self.create_torrent_from_info(file_info, f"{output_path}{filename}.torrent", flag)
            
            message = Node2Tracker(node_id=self.node_id,
                               mode=config.tracker_requests_mode.OWN,
                               filename=filename,
                               infoHash=infoHash)

            self.send_segment(sock=self.send_socket,
                          data=message.encode(),
                          addr=tuple((self.dest_ip, self.dest_port)))
        
            if in_send_mode:    # has been already in send(upload) mode
                log_content = f"You are already in SEND(upload) mode!"
                log(node_id=self.node_id, content=log_content)
                return
            else:
                in_send_mode = True
                log_content = f"DONE!"
                log(node_id=self.node_id, content=log_content)
                t = Thread(target=self.listen, args=(infoHash,))
                t.setDaemon(True)
                t.start()
                
        elif (os.path.isdir(source_path)):
            in_send_mode = False
            # Get list of all files in the directory
            file_list = self.traverse_directory(source_path)                
            
            directory_info = self.get_directory_info(source_path)
            infoHash = self.create_torrent_from_info(directory_info, f"{output_path}{filename}.torrent", flag)
            
            message = Node2Tracker(node_id=self.node_id,
                               mode=config.tracker_requests_mode.OWN,
                               filename=filename,
                               infoHash=infoHash)

            self.send_segment(sock=self.send_socket,
                          data=message.encode(),
                          addr=tuple((self.dest_ip, self.dest_port)))
        
            if in_send_mode:    # has been already in send(upload) mode
                log_content = f"You are already in SEND(upload) mode!"
                log(node_id=self.node_id, content=log_content)
                return
            else:
                in_send_mode = True
                log_content = f"DONE!"
                log(node_id=self.node_id, content=log_content)
                t = Thread(target=self.listen, args=(infoHash,))
                t.setDaemon(True)
                t.start()
                
            for file in file_list:
                self.set_send_mode(os.path.basename(file), os.path.dirname(file), output_path, False)

    def ask_file_size(self, filename: str, file_owner: tuple) -> int:
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        dest_node = file_owner[0]

        msg = Node2Node(src_node_id=self.node_id,
                        dest_node_id=dest_node["node_id"],
                        filename=filename)
        self.send_segment(sock=temp_sock,
                          data=msg.encode(),
                          addr=tuple(dest_node["addr"]))
        while True:
            data, addr = temp_sock.recvfrom(config.constants.BUFFER_SIZE)
            dest_node_response = Message.decode(data)
            size = dest_node_response["size"]
            free_socket(temp_sock)

            return size

    def tell_file_size(self, msg: dict, addr: tuple):
        filename = msg["filename"]
        file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        file_size = os.stat(file_path).st_size
        response_msg = Node2Node(src_node_id=self.node_id,
                        dest_node_id=msg["src_node_id"],
                        filename=filename,
                        size=file_size)
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        self.send_segment(sock=temp_sock,
                          data=response_msg.encode(),
                          addr=addr)

        free_socket(temp_sock)

    def receive_chunk(self, filename: str, range: tuple, file_owner: tuple, infoHash: str):
        dest_node = file_owner[0]
        # we set idx of ChunkSharing to -1, because we want to tell it that we
        # need the chunk from it
        
        msg = ChunkSharing(src_node_id=self.node_id,
                           dest_node_id=dest_node["node_id"],
                           filename=filename,
                           range=range)
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        self.send_segment(sock=temp_sock,
                          data=msg.encode(),
                          addr=tuple(dest_node["addr"]))
        log_content = "Send a request for a chunk of {0} for node{1}".format(filename, dest_node["node_id"])
        log(node_id=self.node_id, content=log_content)

        while True:
            data, addr = temp_sock.recvfrom(config.constants.BUFFER_SIZE)
            msg = Message.decode(data) # but this is not a simple message, it contains chunk's bytes
            if msg["idx"] == -1: # end of the file
                free_socket(temp_sock)
                return

            self.downloaded_files[infoHash].append(msg)

    def sort_downloaded_chunks(self, filename: str, infoHash) -> list:
        sort_result_by_range = sorted(self.downloaded_files[infoHash],
                                      key=itemgetter("range"))
        group_by_range = groupby(sort_result_by_range,
                                 key=lambda i: i["range"])
        sorted_downloaded_chunks = []
        for key, value in group_by_range:
            value_sorted_by_idx = sorted(list(value),
                                         key=itemgetter("idx"))
            sorted_downloaded_chunks.append(value_sorted_by_idx)

        return sorted_downloaded_chunks

    def split_file_owners(self, file_owners: list, filename: str, infoHash: str):
        owners = []
        for owner in file_owners:
            if owner[0]['node_id'] != self.node_id:
                owners.append(owner)
            elif owner[0]['node_id'] == self.node_id:
                log_content = f"You already have this file!"
                log(node_id=self.node_id, content=log_content)
                return
        print(owners)
        if len(owners) == 0:
            log_content = f"No one has {filename}"
            log(node_id=self.node_id, content=log_content)
            return
        # sort owners based on their sending frequency
        owners = sorted(owners, key=lambda x: x[1], reverse=True)

        to_be_used_owners = owners[:config.constants.MAX_SPLITTNES_RATE]
        # 1. first ask the size of the file from peers
        log_content = f"You are going to download {filename} from Node(s) {[o[0]['node_id'] for o in to_be_used_owners]}"
        log(node_id=self.node_id, content=log_content)
        
        file_size = self.ask_file_size(filename=filename, file_owner=to_be_used_owners[0])
        log_content = f"You are downloading {filename} with the size of {file_size} bytes"
        log(node_id=self.node_id, content=log_content)

        # 2. Now, we know the size, let's split it equally among peers to download chunks of it from them
        step = file_size / len(to_be_used_owners)
        chunks_ranges = [(round(step*i), round(step*(i+1))) for i in range(len(to_be_used_owners))]
        

        # 3. Create a thread for each neighbor peer to get a chunk from it
        self.downloaded_files[infoHash] = []
        neighboring_peers_threads = []
        for idx, obj in enumerate(to_be_used_owners):
            t = Thread(target=self.receive_chunk, args=(filename, chunks_ranges[idx], obj, infoHash))
            t.setDaemon(True)
            t.start()
            neighboring_peers_threads.append(t)
        for t in neighboring_peers_threads:
            t.join()

        log_content = "All the chunks of {} has downloaded!".format(filename)
        log(node_id=self.node_id, content=log_content)

        # 4. Now we have downloaded all the chunks of the file. It's time to sort them.
        sorted_chunks = self.sort_downloaded_chunks(filename=filename, infoHash=infoHash)
        log_content = f"All the pieces of the {filename} is now sorted and ready to be reassembled."
        log(node_id=self.node_id, content=log_content)

        # 5. Finally, we assemble the chunks to re-build the file
        total_file = []
        file_path = f"{config.directory.node_files_dir}node{self.node_id}/{filename}"
        for chunk in sorted_chunks:
            for piece in chunk:
                total_file.append(piece["chunk"])
        self.reassemble_file(chunks=total_file,
                             file_path=file_path)
        log_content = f"{filename} has successfully downloaded!"
        log(node_id=self.node_id, content=log_content)
        self.files.append(filename)

    def set_download_mode(self, filename: str):
        # Process the file torrent
        file_path = f"{config.directory.torrents_dir}"
        
        if os.path.exists(f"{file_path}/{filename}") and (self.check_extension(filename,".torrent")):
            filename_decode = self.decode_torrent_name(f"{file_path}/{filename}")
            infoHash_decode = self.decode_torrent_infohash(f"{file_path}/{filename}")
            log_content = f"You just started to download {filename}. Let's search it in torrent!"
            log(node_id=self.node_id, content=log_content)
            tracker_response = self.search_torrent(filename=filename_decode, infoHash= infoHash_decode)
            file_owners = tracker_response['search_result']
            
            # Check filename is file or dir
            # Create directory with filename
            # LOOP if filename is dir
            
            
            self.split_file_owners(file_owners=file_owners, filename=filename_decode, infoHash = infoHash_decode)
        else: 
            log_content = f"You don't have this file or the file format is incorrect (.torrent)!"
            log(node_id=self.node_id, content=log_content)
            return

    def search_torrent(self, filename: str, infoHash: str) -> dict:
        msg = Node2Tracker(node_id=self.node_id,
                           mode=config.tracker_requests_mode.NEED,
                           filename=filename,
                           infoHash=infoHash)
        temp_port = generate_random_port()
        search_sock = set_socket(self.my_ip, temp_port)
        self.send_segment(sock=search_sock,
                          data=msg.encode(),
                          addr=tuple((self.dest_ip, self.dest_port)))
        # now we must wait for the tracker response
        while True:
            data, addr = search_sock.recvfrom(config.constants.BUFFER_SIZE)
            tracker_msg = Message.decode(data)
            return tracker_msg

    def fetch_owned_files(self, current_path) -> list:
        files_and_folders = []

        items = os.listdir(current_path)

        for item in items:
            item_path = os.path.join(current_path, item)
            if os.path.isdir(item_path):
                subfolder_contents = self.fetch_owned_files(item_path)
                files_and_folders.append([item] + subfolder_contents)
            else:
                files_and_folders.append(item)
        return files_and_folders

    def check_nodes_file(self, folder_path: str) -> list:
        if os.path.isdir(folder_path):
            self.files = self.fetch_owned_files(folder_path)
        else:
            os.makedirs(folder_path)
            self.files = []


    def exit_torrent(self):
        try:
            if self.send_socket:
                msg = Node2Tracker(node_id=self.node_id,
                                   mode=config.tracker_requests_mode.EXIT,
                                   filename="",
                                   infoHash="")
                self.send_segment(sock=self.send_socket,
                                  data=Message.encode(msg),
                                  addr=tuple((self.dest_ip, self.dest_port)))
        except Exception as e:
            print(f"Error while exiting torrent: {e}")
        
        finally:
            if self.send_socket:
                free_socket(self.send_socket)
            self.running = False
            log_content = f"You exited the torrent!"
            log(node_id=self.node_id, content=log_content)

    def enter_torrent(self):
        msg = Node2Tracker(node_id=self.node_id,
                           mode=config.tracker_requests_mode.REGISTER,
                           filename="",
                           infoHash="")

        self.send_segment(sock=self.send_socket,
                          data=Message.encode(msg),
                          addr=tuple((self.dest_ip, self.dest_port)))

        log_content = f"You entered Torrent."
        log(node_id=self.node_id, content=log_content)

    def inform_tracker_periodically(self, interval: int):
        if self.running:
            global next_call
            log_content = f"Ping to server!"
            log(node_id=self.node_id, content=log_content)

            msg = Node2Tracker(node_id=self.node_id,
                            mode=config.tracker_requests_mode.REGISTER,
                            filename="",
                            infoHash="")

            self.send_segment(sock=self.send_socket,
                            data=msg.encode(),
                            addr=tuple((self.dest_ip, self.dest_port)))

            datetime.datetime.now()
            next_call = next_call + interval
            Timer(next_call - time.time(), self.inform_tracker_periodically, args=(interval,)).start()
