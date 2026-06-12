import asyncio
from src.QTui.select_UI import SelectWindown
from src.QTui.download_UI import DownloadWindow
from src.QTui.downloaded_UI import DownloadedWindow
from src.QTui.media_lib_UI import MediaLibWindow, TagWindow
from src.QTui.setting_UI import SettingWindow
from src.QTui.style.theme import enable_dark_title_bar
from src.module.i18n import tr, notifier
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt5.uic import loadUi


class IndexWindow(QWidget):
    def __init__(self):
        super().__init__()
        loadUi("src/QTui/ui_file/index.ui", self)  # 请替换为你的 .ui 文件路径
        enable_dark_title_bar(self)

        self.select_button = self.findChild(QPushButton, 'pushButton')
        self.download_button = self.findChild(QPushButton, 'pushButton_2')
        self.downloaded_button = self.findChild(QPushButton, 'pushButton_4')
        self.media_lib_button = self.findChild(QPushButton, 'pushButton_5')
        self.tag_button = self.findChild(QPushButton, 'pushButton_6')
        self.setting_button = self.findChild(QPushButton, 'pushButton_3')

        # 连接按钮点击事件到槽函数
        self.select_button.clicked.connect(self.show_select_window)
        self.download_button.clicked.connect(self.show_download_window)
        self.downloaded_button.clicked.connect(self.show_downloaded_window)
        self.media_lib_button.clicked.connect(self.show_media_lib_window)
        self.tag_button.clicked.connect(self.show_tag_window)
        self.setting_button.clicked.connect(self.show_setting_window)

        # 初始化 QStackedWidget
        self.stackedWidget = QStackedWidget(self.verticalLayoutWidget)
        self.verticalLayout.addWidget(self.stackedWidget)

        # 创建并添加窗口
        self.select_window = SelectWindown()
        self.stackedWidget.addWidget(self.select_window)

        self.download_window = DownloadWindow()
        self.stackedWidget.addWidget(self.download_window)
        # 下载页解析失败点击“重新搜索”：切回搜索页并自动以该番号重新搜索
        self.download_window.research_requested.connect(self.research_work)

        self.downloaded_window = DownloadedWindow()
        self.stackedWidget.addWidget(self.downloaded_window)

        self.media_lib_window = MediaLibWindow()
        self.stackedWidget.addWidget(self.media_lib_window)

        self.tag_window = TagWindow()
        self.stackedWidget.addWidget(self.tag_window)

        self.setting_window = SettingWindow()
        self.stackedWidget.addWidget(self.setting_window)

        # 设置默认显示的窗口
        self.select_button.setChecked(True)
        self.stackedWidget.setCurrentWidget(self.select_window)

        self.logo_label = self.findChild(QLabel, 'logoLabel')
        self.retranslate_ui()
        notifier.language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self):
        if self.logo_label is not None:
            self.logo_label.setText(tr('DLsite 下载器'))
        self.select_button.setText(tr('搜索'))
        self.download_button.setText(tr('下载'))
        self.downloaded_button.setText(tr('已下载'))
        self.media_lib_button.setText(tr('媒体库'))
        self.tag_button.setText(tr('标签'))
        self.setting_button.setText(tr('设置'))

    def show_select_window(self):
        # 切换到 SelectWindown 窗口
        self.stackedWidget.setCurrentWidget(self.select_window)

    def show_download_window(self):
        self.stackedWidget.setCurrentWidget(self.download_window)

    def research_work(self, work_id):
        """从下载页跳转回搜索页，填入番号并自动发起搜索"""
        self.select_button.setChecked(True)
        self.stackedWidget.setCurrentWidget(self.select_window)
        self.select_window.input.setText(work_id)
        asyncio.create_task(self.select_window.show_select_button())

    def show_downloaded_window(self):
        self.stackedWidget.setCurrentWidget(self.downloaded_window)

    def show_media_lib_window(self):
        self.stackedWidget.setCurrentWidget(self.media_lib_window)

    def show_tag_window(self):
        self.stackedWidget.setCurrentWidget(self.tag_window)

    def show_setting_window(self):
        self.stackedWidget.setCurrentWidget(self.setting_window)
