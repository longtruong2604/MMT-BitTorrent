# from py3createtorrent import create_torrent

# source_path = "./"

# tracker_urls = ["udp://192.168.1.139:9090"]
# create_torrent(source_path, trackers=tracker_urls, output="./torrent/my_torrent_file.torrent")

# ###################################################

# import bencodepy
# import hashlib
# import os

# def create_torrent(file_path, output_path):
#     # Read the file and calculate its SHA1 hash
#     with open(file_path, 'rb') as f:
#         file_data = f.read()
#         file_hash = hashlib.sha1(file_data).digest()

#     # Create the info dictionary for the torrent file
#     info = {
#         'length': os.path.getsize(file_path),
#         'name': os.path.basename(file_path),
#         'piece length': 2**20,  # 1 MB piece size (adjust as needed)
#         'pieces': [file_hash]
#     }

#     # Calculate info hash
#     info_bencoded = bencodepy.encode(info)
#     info_hash = hashlib.sha1(info_bencoded).digest()

#     # Create the torrent dictionary
#     torrent_dict = {
#         'info': info,
#         'announce': 'udp://192.168.1.140:9090',  # Tracker URL
#         'creation date': 1620123456,  # Unix timestamp of creation date
#         'created by': 'My Torrent Creator',  # Your name or software name
#         'comment': 'This is a test torrent file',  # Any comment
#         'info_hash': info_hash
#     }
    
#     print(info_hash, bytes.fromhex(info_hash.hex()))

#     # Encode the torrent dictionary using bencode
#     torrent_data = bencodepy.encode(torrent_dict)
    
#     print()

#     # Write the torrent data to the output file
#     with open(output_path, 'wb') as f:
#         f.write(torrent_data)

# # Example usage:
# create_torrent('./file_A.txt', 'output_test.torrent')

# #############################################

import os
import hashlib
import bencodepy

def create_torrent(source_path, output_path):
    if os.path.isfile(source_path):
        # Source is a file
        file_info = get_file_info(source_path)
        return create_torrent_from_info(file_info, output_path)
    elif os.path.isdir(source_path):
        # Source is a directory
        directory_info = get_directory_info(source_path)
        return create_torrent_from_info(directory_info, output_path)

def get_file_info(file_path):
    with open(file_path, 'rb') as f:
        file_data = f.read()
        file_hash = hashlib.sha1(file_data).digest()
        return {
            'path': os.path.basename(file_path),
            'length': os.path.getsize(file_path),
            'pieces': [file_hash]
        }

def get_directory_info(directory_path):
    files_info = []
    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_info = get_file_info(file_path)
            file_info['path'] = os.path.relpath(file_path, directory_path)
            files_info.append(file_info)
    return {
        'files': files_info,
        'piece length': 2**20  # 1 MB piece size (adjust as needed)
    }

def create_torrent_from_info(info, output_path):
    # Calculate info hash
    info_bencoded = bencodepy.encode(info)
    info_hash = hashlib.sha1(info_bencoded).digest()

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

# Example usage
source_path = './hello'  # Path to the file or folder you want to create a torrent for
output_path = './output.torrent'  # Output path for the torrent file
announce_url = 'udp://tracker.example.com:1234'  # Tracker URL

create_torrent(source_path, output_path, announce_url)