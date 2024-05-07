from messages.message import Message

class Node2Tracker(Message):
    def __init__(self, node_id: int, mode: int, filename: str, infoHash: str):

        super().__init__()
        self.node_id = node_id
        self.filename = filename
        self.infoHash = infoHash
        self.mode = mode
