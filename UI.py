import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QFileDialog, QVBoxLayout, QHBoxLayout

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Management App")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget()

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.employee_data = []

        # Create styled entry boxes
        self.entry1 = QTextEdit(self)
        self.entry1.setFixedHeight(30)
        

        self.entry2 = QTextEdit(self)
        self.entry2.setFixedHeight(30)
        

        self.entry3 = QTextEdit(self)
        self.entry3.setFixedHeight(30)
        

        self.entry4 = QTextEdit(self)
        self.entry4.setFixedHeight(30)
    
        self.entry4.setReadOnly(True)

        #Placeholder
        self.entry1.setPlaceholderText("Download file path.")
        self.entry2.setPlaceholderText("Download file path.")
        self.entry3.setPlaceholderText("Download file path.")
        self.entry4.setPlaceholderText("Choose file ...")

        # Create styled buttons
        self.download_button = QPushButton("Download", self)
        self.download_button.setFixedHeight(30)
        

        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.setFixedHeight(30)
        


        self.upload_button = QPushButton("Upload", self)
        self.upload_button.setFixedHeight(30)
        
        self.upload_button.clicked.connect(self.upload_action)

        self.display_box = QTextEdit(self)
        self.display_box.setReadOnly(True)
        self.display_box.setPlaceholderText("Window for loggin.")

        v_layout = QVBoxLayout()
        h_layout1 = QHBoxLayout()
        h_layout2 = QHBoxLayout()

        # Arrange widgets
        h_layout1.addWidget(self.entry1)
        h_layout1.addWidget(self.download_button)

        h_layout2.addWidget(self.entry2)
        h_layout2.addWidget(self.refresh_button)

        v_layout.addLayout(h_layout1)
        v_layout.addLayout(h_layout2)
        v_layout.addWidget(self.entry3)
        v_layout.addWidget(self.entry4)
        v_layout.addWidget(self.upload_button)
        v_layout.addWidget(self.display_box)

        self.setLayout(v_layout)

    def upload_action(self):
        # Implement file upload functionality
        filename, _ = QFileDialog.getOpenFileName(self, "Select a file", "", "All files (*)")
        if filename:
            self.entry4.setPlainText(filename)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
