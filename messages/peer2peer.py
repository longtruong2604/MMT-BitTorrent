from messages.message import Message

class Peer2Peer(Message):
    def __init__(self, src_peer_id: int, dest_peer_id: int, filename: str, file_path: str, size: int = -1, type: int = -1, list: list = []):

        super().__init__()
        self.src_peer_id = src_peer_id
        self.dest_peer_id = dest_peer_id
        self.filename = filename
        self.file_path = file_path
        self.size = size    # size = -1 means a peer is asking for size
        self.type = type
        self.list = list
