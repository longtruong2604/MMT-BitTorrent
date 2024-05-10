import os
import requests
import bencodepy
from tqdm import tqdm

def download_from_torrent(torrent_file, output_dir):
    # Load torrent file and parse it
    with open(torrent_file, 'rb') as f:
        torrent_data = f.read()
        torrent_info = bencodepy.decode(torrent_data)

    # Extract necessary information
    name_bytes = torrent_info[b'info'][b'name']
    name = name_bytes.decode()  # Convert bytes to string
    announce_bytes = torrent_info[b'announce']
    announce = announce_bytes.decode()  # Convert bytes to string
    info_hash = torrent_info[b'info_hash']
    pieces = torrent_info[b'info'][b'pieces']

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Iterate through pieces and download them
    with open(os.path.join(output_dir, name), 'wb') as output_file:
        for piece in tqdm(pieces):
            # Convert bytes to hexadecimal strings
            info_hash_hex = info_hash.hex()
            piece_hex = piece.hex()
            
            # Construct URL for downloading piece
            piece_url = f"{announce}?info_hash={info_hash_hex}&piece={piece_hex}"
            
            # # Download piece
            # response = requests.get(piece_url)
            # output_file.write(response.content)

    print("Download complete.")

# Example usage:
download_from_torrent('./output_test.torrent', './torrent')
