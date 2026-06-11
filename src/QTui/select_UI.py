import asyncio
import os
import re
import sys
import uuid
from PyQt5.QtWidgets import QMainWindow, QLineEdit, QPushButton, QListWidget, QLabel
from PyQt5.uic import loadUi
from src.Anime_sharing.get_as_work_upgroup_url import get_as_work_upgroup_url, as_work_url
from src.Anime_sharing.get_webdrive_url import get_work_down_url
from src.DLsite.DLapi_call import get_work_name
from src.module.conf_operate import Config
from PyQt5.QtCore import QThread, pyqtSignal
import webbrowser
import jellyfish
from src.web_drive.katfile_auto_down import QTUI_katfile_down
from src.module.datebase_execution import SQLiteDB


class SelectWindown(QMainWindow):
    def __init__(self):
        super().__init__()
        self.url_list = []
        self.group_list = []
        self.down_url_list = []
        self.select_ID = None
        self.dl_work_name = None
        self.AS_title = None
        self.push_download_list = []

        # 加载 .ui 文件
        loadUi("src/QTui/ui_file/select.ui", self)  # 请替换为你的 .ui 文件的路径

        # 从 .ui 文件中获取控件
        self.input = self.findChild(QLineEdit, 'select_benner')
        self.search_button = self.findChild(QPushButton, 'select_work')
        self.group_list_output = self.findChild(QListWidget, 'group_list_output')
        self.url_ui_status = self.findChild(QListWidget, 'url_ui_status')
        self.url_ui_list = self.findChild(QListWidget, 'url_ui_list')
        self.download_button = self.findChild(QPushButton, 'download_button')
        self.new_dl_title = self.findChild(QLabel, 'New_DL_title')
        self.new_as_title = self.findChild(QLabel, 'New_as_title')
        self.similarity = self.findChild(QLabel, 'similarity')
        self.if_rj_text = self.findChild(QLabel, 'if_rj')
        self.down_path_text = self.findChild(QLineEdit, 'down_path_text')
        self.download_check_button = self.findChild(QPushButton, 'download_check')

        # 查询按钮
        # self.search_button.clicked.connect(self.show_select_button)
        self.search_button.clicked.connect(lambda: asyncio.create_task(self.show_select_button()))
        # 上传者列表按钮
        self.group_list_output.itemClicked.connect(self.group_list_item_click)
        # 下载列表按钮
        self.url_ui_list.itemClicked.connect(self.download_url_item_click)
        # 下载按钮
        # self.download_button.clicked.connect(self.exec_download)
        self.download_button.clicked.connect(lambda: asyncio.create_task(self.exec_download()))
        # 校验按钮
        # self.download_check_button.clicked.connect(self.show_download_check)
        self.download_check_button.clicked.connect(lambda: asyncio.create_task(self.show_download_check()))

    async def show_download_check(self):
        self.clear_display()
        self.select_ID = self.input.text()
        self.aaa()

    def title_similarity(self):
        import jellyfish
        AS_title = str(self.AS_title)

        if_rj = AS_title[AS_title.rfind('RJ'):]
        if_rj = if_rj[:if_rj.rfind(']')]
        if if_rj == self.select_ID:
            self.if_rj_text.setText('DLsite ID：相同')
            self.if_rj_text.setStyleSheet('color: #4ade80;')
        else:
            self.if_rj_text.setText('DLsite ID：不同')
            self.if_rj_text.setStyleSheet('color: #f87171;')

        AS_title = re.sub(r'\[.*?\]', '', AS_title).replace('\n', '').replace('✨shine✨', '')
        similarity = jellyfish.jaro_winkler_similarity(AS_title, self.dl_work_name)
        similarity = float(f"{similarity:.2f}")
        self.similarity.setText(f"标题相似度: {similarity:.2f}%")
        if similarity < 0.6:
            self.similarity.setStyleSheet('color: #f87171;')
        else:
            self.similarity.setStyleSheet('color: #4ade80;')

    # async def async_exec_download(self):
    #     download_path = f"{Config().read_file_down_path()}\\{self.select_ID}"
    #     os.makedirs(download_path, exist_ok=True)
    #     # 使用 await 等待异步的下载协程
    #     await asyncio.to_thread(QTUI_katfile_down, self.down_url_list, self.select_ID, download_path)
    #     print("下载完成")

    async def exec_download(self):
        # print('下载')
        # # 初始化 DownloadList
        # await DownloadList.initialize()

        if self.down_url_list:
            for i in self.down_url_list:
                sql = f'''INSERT INTO "main"."download_list" ("UUID", "work_id", "url", "status", "long", "delete")
                 VALUES ('{uuid.uuid4()}', '{self.select_ID}', '{i}', '0', '1', '1');'''
                data = {
                    'RJNumber': f'{self.select_ID}',
                    'url': i,
                    'status': True,
                    'long': 0,
                    "delete": False
                }
                SQLiteDB().insert(sql)
            self.down_url_list = []

    def set_new_as_title(self):
        self.new_as_title.setText(self.AS_title)
        self.title_similarity()

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

    def clear_display(self):
        self.group_list_output.clear()
        self.url_ui_status.clear()
        self.url_ui_list.clear()
        self.new_as_title.setText('')
        self.new_dl_title.setText('')
        self.down_path_text.setText('')
        self.similarity.setText('标题相似度：')
        self.if_rj_text.setText('DLsite ID：')

    async def show_select_button(self):
        self.clear_display()
        # 获取输入框的文本
        self.select_ID = self.input.text()
        self.aaa()

    def aaa(self):
        self.down_path_text.setText(f"{Config().read_file_down_path()}/{self.select_ID}".replace('\\\\', '/'))
        if self.select_ID:
            self.group_list, self.url_list = as_work_url(self.select_ID)
            self.dl_work_name = get_work_name(self.select_ID)
            self.set_new_dl_title()
            self.ui_group_list(self.group_list)
