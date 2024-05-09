import bencodepy
import hashlib

with open('../torrents/test.torrent', 'rb') as f:
    torrent_data = f.read()
    torrent_info = bencodepy.decode(torrent_data)
            
    test = {
        'name': torrent_info[b'info'][b'files'][2][b'name'],
        'length': torrent_info[b'info'][b'files'][2][b'length'],
        'pieces': torrent_info[b'info'][b'files'][2][b'pieces']
    }
    
    info_bencoded = bencodepy.encode(test)
    info_hash = hashlib.sha1(info_bencoded).digest()
    
    
    
    print(torrent_info[b'info'][b'files'])