import threading
from tracker import Tracker
from configs import CFG, Config
config = Config.from_json(CFG)

def start_server():
    host = config.constants.TRACKER_ADDR[0]
    port = config.constants.TRACKER_ADDR[1]
    print(host, port)
    
    print("Tracker server is running...")
    tracker = Tracker()
    # threading.Thread(target=tracker.run).start()
    tracker.run()
        

if __name__ == '__main__':
    # Start the server tracker in a background thread
    start_server()
