import os
from PyQt5.QtWidgets import QMainWindow, QLineEdit, QPushButton, QComboBox, QMessageBox, QFileDialog
from PyQt5.QtCore import QStandardPaths
from PyQt5.uic import loadUi
from src.module.conf_operate import Config
from src.web_drive.debrid_link import DebridLink


class SettingWindow(QMainWindow):
    try:
        def __init__(self):
            super().__init__()
            loadUi("src/QTui/ui_file/setting.ui", self)

            self.down_path_save_button = self.findChild(QPushButton, 'DownPathSaveButton')
            self.down_path_save_button.clicked.connect(self.show_choose_path)

            self.proxy_save_button = self.findChild(QPushButton, 'ProxySaveButton')
            self.proxy_save_button.clicked.connect(self.show_save_proxy)

            self.debrid_save_button = self.findChild(QPushButton, 'DebridSaveButton')
            self.debrid_save_button.clicked.connect(self.show_save_debrid)

            self.debrid_test_button = self.findChild(QPushButton, 'DebridTestButton')
            self.debrid_test_button.clicked.connect(self.show_test_debrid)

            self.other_save_button = self.findChild(QPushButton, 'OtherSaveButton')
            self.other_save_button.clicked.connect(self.show_save_other)

            self.system_save_button = self.findChild(QPushButton, 'SystemSaveButton')
            self.system_save_button.clicked.connect(self.show_save_system)

            self.proxy_status_choose = self.findChild(QComboBox, 'proxy_status_choose')
            self.set_proxy_status_comboBox()
            self.proxy_status_choose.currentIndexChanged.connect(self.choose_proxy_status)

            self.proxy_type_choose = self.findChild(QComboBox, 'proxy_type_choose')
            self.set_proxy_type_comboBox()
            self.proxy_type_choose.currentIndexChanged.connect(self.choose_proxy_type)

            self.auto_download_choose = self.findChild(QComboBox, 'if_auto_download')
            self.set_auto_download_comboBox()
            self.auto_download_choose.currentIndexChanged.connect(self.choose_auto_download)

            self.log_level_choose = self.findChild(QComboBox, 'log_level_choose')
            self.set_log_level_comboBox()
            self.log_level_choose.currentIndexChanged.connect(self.choose_log_level)

            self.path_banner_text = self.findChild(QLineEdit, 'path_benner')
            self.address_banner_text = self.findChild(QLineEdit, 'address_benner')
            self.port_banner_text = self.findChild(QLineEdit, 'port_benner')
            self.debrid_api_key_text = self.findChild(QLineEdit, 'debrid_api_key_benner')
            self.download_processes_text = self.findChild(QLineEdit, 'download_processes_benner')
            self.processes_text = self.findChild(QLineEdit, 'processes_benner')
            self.encoding_text = self.findChild(QLineEdit, 'encoding_benner')
            self.api_address_text = self.findChild(QLineEdit, 'api_address_benner')
            self.api_port_text = self.findChild(QLineEdit, 'api_port_benner')

            self.conf = Config()
            self.read_conf()

        @staticmethod
        def default_down_path():
            """用户的“下载”文件夹"""
            return os.path.normpath(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation))

        def read_conf(self):
            path = self.conf.read_file_down_path().replace(r'\\', '\\')
            # 校验下载路径：不存在时回退到用户的下载文件夹并保存
            if not path or not os.path.isdir(path):
                path = self.default_down_path()
                self.conf.write_download_path(path)
            self.path_banner_text.setText(path)

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

            self.debrid_api_key_text.setText(self.conf.read_debrid_api_key())

            auto_download, download_processes = self.conf.read_download_list()
            self.auto_download_choose.setCurrentIndex(0 if auto_download else 1)
            self.download_processes_text.setText(str(download_processes))
            self.processes_text.setText(str(self.conf.read_processes()))

            log_level = self.conf.read_log_level()
            log_level_index = {'info': 0, 'error': 1, 'debug': 2}.get(log_level, 0)
            self.log_level_choose.setCurrentIndex(log_level_index)

            self.encoding_text.setText(str(self.conf.read_sys_encoding()))
            self.api_address_text.setText(self.conf.read_value('API', 'address', '127.0.0.1'))
            self.api_port_text.setText(self.conf.read_value('API', 'port', '5000'))

        def show_save_debrid(self):
            self.conf.write_debrid_api_key(self.debrid_api_key_text.text().strip())

        def show_test_debrid(self):
            client = DebridLink()
            client.api_key = self.debrid_api_key_text.text().strip()
            client.session.headers['Authorization'] = f'Bearer {client.api_key}'
            try:
                info = client.account_infos()
            except Exception:
                info = None
            if info:
                account = info.get('email') or info.get('username') or ''
                QMessageBox.information(self, '测试成功', f'已连接 debrid-link\n账户: {account}')
            else:
                QMessageBox.warning(self, '测试失败', 'API Key 无效或网络不可用')

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

        def set_auto_download_comboBox(self):
            items = [("开启", "True"), ("关闭", "False")]
            for text, value in items:
                self.auto_download_choose.addItem(text, value)

        def choose_auto_download(self, index):
            self.conf.write_value('down_list', 'auto_download', self.auto_download_choose.itemData(index))

        def set_log_level_comboBox(self):
            items = ["info", "error", "debug"]
            for item in items:
                self.log_level_choose.addItem(item, item)

        def choose_log_level(self, index):
            self.conf.write_value('LogLevel', 'level', self.log_level_choose.itemData(index))

        def show_choose_path(self):
            """打开 Windows 文件夹选择对话框，选择后保存为下载路径"""
            current = self.path_banner_text.text()
            start_dir = current if os.path.isdir(current) else self.default_down_path()
            path = QFileDialog.getExistingDirectory(self, '选择下载路径', start_dir)
            if path:
                path = os.path.normpath(path)
                self.path_banner_text.setText(path)
                self.conf.write_download_path(path)

        def show_save_proxy(self):
            address = self.address_banner_text.text()
            port = self.port_banner_text.text()
            self.conf.write_proxy(address, port)

        def show_save_other(self):
            self.conf.write_value('down_list', 'download_processes', self.download_processes_text.text())
            self.conf.write_value('processes', 'processes', self.processes_text.text())

        def show_save_system(self):
            self.conf.write_value('encoding', 'encoding', self.encoding_text.text())
            self.conf.write_value('API', 'address', self.api_address_text.text())
            self.conf.write_value('API', 'port', self.api_port_text.text())

    except Exception as e:
        print(f"数据获取错误: {e}")
