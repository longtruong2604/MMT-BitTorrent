# import bencodepy

# def get_tracker_url(torrent_file_path):
#     with open(torrent_file_path, 'rb') as f:
#         torrent_data = f.read()

#         decoded_torrent = bencodepy.decode(torrent_data)
        
#         if b'announce' in decoded_torrent:
#             tracker_url = decoded_torrent[b'announce']
#             return tracker_url
#         else:
#             return None

# torrent_file_path = './torrent/my_torrent_file.torrent'

# tracker_url = get_tracker_url(torrent_file_path)

# if tracker_url:
#     print("Tracker URL:", tracker_url)
# else:
#     print("Tracker URL not found in the torrent file.")

import bencodepy

def decode_torrent(torrent_file):
    # Read the torrent file
    with open(torrent_file, 'rb') as f:
        torrent_data = f.read()

    # Decode the torrent data using bencode
    torrent_dict = bencodepy.decode(torrent_data)

    return torrent_dict

# Example usage:
torrent_info = decode_torrent('./output_test.torrent')
print(torrent_info)