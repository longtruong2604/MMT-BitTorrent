# from py3createtorrent import create_torrent

# source_path = "./"

# tracker_urls = ["udp://192.168.1.139:9090"]
# create_torrent(source_path, trackers=tracker_urls, output="./torrent/my_torrent_file.torrent")

import bencodepy
import hashlib
import os

def create_torrent(file_path, output_path):
    # Read the file and calculate its SHA1 hash
    with open(file_path, 'rb') as f:
        file_data = f.read()
        file_hash = hashlib.sha1(file_data).digest()

    # Create the info dictionary for the torrent file
    info = {
        'length': os.path.getsize(file_path),
        'name': os.path.basename(file_path),
        'piece length': 2**20,  # 1 MB piece size (adjust as needed)
        'pieces': [file_hash]
    }

    # Calculate info hash
    info_bencoded = bencodepy.encode(info)
    info_hash = hashlib.sha1(info_bencoded).digest()

    # Create the torrent dictionary
    torrent_dict = {
        'info': info,
        'announce': 'udp://192.168.1.140:9090',  # Tracker URL
        'creation date': 1620123456,  # Unix timestamp of creation date
        'created by': 'My Torrent Creator',  # Your name or software name
        'comment': 'This is a test torrent file',  # Any comment
        'info_hash': info_hash
    }
    
    print(info_hash, bytes.fromhex(info_hash.hex()))

    # Encode the torrent dictionary using bencode
    torrent_data = bencodepy.encode(torrent_dict)
    
    print()

    # Write the torrent data to the output file
    with open(output_path, 'wb') as f:
        f.write(torrent_data)

# Example usage:
create_torrent('./', 'output_test.torrent')