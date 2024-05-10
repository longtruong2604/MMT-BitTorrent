from messages.message import Message

class ChunkSharing(Message):
    def __init__(self, src_peer_id: int, dest_peer_id: int, filename: str, file_path: str,
                 range: tuple, idx: int =-1, chunk: bytes = None):

        super().__init__()
        self.src_peer_id = src_peer_id
        self.dest_peer_id = dest_peer_id
        self.filename = filename
        self.file_path = file_path
        self.range = range
        self.idx = idx
        self.chunk = chunk
