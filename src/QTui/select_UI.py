import asyncio
import os
import re
import sys
import uuid
from PyQt5.QtWidgets import QMainWindow, QLineEdit, QPushButton, QListWidget, QLabel
from PyQt5.uic import loadUi
from src.Anime_sharing.get_as_work_upgroup_url import get_as_work_upgroup_url, as_work_url
from src.Anime_sharing.get_webdrive_url import get_work_down_url
from src.web_drive.doun_url_test import katfile
from src.DLsite.DLapi_call import get_work_name
from src.module.conf_operate import Config
from src.module.datebase_execution import MySQLDB
from src.dictionary.db_works import works_status
from src.DLsite.craw_dlsite_works_name import UI_A_craw_dlsite_works
from src.DLsite.craw_dlsite_infomation import UI_A_crawl_work_web_information
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
        self.work_table_status = None
        self.open_DB = Config().open_DB()
        self.works_status = works_status()
        self.push_download_list = []

        # 加载 .ui 文件
        loadUi("src/QTui/ui_file/select.ui", self)  # 请替换为你的 .ui 文件的路径

        # 从 .ui 文件中获取控件
        self.input = self.findChild(QLineEdit, 'select_benner')
        self.search_button = self.findChild(QPushButton, 'select_work')
        self.confirm_in_db_button = self.findChild(QPushButton, 'confirm_in_db')
        self.group_list_output = self.findChild(QListWidget, 'group_list_output')
        self.url_ui_status = self.findChild(QListWidget, 'url_ui_status')
        self.url_ui_list = self.findChild(QListWidget, 'url_ui_list')
        self.test_down_url_button = self.findChild(QPushButton, 'test_down_url_button')
        self.download_button = self.findChild(QPushButton, 'download_button')
        self.new_dl_title = self.findChild(QLabel, 'New_DL_title')
        self.new_as_title = self.findChild(QLabel, 'New_as_title')
        self.similarity = self.findChild(QLabel, 'similarity')
        self.in_db_text = self.findChild(QLabel, 'in_db')
        self.if_rj_text = self.findChild(QLabel, 'if_rj')
        self.db_status_text = self.findChild(QLabel, 'db_status')
        self.down_path_text = self.findChild(QLineEdit, 'down_path_text')
        self.download_check_button = self.findChild(QPushButton, 'download_check')

        # 查询按钮
        # self.search_button.clicked.connect(self.show_select_button)
        self.search_button.clicked.connect(lambda: asyncio.create_task(self.show_select_button()))
        # 测试连接按钮
        # self.test_down_url_button.clicked.connect(self.exec_test_url_button)
        self.test_down_url_button.clicked.connect(lambda: asyncio.create_task(self.exec_test_url_button()))
        # 上传者列表按钮
        self.group_list_output.itemClicked.connect(self.group_list_item_click)
        # 下载列表按钮
        self.url_ui_list.itemClicked.connect(self.download_url_item_click)
        # 下载按钮
        # self.download_button.clicked.connect(self.exec_download)
        self.download_button.clicked.connect(lambda: asyncio.create_task(self.exec_download()))
        # 入库按钮
        # self.confirm_in_db_button.clicked.connect(self.confirm_in_db_func)
        self.confirm_in_db_button.clicked.connect(lambda: asyncio.create_task(self.confirm_in_db_func()))
        # 校验按钮
        # self.download_check_button.clicked.connect(self.show_download_check)
        self.download_check_button.clicked.connect(lambda: asyncio.create_task(self.show_download_check()))

        if not self.open_DB:
            self.db_status_text.setText('未开启数据库模式')

    async def show_download_check(self):
        self.clear_display()
        self.select_ID = self.input.text()

        if self.open_DB:
            sql = f"SELECT work_state FROM `works` WHERE  work_id = '{self.select_ID}'"
            flag, self.work_table_status = MySQLDB().select(sql)
            status = self.work_table_status[0][0]
            if status:
                self.db_status.setText(f'{self.works_status[status]}')
        self.aaa()

    async def confirm_in_db_func(self):
        if self.open_DB:
            if int(self.work_table_status[0][0]) < 0:
                pass
            elif self.work_table_status[0][0] in ['0', '1']:
                UI_A_craw_dlsite_works(self.select_ID)
                sql = f"SELECT work_type FROM `works` WHERE  work_id = '{self.select_ID}'"
                flag, data = MySQLDB().select(sql)
                WorkType = data[0][0]
                UI_A_crawl_work_web_information(self.select_ID, WorkType)
            elif self.work_table_status[0][0] in ['2']:
                sql = f"SELECT work_type FROM `works` WHERE  work_id = '{self.select_ID}'"
                flag, data = MySQLDB().select(sql)
                WorkType = data[0][0]
                UI_A_crawl_work_web_information(self.select_ID, WorkType)
            elif int(self.work_table_status[0][0]) > 6:
                sql = f"UPDATE `DLsite`.`works` SET  `work_state` = '-1' WHERE `work_id` = '{self.select_ID}';"
                MySQLDB().update(sql)

    def title_similarity(self):
        import jellyfish
        AS_title = str(self.AS_title)

        if_rj = AS_title[AS_title.rfind('RJ'):]
        if_rj = if_rj[:if_rj.rfind(']')]
        if if_rj == self.select_ID:
            self.if_rj_text.setText('DLsite ID：相同')
            self.if_rj_text.setStyleSheet('color: black;')
        else:
            self.if_rj_text.setText('DLsite ID：不同')
            self.if_rj_text.setStyleSheet('color: red;')

        AS_title = re.sub(r'\[.*?\]', '', AS_title).replace('\n', '').replace('✨shine✨', '')
        similarity = jellyfish.jaro_winkler_similarity(AS_title, self.dl_work_name)
        similarity = float(f"{similarity:.2f}")
        self.similarity.setText(f"标题相似度: {similarity:.2f}%")
        if similarity < 0.6:
            self.similarity.setStyleSheet('color: red;')
        else:
            self.similarity.setStyleSheet('color: black;')

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

    async def exec_test_url_button(self):
        status_list = []
        for i in self.down_url_list:
            if katfile(i):
                status_list.append('正常')
            else:
                status_list.append('失效')
        self.ui_url_status_list(status_list)

    def clear_display(self):
        self.group_list_output.clear()
        self.url_ui_status.clear()
        self.url_ui_list.clear()
        self.db_status.clear()
        self.new_as_title.setText('')
        self.new_dl_title.setText('')
        self.down_path_text.setText('')
        self.similarity.setText('标题相似度：')
        self.if_rj_text.setText('DLsite ID：')
        self.db_status_text.setText('')

    async def show_select_button(self):
        self.clear_display()
        # 获取输入框的文本
        self.select_ID = self.input.text()

        if self.open_DB:
            sql = f"SELECT work_state FROM `works` WHERE  work_id = '{self.select_ID}'"
            flag, self.work_table_status = MySQLDB().select(sql)
            status = self.work_table_status[0][0]
            if status:
                print(status)
                status = self.works_status[status]
                print(status)
                if status in ['已下载', '已解压', '已归档', '已听过']:
                    self.db_status.setText(f'{status}')
                else:
                    self.db_status.setText(f'{status}')
                    self.aaa()
        else:
            self.aaa()

    def aaa(self):
        self.down_path_text.setText(f"{Config().read_file_down_path()}/{self.select_ID}".replace('\\\\', '/'))
        if self.select_ID:
            self.group_list, self.url_list = as_work_url(self.select_ID)
            self.dl_work_name = get_work_name(self.select_ID)
            self.set_new_dl_title()
            self.ui_group_list(self.group_list)
