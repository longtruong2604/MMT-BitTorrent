from messages.message import Message

class Peer2Tracker(Message):
    def __init__(self, peer_id: int, mode: int, filename: str, infoHash: str, flag: bool):

        super().__init__()
        self.peer_id = peer_id
        self.filename = filename
        self.infoHash = infoHash
        self.mode = mode
        self.flag = flag
