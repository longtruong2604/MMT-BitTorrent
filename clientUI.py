import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTimer
import threading
from peer import Peer, config, log, parse_command

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.initClient()
        self.initUI()

    def initClient(self):
        self.thread_lock = threading.Lock()
        self.peer = None

    def initUI(self):
        self.setWindowTitle('BitTorrent')
        self.resize(1280, 720)

        # Tạo layout chính
        layout = QHBoxLayout(self)

        # Tạo layout cho cột 1
        column1_layout = QVBoxLayout()

        # Tạo danh sách tên
        self.list_widget = QListWidget()
        # Thêm các mục vào danh sách
            
        
        # for i in range(50):  # Đây chỉ là một ví dụ, bạn có thể thay đổi số lượng tên tùy ý
        #     self.list_widget.addItem(f'Item {i}')
        column1_layout.addWidget(self.list_widget)

        # Đặt padding cho các mục trong QListWidget
        self.list_widget.setStyleSheet("QListWidget::item { padding: 10px; }")

        # Tạo layout cho cột 2
        column2_layout = QVBoxLayout()

        # # Tạo nút upload
        # self.upload_button = QPushButton('')
        # self.upload_button.setFixedHeight(150)
        # self.upload_button.clicked.connect(self.uploadClicked)
        # self.upload_button.setStyleSheet("padding: 10px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; background-image: url('./assets/uploadBTN.png'); background-position: center; background-repeat: no-repeat;")
        # column2_layout.addWidget(self.upload_button)
        
        self.entryFileName = QTextEdit(self)
        self.entryFileName.setFixedHeight(50)
        self.entryFileName.setPlaceholderText("Enter fileName...")
        column2_layout.addWidget(self.entryFileName)
        
        self.uploadBTN = QPushButton('Upload')
        self.uploadBTN.setFixedHeight(50)
        self.uploadBTN.clicked.connect(self.handleUpload)
        self.uploadBTN.setStyleSheet("padding: 10px; background-color: #f38120; color: white; border: none; border-radius: 5px;")
        column2_layout.addWidget(self.uploadBTN)

        # Tạo nút bên cột 2
        self.button2 = QPushButton('Download')
        self.button2.setFixedHeight(50)
        self.button2.clicked.connect(self.handleDownload)
        self.button2.setStyleSheet("padding: 10px; background-color: #00A3FF; color: white; border: none; border-radius: 5px;")
        column2_layout.addWidget(self.button2)
        
        # Tạo nút bên cột 2
        self.connectTrackerBTN = QPushButton('Connect To Tracker')
        self.connectTrackerBTN.setFixedHeight(50)
        self.connectTrackerBTN.clicked.connect(self.handleConnectTracker)
        self.connectTrackerBTN.setStyleSheet("padding: 10px; background-color: #4CAF50; color: white; border: none; border-radius: 5px;")
        column2_layout.addWidget(self.connectTrackerBTN)

        # Tạo nút bên cột 2
        self.exitTrackBTN = QPushButton('Refresh files')
        self.exitTrackBTN.setFixedHeight(50)
        self.exitTrackBTN.clicked.connect(self.handleRefreshFileList)
        self.exitTrackBTN.setStyleSheet("padding: 10px; background-color: #FF004A; color: white; border: none; border-radius: 5px;")
        column2_layout.addWidget(self.exitTrackBTN)
        
        # Display log
        self.displayLogField = QTextEdit(self)
        self.displayLogField.setReadOnly(True)
        self.displayLogField.setPlaceholderText("[10:44:05]  I informed the tracker that I'm still alive in the torrent!")
        column2_layout.addWidget(self.displayLogField)
        
        # Thêm layout cột 1 và cột 2 vào layout chính
        layout.addLayout(column1_layout)
        layout.addLayout(column2_layout)

        # Chia đều chiều rộng của các cột
        layout.setStretchFactor(column1_layout, 2)
        layout.setStretchFactor(column2_layout, 1)
        
        # Tạo QTimer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateFilesExist)
        # Set interval là 10 giây (10,000 ms)
        self.timer.start(5000)
    
    def peerRun(my_ip, peer_id, dest_ip, dest_port):
        
        print("Enter 'join' to connect Tracker server or 'exit' to exit!")
    
        while True:
            command = input()
            if command.lower() == 'join':
                peer = Peer(peer_id=peer_id,
                    rcv_port=dest_port,
                    send_port=peer_id,
                    my_ip = my_ip,
                    dest_ip = dest_ip,
                    dest_port=dest_port)
                log_content = f"***************** CLIENT START! *****************"
                log(peer_id=peer.peer_id, content=log_content)
                
                # print(peer.files)
                peer.enter_torrent()
                
                # We create a thread to periodically informs the tracker to tell it is still in the torrent.
                timer_thread = threading.Thread(target=peer.inform_tracker_periodically, args=(config.constants.PEER_TIME_INTERVAL,))
                timer_thread.setDaemon(True)
                timer_thread.start()

                print("ENTER YOUR COMMAND (ex: <mode> <fileName>!")
                while True:
                    peerCommand = input()
                    mode, filename = parse_command(peerCommand)

                    #################### send mode ####################
                    if mode == 'send':
                        peer.set_send_mode(filename=filename, file_path=(str(config.directory.peers_dir) + "peer" + str(peer.peer_id)), output_path=(config.directory.torrents_dir), flag=True)
                    #################### download mode ####################
                    elif mode == 'download':
                        t = threading.Thread(target=peer.set_download_mode, args=(filename, ))
                        t.setDaemon(True)
                        t.start()
                    #################### exit mode ####################
                    elif mode == 'exit':
                        peer.exit_torrent()
                        exit(0)
            elif command.lower() == 'exit':
                break
            else: 
                print("Enter 'join' to connect Tracker server or 'exit' to exit!")

    def connect_tracker(self, my_ip, my_port):
        # Connect to another server
        tracker_host = config.constants.TRACKER_ADDR[0]
        tracker_port = config.constants.TRACKER_ADDR[1]
        
        self.peer = Peer(peer_id=my_port,
            rcv_port=tracker_port,
            send_port=my_port,
            my_ip = my_ip,
            dest_ip = tracker_host,
            dest_port=tracker_port)
        
        log_content = f"***************** CLIENT START! *****************"
        log(peer_id=self.peer.peer_id, content=log_content)

        # print(peer.files)
        self.peer.enter_torrent()

        # We create a thread to periodically informs the tracker to tell it is still in the torrent.
        timer_thread = threading.Thread(target=self.peer.inform_tracker_periodically, args=(config.constants.PEER_TIME_INTERVAL,))
        timer_thread.setDaemon(True)
        timer_thread.start()
    
    def start_peer(self, my_port):
        client_ip = '10.230.198.238'
        
        # Start the client functionality in a separate thread
        self.connect_tracker(client_ip, my_port)

    def handleDownload(self):
        # # Lấy tên mục được chọn trong QListWidget
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            # selected_item_text = selected_items[0].text()
            filename = selected_items[0].text()
            print(filename)
            t = threading.Thread(target=self.peer.set_download_mode, args=(filename, ))
            t.setDaemon(True)
            t.start()
            
        # filename = self.entryFileName.toPlainText()
        # t = threading.Thread(target=self.peer.set_download_mode, args=(filename, ))
        # t.setDaemon(True)
        # t.start()

    def uploadClicked(self):
        file_dialog = QFileDialog()
        file_dialog.exec_()

    def handleConnectTracker(self):
        threading.Thread(target=self.start_peer, args=(7777,)).start()
    
    def handleRefreshFileList(self):
        if self.peer:
            self.list_widget.clear()
            # Thêm các mục mới từ mảng vào QListWidget
            
            files = self.peer.fetch_torrents_files()
            self.list_widget.addItems(files)
    
    def updateFilesExist(self):
        if self.peer:
            self.list_widget.clear()
            # Thêm các mục mới từ mảng vào QListWidget
            
            files = self.peer.fetch_torrents_files()
            self.list_widget.addItems(files)
    
    def handleUpload(self):
        filename = self.entryFileName.toPlainText()
        self.peer.set_send_mode(filename=filename, file_path=(str(config.directory.peers_dir) + "peer" + str(self.peer.peer_id)), output_path=(config.directory.torrents_dir), flag=True)


# if __name__ == '__main__':
#     # Example usage: start peers sequentially or ensure a delay in client connection attempts
#     threading.Thread(target=start_peer, args=(8888,)).start()

if __name__ == '__main__': 
    app = QApplication(sys.argv)
    window = MyWidget()
    window.show()
    sys.exit(app.exec_())