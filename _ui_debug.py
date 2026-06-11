import sys
from PyQt5 import uic
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLineEdit,
                             QPushButton, QListWidget, QLabel, QComboBox)

app = QApplication(sys.argv)
from src.QTui.style.theme import apply_dark_theme
apply_dark_theme(app)

w1 = QWidget()
uic.loadUi('src/QTui/ui_file/index.ui', w1)

w2 = QMainWindow()
uic.loadUi('src/QTui/ui_file/select.ui', w2)
print('A findChildren:', [c.objectName() for c in w2.findChildren(QListWidget)])
print('A findChild:', w2.findChild(QListWidget, 'group_list_output'))

for n in ['select_benner', 'down_path_text']:
    print('lineedit', n, w2.findChild(QLineEdit, n))
print('B findChild:', w2.findChild(QListWidget, 'group_list_output'))

for n in ['select_work', 'confirm_in_db', 'test_down_url_button',
          'download_button', 'download_check']:
    print('button', n, w2.findChild(QPushButton, n))
print('C findChild:', w2.findChild(QListWidget, 'group_list_output'))
print('C findChildren:', [c.objectName() for c in w2.findChildren(QListWidget)])

import gc
gc.collect()
print('D after gc findChild:', w2.findChild(QListWidget, 'group_list_output'))
