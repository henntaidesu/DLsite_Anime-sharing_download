import os
import sys
from PyQt5.QtWidgets import QMainWindow, QLineEdit, QPushButton, QListWidget, QLabel
from PyQt5.uic import loadUi
from src.Anime_sharing.get_as_work_upgroup_url import get_as_work_upgroup_url, as_work_url
from src.Anime_sharing.get_webdrive_url import get_work_down_url
from src.web_drive.doun_url_test import katfile
from src.DLsite.DLapi_call import get_work_name
from src.module.conf_operate import Config
import webbrowser
import jellyfish


class SelectWindown(QMainWindow):
    try:
        def __init__(self):
            super().__init__()
            self.url_list = []
            self.group_list = []
            self.down_url_list = []
            self.select_ID = None
            self.dl_work_name = None
            self.AS_title = None
            # 加载 .ui 文件
            loadUi("src/QTui/ui_file/select.ui", self)  # 请替换为你的 .ui 文件的路径

            # 从 .ui 文件中获取控件
            self.input = self.findChild(QLineEdit, 'select_benner')
            self.search_button = self.findChild(QPushButton, 'select_work')
            self.group_list_output = self.findChild(QListWidget, 'group_list_output')
            self.url_ui_status = self.findChild(QListWidget, 'url_ui_status')
            self.url_ui_list = self.findChild(QListWidget, 'url_ui_list')
            self.test_down_url_button = self.findChild(QPushButton, 'test_down_url_button')
            self.download_button = self.findChild(QPushButton, 'download_button')
            # self.work_name_banner_text = self.findChild(QLineEdit, 'select_benner_2')
            self.new_as_title = self.findChild(QLabel, 'New_as_title')
            self.new_dl_title = self.findChild(QLabel, 'New_DL_title')
            self.similarity = self.findChild(QLabel, 'similarity')

            # 根据你的UI文件中的控件名称

            # 查询按钮
            self.search_button.clicked.connect(self.show_select_button)
            # 测试连接按钮
            self.test_down_url_button.clicked.connect(self.exec_test_url_button)
            # 上传者列表按钮
            self.group_list_output.itemClicked.connect(self.group_list_item_click)
            # 下载列表按钮
            self.url_ui_list.itemClicked.connect(self.download_url_item_click)
            # 下载按钮
            # self.download_button.clicked.connect(self.exec_download)

        def title_similarity(self):
            from difflib import SequenceMatcher
            AS_title = self.AS_title
            similarity = SequenceMatcher(None, AS_title, self.dl_work_name).ratio()
            self.similarity.setText(f"相似度: {similarity:.2f}")

        def exec_download(self):
            from src.web_drive.web_download import download
            download_path = f"{Config().read_file_down_path()}/{self.select_ID}"
            os.makedirs(download_path, exist_ok=True)

            for url in self.down_url_list:
                download(download_path)

        def set_new_as_title(self):
            self.new_as_title.setText(self.AS_title)

        def set_new_dl_title(self):
            self.new_dl_title.setText(self.dl_work_name)

        def ui_group_list(self, group_data):
            """将数据填充到列表中"""
            self.group_list_output.clear()  # 清除现有内容
            for item in group_data:
                self.group_list_output.addItem(item)

        def ui_url_list(self, url_list):
            self.url_ui_list.clear()  # 清除现有内容
            for item in url_list:
                self.url_ui_list.addItem(item)

        def ui_url_status_list(self, status_list):
            self.url_ui_status.clear()
            for i in status_list:
                self.url_ui_status.addItem(i)

        def group_list_item_click(self, item):
            if self.url_list:
                url = self.group_list_output.row(item)  # 获取点击的行号
                self.url_ui_list.clear()  # 清除现有内容

                self.down_url_list, self.AS_title = get_work_down_url(self.url_list[url])
                if self.down_url_list:
                    self.ui_url_list(self.down_url_list)
                    self.set_new_as_title()
                    # self.title_similarity()
                else:
                    self.url_ui_list.clear()  # 清除现有内容

        def download_url_item_click(self, item):
            if self.down_url_list:
                download_path = f"{Config().read_file_down_path()}/{self.select_ID}"
                os.makedirs(download_path, exist_ok=True)
                down_url_flag = self.url_ui_list.row(item)
                down_url = self.down_url_list[down_url_flag]
                webbrowser.open(down_url)


        def exec_test_url_button(self):
            status_list = []
            for i in self.down_url_list:
                if katfile(i):
                    status_list.append('正常')
                else:
                    status_list.append('失效')
            self.ui_url_status_list(status_list)

        def show_select_button(self):
            # 获取输入框的文本
            self.select_ID = self.input.text()
            self.group_list_output.clear()
            self.url_ui_status.clear()
            self.url_ui_list.clear()
            self.new_as_title.setText('')
            self.new_dl_title.setText('')

            if self.select_ID:
                self.group_list, self.url_list = as_work_url(self.select_ID)
                self.dl_work_name = get_work_name(self.select_ID)
                self.set_new_dl_title()
                self.ui_group_list(self.group_list)


    except Exception as e:
        print(f"数据获取错误: {e}")
