from PyQt5.QtWidgets import (QMainWindow, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer
from PyQt5.uic import loadUi
from src.module.datebase_execution import SQLiteDB
from src.web_drive.debrid_link import start_download_worker, download_worker_running

# download_list.status -> 显示文本与颜色
STATUS_MAP = {
    '0': ('等待下载', '#facc15'),
    '1': ('已完成', '#4ade80'),
    '2': ('解析失败', '#f87171'),
}


class DownloadWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("src/QTui/ui_file/download.ui", self)

        self.download_table = self.findChild(QTableWidget, 'download_table')
        self.start_download_button = self.findChild(QPushButton, 'start_download_button')
        self.refresh_button = self.findChild(QPushButton, 'refresh_button')
        self.clear_done_button = self.findChild(QPushButton, 'clear_done_button')
        self.clear_all_button = self.findChild(QPushButton, 'clear_all_button')

        self.download_table.setColumnCount(3)
        self.download_table.setHorizontalHeaderLabels(['番号', '下载链接', '状态'])
        header = self.download_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.start_download_button.clicked.connect(self.start_download)
        self.refresh_button.clicked.connect(self.refresh)
        self.clear_done_button.clicked.connect(self.clear_done)
        self.clear_all_button.clicked.connect(self.clear_all)

        # 页面可见时每 3 秒自动刷新一次状态
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(3000)
        self.refresh_timer.timeout.connect(self.refresh)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self.refresh_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.refresh_timer.stop()

    def start_download(self):
        start_download_worker()
        self._update_start_button()

    def _update_start_button(self):
        if download_worker_running():
            self.start_download_button.setText('下载中…')
            self.start_download_button.setEnabled(False)
        else:
            self.start_download_button.setText('开始下载')
            self.start_download_button.setEnabled(True)

    def refresh(self):
        self._update_start_button()
        sql = '''SELECT "work_id", "url", "status" FROM "main"."download_list" ORDER BY rowid DESC'''
        result = SQLiteDB().select(sql)
        if result is False:
            return
        flag, rows = result

        self.download_table.setRowCount(len(rows))
        for i, (work_id, url, status) in enumerate(rows):
            text, color = STATUS_MAP.get(status, (f'未知({status})', '#cdd3de'))

            self.download_table.setItem(i, 0, QTableWidgetItem(work_id or ''))
            self.download_table.setItem(i, 1, QTableWidgetItem(url or ''))
            status_item = QTableWidgetItem(text)
            status_item.setForeground(QColor(color))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.download_table.setItem(i, 2, status_item)

    def clear_done(self):
        SQLiteDB().delete('''DELETE FROM "main"."download_list" WHERE "status" = '1' ''')
        self.refresh()

    def clear_all(self):
        if self.download_table.rowCount() == 0:
            return
        answer = QMessageBox.question(
            self, '清空下载列表',
            '确定要清空整个下载列表吗？等待中的任务也会被删除。',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            SQLiteDB().delete('''DELETE FROM "main"."download_list"''')
            self.refresh()
