import bencodepy

with open('../torrents/file_A.txt.torrent', 'rb') as f:
    torrent_data = f.read()
    torrent_info = bencodepy.decode(torrent_data)
            
    print(torrent_info)