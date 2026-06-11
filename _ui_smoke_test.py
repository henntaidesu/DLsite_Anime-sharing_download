import sys
from PyQt5 import uic
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLineEdit,
                             QPushButton, QListWidget, QLabel, QComboBox)

app = QApplication(sys.argv)
from src.QTui.style.theme import apply_dark_theme
apply_dark_theme(app)

w1 = QWidget()
uic.loadUi('src/QTui/ui_file/index.ui', w1)
assert w1.findChild(QPushButton, 'pushButton')
assert w1.findChild(QPushButton, 'pushButton_2')
assert w1.findChild(QPushButton, 'pushButton_3')
assert getattr(w1, 'verticalLayout', None) is not None
assert getattr(w1, 'verticalLayoutWidget', None) is not None
print('index.ui widgets OK')

w2 = QMainWindow()
uic.loadUi('src/QTui/ui_file/select.ui', w2)
for n in ['select_benner', 'down_path_text']:
    assert w2.findChild(QLineEdit, n), n
for n in ['select_work', 'confirm_in_db', 'test_down_url_button',
          'download_button', 'download_check']:
    assert w2.findChild(QPushButton, n), n
for n in ['group_list_output', 'url_ui_status', 'url_ui_list']:
    assert w2.findChild(QListWidget, n) is not None, n
for n in ['New_DL_title', 'New_as_title', 'similarity', 'in_db', 'if_rj', 'db_status']:
    assert w2.findChild(QLabel, n), n
print('select.ui widgets OK')

w3 = QMainWindow()
uic.loadUi('src/QTui/ui_file/setting.ui', w3)
for n in ['path_benner', 'address_benner', 'port_benner',
          'user_benner', 'passwd_benner', 'XFSS_benner']:
    assert w3.findChild(QLineEdit, n), n
for n in ['DownPathSaveButton', 'ProxySaveButton', 'KatfileConfigSaveButton',
          'KatfileXfssSaveButton', 'GetKatfileXfssButton']:
    assert w3.findChild(QPushButton, n), n
for n in ['proxy_status_choose', 'proxy_type_choose', 'if_auto_download']:
    assert w3.findChild(QComboBox, n), n
print('setting.ui widgets OK')
print('ALL PASS')
