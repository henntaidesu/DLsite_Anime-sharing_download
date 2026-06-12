import os
from PyQt6.QtWidgets import (QMainWindow, QLineEdit, QPushButton, QComboBox, QMessageBox,
                             QFileDialog, QGroupBox, QLabel)
from PyQt6.QtCore import QStandardPaths
from PyQt6.uic import loadUi
from src.module.conf_operate import Config
from src.module.i18n import tr, notifier, apply_language, current_language, LANGUAGES
from src.web_drive.debrid_link import DebridLink


class SettingWindow(QMainWindow):
    try:
        def __init__(self):
            super().__init__()
            loadUi("src/QTui/ui_file/setting.ui", self)

            self.down_path_save_button = self.findChild(QPushButton, 'DownPathSaveButton')
            self.down_path_save_button.clicked.connect(self.show_choose_path)

            self.debrid_test_button = self.findChild(QPushButton, 'DebridTestButton')
            self.debrid_test_button.clicked.connect(self.show_test_debrid)

            self.proxy_status_choose = self.findChild(QComboBox, 'proxy_status_choose')
            self.set_proxy_status_comboBox()
            self.proxy_status_choose.currentIndexChanged.connect(self.choose_proxy_status)

            self.proxy_type_choose = self.findChild(QComboBox, 'proxy_type_choose')
            self.set_proxy_type_comboBox()
            self.proxy_type_choose.currentIndexChanged.connect(self.choose_proxy_type)

            self.auto_download_choose = self.findChild(QComboBox, 'if_auto_download')
            self.set_auto_download_comboBox()
            self.auto_download_choose.currentIndexChanged.connect(self.choose_auto_download)

            self.auto_unzip_choose = self.findChild(QComboBox, 'if_auto_unzip')
            self.set_auto_unzip_comboBox()
            self.auto_unzip_choose.currentIndexChanged.connect(self.choose_auto_unzip)

            self.folder_name_choose = self.findChild(QComboBox, 'folder_name_choose')
            self.set_folder_name_comboBox()
            self.folder_name_choose.currentIndexChanged.connect(self.choose_folder_name)

            self.log_level_choose = self.findChild(QComboBox, 'log_level_choose')
            self.set_log_level_comboBox()
            self.log_level_choose.currentIndexChanged.connect(self.choose_log_level)

            self.language_choose = self.findChild(QComboBox, 'language_choose')
            self.set_language_comboBox()
            self.language_choose.currentIndexChanged.connect(self.choose_language)

            self.path_banner_text = self.findChild(QLineEdit, 'path_benner')
            self.address_banner_text = self.findChild(QLineEdit, 'address_benner')
            self.port_banner_text = self.findChild(QLineEdit, 'port_benner')
            self.debrid_api_key_text = self.findChild(QLineEdit, 'debrid_api_key_benner')
            self.download_processes_text = self.findChild(QLineEdit, 'download_processes_benner')
            self.min_speed_text = self.findChild(QLineEdit, 'min_speed_benner')
            self.speed_limit_text = self.findChild(QLineEdit, 'speed_limit_benner')
            self.processes_text = self.findChild(QLineEdit, 'processes_benner')
            self.encoding_text = self.findChild(QLineEdit, 'encoding_benner')
            self.api_address_text = self.findChild(QLineEdit, 'api_address_benner')
            self.api_port_text = self.findChild(QLineEdit, 'api_port_benner')

            # 输入框编辑完成（回车或失去焦点）即保存，无需保存按钮
            self.path_banner_text.editingFinished.connect(self.save_down_path)
            self.address_banner_text.editingFinished.connect(self.save_proxy)
            self.port_banner_text.editingFinished.connect(self.save_proxy)
            self.debrid_api_key_text.editingFinished.connect(self.save_debrid)
            self.download_processes_text.editingFinished.connect(self.save_download_processes)
            self.min_speed_text.editingFinished.connect(self.save_min_speed)
            self.speed_limit_text.editingFinished.connect(self.save_speed_limit)
            self.processes_text.editingFinished.connect(self.save_processes)
            self.encoding_text.editingFinished.connect(self.save_encoding)
            self.api_address_text.editingFinished.connect(self.save_api)
            self.api_port_text.editingFinished.connect(self.save_api)

            self.conf = Config()
            self.read_conf()

            self.retranslate_ui()
            notifier.language_changed.connect(self.retranslate_ui)

        def retranslate_ui(self):
            self.setWindowTitle(tr('设置'))
            titles = {'downloadGroup': '下载', 'proxyGroup': '代理',
                      'debridGroup': 'Debrid-Link 下载中转站', 'otherGroup': '下载选项',
                      'systemGroup': '系统'}
            for name, key in titles.items():
                group = self.findChild(QGroupBox, name)
                if group is not None:
                    group.setTitle(tr(key))

            labels = {'label': '缓存路径', 'label_4': '自动下载', 'autoUnzipLabel': '自动解压',
                      'folderNameLabel': '文件夹命名', 'label_5': '单文件线程数',
                      'label_6': '查询线程数', 'minSpeedLabel': '最低速度 (KB/s)',
                      'speedLimitLabel': '速度限制 (KB/s)',
                      'label_lang': '语言', 'label_7': '日志级别', 'label_8': '解压编码',
                      'label_9': 'API 地址'}
            for name, key in labels.items():
                label = self.findChild(QLabel, name)
                if label is not None:
                    label.setText(tr(key))

            self.down_path_save_button.setText(tr('保存'))
            self.debrid_test_button.setText(tr('测试'))

            # 工具提示
            label5 = self.findChild(QLabel, 'label_5')
            if label5 is not None:
                label5.setToolTip(tr('单个文件分成多少段并发下载（多线程下载），1 为不分段'))
            self.download_processes_text.setToolTip(
                tr('单个文件分成多少段并发下载（多线程下载），1 为不分段，最大 16'))
            self.min_speed_text.setToolTip(tr('持续低于该速度 30 秒后自动重试，0 表示不限制'))
            self.speed_limit_text.setToolTip(tr('下载总速度上限，0 表示不限速'))

            # 下拉框选项文案（保持 itemData 不变，仅更新显示文本）
            for combo in (self.proxy_status_choose, self.auto_download_choose, self.auto_unzip_choose):
                combo.setItemText(0, tr('开启'))
                combo.setItemText(1, tr('关闭'))
            self.folder_name_choose.setItemText(0, tr('RJ号'))
            self.folder_name_choose.setItemText(1, tr('作品名称'))

        def showEvent(self, event):
            """切换到本页时重新加载配置：先丢弃缓存从数据库重读，再回填控件"""
            super().showEvent(event)
            self.conf.reload()
            self.read_conf()

        @staticmethod
        def default_down_path():
            """用户的“下载”文件夹"""
            return os.path.normpath(QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DownloadLocation))

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
            self.auto_unzip_choose.setCurrentIndex(0 if self.conf.read_auto_unzip() else 1)
            self.folder_name_choose.setCurrentIndex(1 if self.conf.read_folder_name() == 'work_name' else 0)
            self.download_processes_text.setText(str(download_processes))
            self.min_speed_text.setText(str(self.conf.read_min_speed()))
            self.speed_limit_text.setText(str(self.conf.read_speed_limit()))
            self.processes_text.setText(str(self.conf.read_processes()))

            log_level = self.conf.read_log_level()
            log_level_index = {'info': 0, 'error': 1, 'debug': 2}.get(log_level, 0)
            self.log_level_choose.setCurrentIndex(log_level_index)

            self.encoding_text.setText(str(self.conf.read_sys_encoding()))
            self.api_address_text.setText(self.conf.read_value('API', 'address', '127.0.0.1'))
            self.api_port_text.setText(self.conf.read_value('API', 'port', '5000'))

            codes = [code for code, _ in LANGUAGES]
            lang_index = codes.index(current_language()) if current_language() in codes else 0
            self.language_choose.blockSignals(True)  # 回填时不触发切换
            self.language_choose.setCurrentIndex(lang_index)
            self.language_choose.blockSignals(False)

        def save_down_path(self):
            """手动输入下载路径：输入的是有效目录时才保存"""
            path = self.path_banner_text.text().strip()
            if path and os.path.isdir(path):
                self.conf.write_download_path(os.path.normpath(path))

        def save_proxy(self):
            self.conf.write_proxy(self.address_banner_text.text(), self.port_banner_text.text())

        def save_debrid(self):
            self.conf.write_debrid_api_key(self.debrid_api_key_text.text().strip())

        def save_download_processes(self):
            self.conf.write_value('down_list', 'download_processes', self.download_processes_text.text())

        def save_min_speed(self):
            value = self.min_speed_text.text().strip()
            self.conf.write_value('down_list', 'min_speed', value if value.isdigit() else '0')

        def save_speed_limit(self):
            value = self.speed_limit_text.text().strip()
            self.conf.write_value('down_list', 'speed_limit', value if value.isdigit() else '0')

        def save_processes(self):
            self.conf.write_value('processes', 'processes', self.processes_text.text())

        def save_encoding(self):
            self.conf.write_value('encoding', 'encoding', self.encoding_text.text())

        def save_api(self):
            self.conf.write_value('API', 'address', self.api_address_text.text())
            self.conf.write_value('API', 'port', self.api_port_text.text())

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
                QMessageBox.information(self, tr('测试成功'),
                                       tr('已连接 debrid-link\n账户: {account}').format(account=account))
            else:
                QMessageBox.warning(self, tr('测试失败'), tr('API Key 无效或网络不可用'))

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
                self.proxy_status_choose.addItem(tr(item[0]), item)

        def choose_proxy_status(self, index):
            selected_item = self.proxy_status_choose.itemData(index)[1]
            self.conf.write_proxy_status(selected_item)

        def set_auto_download_comboBox(self):
            items = [("开启", "True"), ("关闭", "False")]
            for text, value in items:
                self.auto_download_choose.addItem(tr(text), value)

        def choose_auto_download(self, index):
            self.conf.write_value('down_list', 'auto_download', self.auto_download_choose.itemData(index))

        def set_auto_unzip_comboBox(self):
            items = [("开启", "True"), ("关闭", "False")]
            for text, value in items:
                self.auto_unzip_choose.addItem(tr(text), value)

        def choose_auto_unzip(self, index):
            self.conf.write_value('down_list', 'auto_unzip', self.auto_unzip_choose.itemData(index))

        def set_folder_name_comboBox(self):
            items = [("RJ号", "rj"), ("作品名称", "work_name")]
            for text, value in items:
                self.folder_name_choose.addItem(tr(text), value)

        def choose_folder_name(self, index):
            self.conf.write_value('down_list', 'folder_name', self.folder_name_choose.itemData(index))

        def set_language_comboBox(self):
            for code, name in LANGUAGES:
                self.language_choose.addItem(name, code)

        def choose_language(self, index):
            apply_language(self.language_choose.itemData(index))

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
            path = QFileDialog.getExistingDirectory(self, tr('选择缓存路径'), start_dir)
            if path:
                path = os.path.normpath(path)
                self.path_banner_text.setText(path)
                self.conf.write_download_path(path)


    except Exception as e:
        print(f"数据获取错误: {e}")
