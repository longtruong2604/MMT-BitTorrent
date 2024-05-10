from messages.message import Message

class Tracker2Peer(Message):
    def __init__(self, dest_peer_id: int, search_result: list, filename: str):

        super().__init__()
        self.dest_peer_id = dest_peer_id
        self.search_result = search_result
        self.filename = filename
