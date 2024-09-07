import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QLineEdit, QPushButton, QListWidget, \
    QPlainTextEdit
from PyQt5.uic import loadUi
from src.Anime_sharing.get_as_work_upgroup_url import get_as_work_upgroup_url, as_work_url
from src.Anime_sharing.get_webdrive_url import get_work_down_url
from src.web_drive.doun_url_test import katfile

class SelectWindown(QMainWindow):
    try:
        def __init__(self):
            super().__init__()
            self.url_list = []
            self.group_list = []
            self.down_url_list = []
            # 加载 .ui 文件
            loadUi("src/QTui/ui_file/select.ui", self)  # 请替换为你的 .ui 文件的路径

            # 从 .ui 文件中获取控件
            self.input = self.findChild(QLineEdit, 'select_benner')
            self.search_button = self.findChild(QPushButton, 'select_work')
            self.group_list_output = self.findChild(QListWidget, 'group_list_output')
            self.url_ui_status = self.findChild(QListWidget, 'url_ui_status')
            self.url_ui_list = self.findChild(QListWidget, 'url_ui_list')
            self.test_down_url_button = self.findChild(QPushButton, 'test_down_url_button')
            self.download_button = self.findChild(QPushButton, 'download_button')  # 确认控件是 QPushButton

            # 根据你的UI文件中的控件名称

            # 查询按钮
            self.search_button.clicked.connect(self.show_select_button)
            # 测试连接按钮
            self.test_down_url_button.clicked.connect(self.exec_test_url_button)
            # 上传者列表按钮
            self.group_list_output.itemClicked.connect(self.group_list_item_click)
            # 下载按钮
            self.download_button.clicked.connect(self.exec_download)

        def exec_download(self):
            # self.group_list_output.clear()  # 清除现有内容
            pass

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
            """处理列表中行的点击事件"""
            if self.url_list:
                url = self.group_list_output.row(item)  # 获取点击的行号
                self.url_ui_list.clear()  # 清除现有内容
                # print(f"点击的行号: {url}")  # 输出行号
                # print(self.url_list[url])

                self.down_url_list = get_work_down_url(self.url_list[url])
                # print(self.down_url_list)
                if self.down_url_list:
                    self.ui_url_list(self.down_url_list)
                else:
                    self.url_ui_list.clear()  # 清除现有内容

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
            text = self.input.text()
            self.group_list_output.clear()
            self.url_ui_status.clear()
            self.url_ui_list.clear()
            if text:
                self.group_list, self.url_list = as_work_url(text)
                self.ui_group_list(self.group_list)


    except Exception as e:
        print(f"数据获取错误: {e}")


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     window = MainWindow()
#     window.show()
#     app.exec_()
#     # sys.exit()
