import os
from py3createtorrent import create_torrent

source_path = "./"

tracker_urls = ["udp://tracker.openbittorrent.com:80"]
create_torrent(source_path, trackers=tracker_urls, output="my_torrent_file.torrent")