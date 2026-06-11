from src.QTui.select_UI import SelectWindown
from src.QTui.download_UI import DownloadWindow
from src.QTui.downloaded_UI import DownloadedWindow
from src.QTui.setting_UI import SettingWindow
from src.QTui.style.theme import enable_dark_title_bar
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QPushButton, QVBoxLayout, QWidget
from PyQt5.uic import loadUi


class IndexWindow(QWidget):
    def __init__(self):
        super().__init__()
        loadUi("src/QTui/ui_file/index.ui", self)  # 请替换为你的 .ui 文件路径
        enable_dark_title_bar(self)

        self.select_button = self.findChild(QPushButton, 'pushButton')
        self.download_button = self.findChild(QPushButton, 'pushButton_2')
        self.downloaded_button = self.findChild(QPushButton, 'pushButton_4')
        self.setting_button = self.findChild(QPushButton, 'pushButton_3')

        # 连接按钮点击事件到槽函数
        self.select_button.clicked.connect(self.show_select_window)
        self.download_button.clicked.connect(self.show_download_window)
        self.downloaded_button.clicked.connect(self.show_downloaded_window)
        self.setting_button.clicked.connect(self.show_setting_window)

        # 初始化 QStackedWidget
        self.stackedWidget = QStackedWidget(self.verticalLayoutWidget)
        self.verticalLayout.addWidget(self.stackedWidget)

        # 创建并添加窗口
        self.select_window = SelectWindown()
        self.stackedWidget.addWidget(self.select_window)

        self.download_window = DownloadWindow()
        self.stackedWidget.addWidget(self.download_window)

        self.downloaded_window = DownloadedWindow()
        self.stackedWidget.addWidget(self.downloaded_window)

        self.setting_window = SettingWindow()
        self.stackedWidget.addWidget(self.setting_window)

        # 设置默认显示的窗口
        self.select_button.setChecked(True)
        self.stackedWidget.setCurrentWidget(self.select_window)

    def show_select_window(self):
        # 切换到 SelectWindown 窗口
        self.stackedWidget.setCurrentWidget(self.select_window)

    def show_download_window(self):
        self.stackedWidget.setCurrentWidget(self.download_window)

    def show_downloaded_window(self):
        self.stackedWidget.setCurrentWidget(self.downloaded_window)

    def show_setting_window(self):
        self.stackedWidget.setCurrentWidget(self.setting_window)
