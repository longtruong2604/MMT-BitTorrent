import bencodepy

with open('../torrents/test.torrent', 'rb') as f:
    torrent_data = f.read()
    torrent_info = bencodepy.decode(torrent_data)
            
    print(torrent_info[b'info'][b'files'][0])