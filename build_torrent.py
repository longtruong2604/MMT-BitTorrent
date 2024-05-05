from py3createtorrent import create_torrent

source_path = "./"

tracker_urls = ["udp://192.168.1.139:9090"]
create_torrent(source_path, trackers=tracker_urls, output="./torrent/my_torrent_file.torrent")