import sys
import time

from PyQt5.QtWidgets import QMainWindow, QLineEdit, QPushButton, QComboBox
from PyQt5.uic import loadUi
from src.module.conf_operate import WriteConf, Config


class SettingWindow(QMainWindow):
    try:
        def __init__(self):
            super().__init__()
            loadUi("src/QTui/ui_file/setting.ui", self)  # 请替换为你的 .ui 文件的路径
            # for child in self.findChildren(QLineEdit):
            #     print(child.objectName())

            self.down_path_save_button = self.findChild(QPushButton, 'DownPathSaveButton')
            self.down_path_save_button.clicked.connect(self.show_save_path)

            self.proxy_save_button = self.findChild(QPushButton, 'ProxySaveButton')
            self.proxy_save_button.clicked.connect(self.show_save_proxy)

            self.katfile_config_save_button = self.findChild(QPushButton, 'KatfileConfigSaveButton')
            self.katfile_config_save_button.clicked.connect(self.show_save_Katfile)

            self.katfile_xfss_save_button = self.findChild(QPushButton, 'KatfileXfssSaveButton')
            self.katfile_xfss_save_button.clicked.connect(self.show_save_XFSS)

            self.get_katfile_xfss_button = self.findChild(QPushButton, 'GetKatfileXfssButton')
            self.get_katfile_xfss_button.clicked.connect(self.show_get_katfile_xfss_button)

            self.proxy_status_choose = self.findChild(QComboBox, 'proxy_status_choose')
            self.set_proxy_status_comboBox()
            self.proxy_status_choose.currentIndexChanged.connect(self.choose_proxy_status)

            self.proxy_type_choose = self.findChild(QComboBox, 'proxy_type_choose')
            self.set_proxy_type_comboBox()
            self.proxy_type_choose.currentIndexChanged.connect(self.choose_proxy_type)

            self.path_banner_text = self.findChild(QLineEdit, 'path_benner')
            self.address_banner_text = self.findChild(QLineEdit, 'address_benner')
            self.port_banner_text = self.findChild(QLineEdit, 'port_benner')
            self.katfile_user_banner_text = self.findChild(QLineEdit, 'user_benner')
            self.katfile_passwd_banner_text = self.findChild(QLineEdit, 'passwd_benner')
            self.XFSS_banner_text = self.findChild(QLineEdit, 'XFSS_benner')

            self.conf = Config()
            self.read_conf()

        def read_conf(self):
            path = self.conf.read_file_down_path()
            self.path_banner_text.setText(path.replace(r'\\', '\\'))

            if_true, host, port, proxy_type = self.conf.read_setting_proxy()
            self.address_banner_text.setText(host)
            self.port_banner_text.setText(port)

            if if_true == 'True':
                if_true_index = 0
            else:
                if_true_index = 1
            self.proxy_status_choose.setCurrentIndex(if_true_index)

            if proxy_type == 'http':
                proxy_type_index = 0
            elif proxy_type == 'https':
                proxy_type_index = 1
            else:
                proxy_type_index = 2
            self.proxy_type_choose.setCurrentIndex(proxy_type_index)

            user, passwd, xfss = self.conf.read_katfile_use()

            self.katfile_user_banner_text.setText(user)
            self.katfile_passwd_banner_text.setText(passwd)
            self.XFSS_banner_text.setText(xfss)

        def show_get_katfile_xfss_button(self):
            pass

        def set_proxy_type_comboBox(self):
            items = ["http", "https", "Socks5"]
            for item in items:
                self.proxy_type_choose.addItem(f"{item}", item)

        def choose_proxy_type(self, index):
            proxy_type = self.proxy_type_choose.itemData(index)
            self.conf.write_proxy_type(proxy_type)

        def set_proxy_status_comboBox(self):
            items = [("开启", "True"), ("关闭", "False")]
            for item in items:
                self.proxy_status_choose.addItem(f"{item[0]}", item)

        def choose_proxy_status(self, index):
            selected_item = self.proxy_status_choose.itemData(index)[1]
            self.conf.write_proxy_status(selected_item)

        def show_save_path(self):
            path_text = self.path_banner_text.text()
            self.conf.write_download_path(path_text)

        def show_save_proxy(self):
            address = self.address_banner_text.text()
            port = self.port_banner_text.text()
            self.conf.write_proxy(address, port)

        def show_save_Katfile(self):
            user = self.katfile_user_banner_text.text()
            passwd = self.katfile_passwd_banner_text.text()
            self.conf.write_katfile_user(user, passwd)

        def show_save_XFSS(self):
            XFSS = self.XFSS_banner_text.text()
            self.conf.write_katfile_xfss(XFSS)

    except Exception as e:
        print(f"数据获取错误: {e}")
