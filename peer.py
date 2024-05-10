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
from messages.peer2tracker import Peer2Tracker
from messages.peer2peer import Peer2Peer
from messages.chunk_sharing import ChunkSharing
from segment import UDPSegment

next_call = time.time()


class Peer:
    def __init__(self, peer_id: int, rcv_port: int, send_port: int, my_ip: str, dest_ip: str, dest_port: int):
        self.peer_id = peer_id
        # self.rcv_socket = set_socket(dest_ip, rcv_port)
        self.send_socket = set_socket(my_ip, send_port)
        self.files = self.check_peers_file(config.directory.peers_dir + 'peer' + str(self.peer_id))
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
    
    def handle_torrent(self, file_path: str):
        with open(f"{file_path}", 'rb') as f:
            torrent_data = f.read()
            torrent_info = bencodepy.decode(torrent_data)
            
            result = []
            for i in range(len(torrent_info[b'info'][b'files'])):
                data = {
                    'name': torrent_info[b'info'][b'files'][i][b'name'],
                    'length': torrent_info[b'info'][b'files'][i][b'length'],
                    'pieces': torrent_info[b'info'][b'files'][i][b'pieces']
                }
                
                info_bencoded = bencodepy.encode(data)
                info_hash = hashlib.sha1(info_bencoded).digest()
                
                result.append({
                    'name': data['name'].decode('utf-8'),
                    'data': info_hash.hex()
                })
    
            return result
    
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
            for dir in dirs:
                dir_path = os.path.join(root,dir)
                file_list.append(dir_path)

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
    
    def get_folder_size(self, folder_path: str):
        total_size = 0
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                total_size += self.get_folder_size(item_path)
            else:
                total_size += os.path.getsize(item_path)
        return total_size
    
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

    def send_chunk(self, filename: str,file_path: str, rng: tuple, dest_peer_ip: str ,dest_peer_id: int, dest_port: int, infoHash: str):
        file_path = f"{file_path}/{filename}"
        chunk_pieces = self.split_file_to_chunks(file_path=file_path,
                                                 rng=rng)
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        for idx, p in enumerate(chunk_pieces):
            msg = ChunkSharing(src_peer_id=self.peer_id,
                               dest_peer_id=dest_peer_id,
                               filename=filename,
                               file_path=file_path,
                               range=rng,
                               idx=idx,
                               chunk=p)
            log_content = f"The {idx}/{len(chunk_pieces)} has been sent!"
            log(peer_id=self.peer_id, content=log_content)
            self.send_segment(sock=temp_sock,
                              data=Message.encode(msg),
                              addr=(dest_peer_ip, dest_port))
        # now let's tell the neighboring peer that sending has finished (idx = -1)
        msg = ChunkSharing(src_peer_id=self.peer_id,
                           dest_peer_id=dest_peer_id,
                           filename=filename,
                           file_path=file_path,
                           range=rng)
        self.send_segment(sock=temp_sock,
                          data=Message.encode(msg),
                          addr=(dest_peer_ip, dest_port))

        log_content = "The process of sending a chunk to peer{} of file {} has finished!".format(dest_peer_id, filename)
        log(peer_id=self.peer_id, content=log_content)

        msg = Peer2Tracker(peer_id=self.peer_id,
                           mode=config.tracker_requests_mode.UPDATE,
                           filename=filename,
                           infoHash=infoHash,
                           flag=False)

        self.send_segment(sock=temp_sock,
                          data=Message.encode(msg),
                          addr=tuple((self.dest_ip, self.dest_port)))

        free_socket(temp_sock)

    def handle_requests(self, msg: dict, addr: tuple, infoHash: str):
        # 1. asks the peer about a file size
        if "size" in msg.keys() and msg["size"] == -1:
            self.tell_file_size(msg=msg, addr=addr)
        # 2. Wants a chunk of a file
        elif "range" in msg.keys() and msg["chunk"] is None:
            self.send_chunk(filename=msg["filename"],
                            file_path=msg["file_path"],
                            rng=msg["range"],
                            dest_peer_ip=addr[0],
                            dest_peer_id=msg["src_peer_id"],
                            dest_port=addr[1],
                            infoHash=infoHash)
        # 3. Check if folder
        elif "type" in msg.keys() and msg["type"] == -1:
            self.tell_is_folder(msg=msg, addr=addr)
        # 4. Get list of files from peer:
        elif "list" in msg.keys() and msg["list"] == []:
            self.tell_list_of_files(msg, addr=addr)

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
                    log(peer_id=self.peer_id, content=log_content)

    def set_send_mode(self, filename: str, file_path: str, output_path: str, flag: bool):
        if self.check_file_in_nested_list(self.files, filename) == False:
            log(peer_id=self.peer_id,
                content=f"You don't have {filename}")
            return
        # Check file or dir
        # LOOP - Hash to tracker of dir
        source_path = f"{file_path}\{filename}"
        
        if (os.path.isfile(source_path)):
            in_send_mode = False
            file_info = self.get_file_info(source_path)
            infoHash = self.create_torrent_from_info(file_info, f"{output_path}{filename}.torrent", flag)
            
            message = Peer2Tracker(peer_id=self.peer_id,
                               mode=config.tracker_requests_mode.OWN,
                               filename=filename,
                               infoHash=infoHash,
                               flag=flag)

            self.send_segment(sock=self.send_socket,
                          data=message.encode(),
                          addr=tuple((self.dest_ip, self.dest_port)))
        
            if in_send_mode:    # has been already in send(upload) mode
                log_content = f"You are already in SEND(upload) mode!"
                log(peer_id=self.peer_id, content=log_content)
                return
            else:
                in_send_mode = True
                log_content = f"DONE!"
                log(peer_id=self.peer_id, content=log_content)
                t = Thread(target=self.listen, args=(infoHash,))
                t.setDaemon(True)
                t.start()
                
        elif (os.path.isdir(source_path)):
            in_send_mode = False
            # Get list of all files in the directory
            file_list = self.traverse_directory(source_path)                
            
            directory_info = self.get_directory_info(source_path)
            infoHash = self.create_torrent_from_info(directory_info, f"{output_path}{filename}.torrent", flag)
            
            message = Peer2Tracker(peer_id=self.peer_id,
                               mode=config.tracker_requests_mode.OWN,
                               filename=filename,
                               infoHash=infoHash,
                               flag=flag)

            self.send_segment(sock=self.send_socket,
                          data=message.encode(),
                          addr=tuple((self.dest_ip, self.dest_port)))
        
            if in_send_mode:    # has been already in send(upload) mode
                log_content = f"You are already in SEND(upload) mode!"
                log(peer_id=self.peer_id, content=log_content)
                return
            else:
                in_send_mode = True
                log_content = f"DONE!"
                log(peer_id=self.peer_id, content=log_content)
                t = Thread(target=self.listen, args=(infoHash,))
                t.setDaemon(True)
                t.start()
                
            # for file in file_list:
            #     self.set_send_mode(os.path.basename(file), os.path.dirname(file), output_path, False)

    def ask_file_size(self, filename: str, file_path: str, file_owner: tuple) -> int:
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        dest_peer = file_owner[0]

        msg = Peer2Peer(src_peer_id=self.peer_id,
                        dest_peer_id=dest_peer["peer_id"],
                        filename=filename,
                        file_path=file_path,
                        size = -1,
                        type = 0,
                        list = [])
        self.send_segment(sock=temp_sock,
                          data=msg.encode(),
                          addr=tuple(dest_peer["addr"]))
        while True:
            data, addr = temp_sock.recvfrom(config.constants.BUFFER_SIZE)
            dest_peer_response = Message.decode(data)
            size = dest_peer_response["size"]
            free_socket(temp_sock)

            return size

    def tell_file_size(self, msg: dict, addr: tuple):
        filename = msg["filename"]
        f_path = msg["file_path"]
        file_path = f"{f_path}\{filename}"
        if os.path.isfile(file_path):
            file_size = os.stat(file_path).st_size
        else:
            file_size = self.get_folder_size(file_path)
            
        response_msg = Peer2Peer(src_peer_id=self.peer_id,
                        dest_peer_id=msg["src_peer_id"],
                        filename=filename,
                        file_path=file_path,
                        size=file_size,
                        type = 0, 
                        list = [])
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        self.send_segment(sock=temp_sock,
                          data=response_msg.encode(),
                          addr=addr)

        free_socket(temp_sock)

    def ask_is_folder(self, file_path: str, file_owner: tuple) -> int:
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        dest_peer = file_owner[0]

        msg = Peer2Peer(src_peer_id=self.peer_id,
                        dest_peer_id=dest_peer["peer_id"],
                        filename=file_path,
                        file_path=file_path,
                        size = 0,
                        type = -1,
                        list = [])
        self.send_segment(sock=temp_sock,
                          data=msg.encode(),
                          addr=tuple(dest_peer["addr"]))
        while True:
            data, addr = temp_sock.recvfrom(config.constants.BUFFER_SIZE)
            dest_peer_response = Message.decode(data)
            result = dest_peer_response["type"]
            free_socket(temp_sock)

            return result
        
    def tell_is_folder(self, msg: dict, addr: tuple):
        filename = msg["filename"]
        if os.path.isfile(filename):
            isFolder = 0
        else:
            isFolder = 1
            
        response_msg = Peer2Peer(src_peer_id=self.peer_id,
                        dest_peer_id=msg["src_peer_id"],
                        filename=filename,
                        file_path="",
                        size=0,
                        type=isFolder, 
                        list = [])
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        self.send_segment(sock=temp_sock,
                          data=response_msg.encode(),
                          addr=addr)

        free_socket(temp_sock)
        
    def ask_list_of_files(self, filename: str, file_owner: tuple) -> int:
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        dest_peer = file_owner[0]

        msg = Peer2Peer(src_peer_id=self.peer_id,
                        dest_peer_id=dest_peer["peer_id"],
                        filename=filename,
                        file_path="",
                        size = 0,
                        type = 0,
                        list = [])
        self.send_segment(sock=temp_sock,
                          data=msg.encode(),
                          addr=tuple(dest_peer["addr"]))
        while True:
            data, addr = temp_sock.recvfrom(config.constants.BUFFER_SIZE)
            dest_peer_response = Message.decode(data)
            result = dest_peer_response["list"]
            free_socket(temp_sock)

            return result
        
    def tell_list_of_files(self, msg: dict, addr: tuple):
        filename = msg["filename"]
        result = self.fetch_owned_files(filename)
            
        response_msg = Peer2Peer(src_peer_id=self.peer_id,
                        dest_peer_id=msg["src_peer_id"],
                        filename=filename,
                        file_path="",
                        size= 0,
                        type= 0, 
                        list = result)
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        self.send_segment(sock=temp_sock,
                          data=response_msg.encode(),
                          addr=addr)

        free_socket(temp_sock)

    def receive_chunk(self, filename: str, file_path: str, range: tuple, file_owner: tuple, infoHash: str):
        dest_peer = file_owner[0]
        # we set idx of ChunkSharing to -1, because we want to tell it that we
        # need the chunk from it
        
        msg = ChunkSharing(src_peer_id=self.peer_id,
                           dest_peer_id=dest_peer["peer_id"],
                           filename=filename,
                           file_path = file_path,
                           range=range)
        temp_port = generate_random_port()
        temp_sock = set_socket(self.my_ip, temp_port)
        self.send_segment(sock=temp_sock,
                          data=msg.encode(),
                          addr=tuple(dest_peer["addr"]))
        log_content = "Send a request for a chunk of {0} for peer{1}".format(filename, dest_peer["peer_id"])
        log(peer_id=self.peer_id, content=log_content)

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
            if owner[0]['peer_id'] != self.peer_id:
                owners.append(owner)
            elif owner[0]['peer_id'] == self.peer_id:
                log_content = f"You already have this file!"
                log(peer_id=self.peer_id, content=log_content)
                return
        print(owners)
        if len(owners) == 0:
            log_content = f"No one has file/folder {filename}"
            log(peer_id=self.peer_id, content=log_content)
            return
        # sort owners based on their sending frequency
        owners = sorted(owners, key=lambda x: x[1], reverse=True)

        to_be_used_owners = owners[:config.constants.MAX_SPLITTNES_RATE]
        # Ask the size of the file from peers
        log_content = f"You are going to download {filename} from Peer(s) {[o[0]['peer_id'] for o in to_be_used_owners]}"
        log(peer_id=self.peer_id, content=log_content)
        
        file_size = self.ask_file_size(filename=filename, file_path=f"{config.directory.peers_dir}peer{to_be_used_owners[0][0]['peer_id']}", file_owner=to_be_used_owners[0])
        log_content = f"You are downloading {filename} with the size of {file_size} bytes"
        log(peer_id=self.peer_id, content=log_content)
        
        file_path = f"{config.directory.peers_dir}peer{file_owners[0][0]['peer_id']}\{filename}"
        isFolder = self.ask_is_folder(file_path = file_path,file_owner = file_owners[0])

        if isFolder:
            list_data_torrent = self.handle_torrent(f"{config.directory.torrents_dir}{filename}.torrent")
            source_path = f"{config.directory.peers_dir}peer{self.peer_id}\{filename}"
            if not os.path.exists(source_path):
                os.makedirs(source_path)
                
            list_of_files = self.ask_list_of_files(filename=file_path, file_owner = file_owners[0])
            # Xu ly
            for file in list_of_files:
                if isinstance(file, str):                    
                    target_object = [item for item in list_data_torrent if item['name'] == file][0]
                    self.download(file_owners=to_be_used_owners, filename=str(file), file_path= file_path, source_path=f"{source_path}\{str(file)}", infoHash = str(target_object['data']))
                elif isinstance(file, list):
                    if not os.path.exists(f"{source_path}\{str(file[0])}"):
                        os.makedirs(f"{source_path}\{str(file[0])}")
                    self.handle_download(list_of_files=file[1:], list_data_torrent=list_data_torrent, to_be_used_owners=to_be_used_owners
                                         , file_path=f"{file_path}\{str(file[0])}"
                                         , source_path=f"{source_path}\{str(file[0])}")
        else:
            source_path = f"{config.directory.peers_dir}peer{self.peer_id}\{filename}"
            self.download(file_owners=to_be_used_owners, filename=filename,
                          file_path = f"{config.directory.peers_dir}peer{file_owners[0][0]['peer_id']}", 
                          source_path = f"{config.directory.peers_dir}peer{self.peer_id}\{filename}",
                          infoHash = infoHash)
        
        log_content = f"DOWNLOAD SUCCESS!!!!"
        log(peer_id=self.peer_id, content=log_content)
        newData = []
        newData.append(os.path.basename(source_path))
        
        if isFolder:
            newData.append(self.fetch_owned_files(source_path))
        
        self.files.append(newData)

    def download(self, file_owners: list, filename: str, file_path: str, source_path: str, infoHash: str):
        # 1. Ask file size
        file_size = self.ask_file_size(filename=filename, file_path=file_path, file_owner=file_owners[0])
        # 2. Now, we know the size, let's split it equally among peers to download chunks of it from them
        step = file_size / len(file_owners)
        chunks_ranges = [(round(step*i), round(step*(i+1))) for i in range(len(file_owners))]

        # 3. Create a thread for each neighbor peer to get a chunk from it
        self.downloaded_files[infoHash] = []
        neighboring_peers_threads = []
        for idx, obj in enumerate(file_owners):
            t = Thread(target=self.receive_chunk, args=(filename, file_path, chunks_ranges[idx], obj, infoHash))
            t.setDaemon(True)
            t.start()
            neighboring_peers_threads.append(t)
        for t in neighboring_peers_threads:
            t.join()

        log_content = "All the chunks of {} has downloaded!".format(filename)
        log(peer_id=self.peer_id, content=log_content)

        # 4. Now we have downloaded all the chunks of the file. It's time to sort them.
        sorted_chunks = self.sort_downloaded_chunks(filename=filename, infoHash=infoHash)
        log_content = f"All the pieces of the {filename} is now sorted and ready to be reassembled."
        log(peer_id=self.peer_id, content=log_content)

        # 5. Finally, we assemble the chunks to re-build the file
        total_file = []
        for chunk in sorted_chunks:
            for piece in chunk:
                total_file.append(piece["chunk"])
        self.reassemble_file(chunks=total_file,
                             file_path=source_path)
        log_content = f"{filename} has successfully downloaded!"
        log(peer_id=self.peer_id, content=log_content)

    def handle_download(self, list_of_files: list, list_data_torrent: list, to_be_used_owners: list, file_path: str, source_path: str):
        for file in list_of_files:
            if isinstance(file, str):
                target_object = [item for item in list_data_torrent if item['name'] == file]
                if target_object:
                    target_object = target_object[0]
                    self.download(file_owners=to_be_used_owners, filename=str(file), file_path= file_path, source_path=f"{source_path}\{str(file)}", infoHash = str(target_object['data']))
                else:
                    return
            elif isinstance(file, list):
                if not os.path.exists(f"{source_path}\{str(file[0])}"):
                    os.makedirs(f"{source_path}\{str(file[0])}")
                self.handle_download(list_of_files=file[1:], list_data_torrent=list_data_torrent, to_be_used_owners=to_be_used_owners
                                         , file_path=f"{file_path}\{str(file[0])}"
                                         , source_path=f"{source_path}\{str(file[0])}")

    def set_download_mode(self, filename: str):
        # Process the file torrent
        file_path = f"{config.directory.torrents_dir}"
        
        if os.path.exists(f"{file_path}/{filename}") and (self.check_extension(filename,".torrent")):
            filename_decode = self.decode_torrent_name(f"{file_path}/{filename}")
            infoHash_decode = self.decode_torrent_infohash(f"{file_path}/{filename}")
            log_content = f"You just started to download {filename}. Let's search it in torrent!"
            log(peer_id=self.peer_id, content=log_content)  
            tracker_response = self.search_torrent(filename=filename_decode, infoHash= infoHash_decode)
            
            file_owners = tracker_response['search_result']
            self.split_file_owners(file_owners=file_owners, filename=filename_decode, infoHash = infoHash_decode)
        else: 
            log_content = f"You don't have this file or the file format is incorrect (.torrent)!"
            log(peer_id=self.peer_id, content=log_content)
            return

    def search_torrent(self, filename: str, infoHash: str) -> dict:
        msg = Peer2Tracker(peer_id=self.peer_id,
                           mode=config.tracker_requests_mode.NEED,
                           filename=filename,
                           infoHash=infoHash,flag=False)
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

    def check_peers_file(self, folder_path: str):
        if os.path.isdir(folder_path):
            files = self.fetch_owned_files(folder_path)
        else:
            os.makedirs(folder_path)
            files = []
        return files


    def exit_torrent(self):
        try:
            if self.send_socket:
                msg = Peer2Tracker(peer_id=self.peer_id,
                                   mode=config.tracker_requests_mode.EXIT,
                                   filename="",
                                   infoHash="",
                                   flag=False)
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
            log(peer_id=self.peer_id, content=log_content)

    def enter_torrent(self):
        msg = Peer2Tracker(peer_id=self.peer_id,
                           mode=config.tracker_requests_mode.REGISTER,
                           filename="",
                           infoHash="",
                           flag=False)

        self.send_segment(sock=self.send_socket,
                          data=Message.encode(msg),
                          addr=tuple((self.dest_ip, self.dest_port)))

        log_content = f"You entered Torrent."
        log(peer_id=self.peer_id, content=log_content)

    def inform_tracker_periodically(self, interval: int):
        if self.running:
            global next_call
            log_content = f"Ping to server!"
            log(peer_id=self.peer_id, content=log_content)

            msg = Peer2Tracker(peer_id=self.peer_id,
                            mode=config.tracker_requests_mode.REGISTER,
                            filename="",
                            infoHash="",
                            flag=False)

            self.send_segment(sock=self.send_socket,
                            data=msg.encode(),
                            addr=tuple((self.dest_ip, self.dest_port)))

            datetime.datetime.now()
            next_call = next_call + interval
            Timer(next_call - time.time(), self.inform_tracker_periodically, args=(interval,)).start()
