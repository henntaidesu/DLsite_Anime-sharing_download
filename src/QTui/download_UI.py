from PyQt5.QtWidgets import (QMainWindow, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QMessageBox, QProgressBar, QLabel)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.uic import loadUi
from src.module.datebase_execution import SQLiteDB
from src.web_drive.debrid_link import (start_download_worker, stop_download_worker,
                                       download_worker_running, stop_requested,
                                       DOWNLOAD_PROGRESS)

# download_list.status -> 显示文本与颜色
STATUS_MAP = {
    '0': ('等待下载', '#facc15'),
    '3': ('下载中', '#60a5fa'),
    '1': ('已完成', '#4ade80'),
    '2': ('解析失败', '#f87171'),
}


def format_speed(speed):
    if speed >= 1024 * 1024:
        return f'{speed / 1024 / 1024:.1f} MB/s'
    if speed >= 1024:
        return f'{speed / 1024:.0f} KB/s'
    return f'{speed:.0f} B/s'


def file_name_of(url):
    """从下载链接提取文件名（前台不直接显示链接）"""
    return url.rstrip('/').rsplit('/', 1)[-1].split('?')[0]


def format_reset(seconds):
    """把距离流量重置的秒数格式化为 Xh Ym（不足 1 分钟显示 <1m）"""
    seconds = int(seconds)
    if seconds <= 0:
        return ''
    hours, minutes = seconds // 3600, (seconds % 3600) // 60
    if hours:
        return f'{hours}h{minutes}m'
    return f'{minutes}m' if minutes else '<1m'


class UsageLoader(QThread):
    """后台请求 debrid-link 流量使用情况，避免网络请求卡住 UI"""
    loaded = pyqtSignal(object)  # downloader/limits 的 value 字典，失败时为 None

    def run(self):
        from src.web_drive.debrid_link import DebridLink
        try:
            self.loaded.emit(DebridLink().download_limits())
        except Exception:
            self.loaded.emit(None)


class DownloadWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("src/QTui/ui_file/download.ui", self)

        self.download_tree = self.findChild(QTreeWidget, 'download_tree')
        self.start_download_button = self.findChild(QPushButton, 'start_download_button')
        self.refresh_button = self.findChild(QPushButton, 'refresh_button')
        self.clear_done_button = self.findChild(QPushButton, 'clear_done_button')
        self.clear_all_button = self.findChild(QPushButton, 'clear_all_button')
        self.usage_label = self.findChild(QLabel, 'usage_label')
        self.usage_bar = self.findChild(QProgressBar, 'usage_bar')
        self.usage_loader = None

        self.download_tree.setColumnCount(4)
        self.download_tree.setHeaderLabels(['番号 / 文件', '下载进度', '速度', '状态'])
        header = self.download_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.download_tree.setColumnWidth(1, 220)
        self.download_tree.setColumnWidth(2, 110)
        self.download_tree.setColumnWidth(3, 110)

        self.start_download_button.clicked.connect(self.start_download)
        self.refresh_button.clicked.connect(self.refresh)
        self.clear_done_button.clicked.connect(self.clear_done)
        self.clear_all_button.clicked.connect(self.clear_all)

        # 页面可见时每秒刷新一次进度与速度
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(self.refresh)

        # debrid-link 流量使用量变化较慢，单独用较长间隔在后台线程查询
        self.usage_timer = QTimer(self)
        self.usage_timer.setInterval(15000)
        self.usage_timer.timeout.connect(self._fetch_usage)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self.refresh_timer.start()
        self._fetch_usage()
        self.usage_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.refresh_timer.stop()
        self.usage_timer.stop()

    def _fetch_usage(self):
        """启动后台线程查询 debrid-link 流量使用量（上一次还在跑则跳过）"""
        if self.usage_loader is not None and self.usage_loader.isRunning():
            return
        self.usage_loader = UsageLoader(self)
        self.usage_loader.loaded.connect(self._update_usage)
        self.usage_loader.start()

    def _update_usage(self, value):
        """把流量使用量更新到表头进度条与标签：百分比 + 距离重置时间"""
        usage = (value or {}).get('usagePercent') or {}
        current = usage.get('current')
        if current is None:
            self.usage_label.setText('debrid-link 使用量 --')
            self.usage_bar.setValue(0)
            return
        self.usage_bar.setValue(min(100, int(round(current))))
        text = 'debrid-link 使用量'
        reset = format_reset((value.get('nextResetSeconds') or {}).get('value', 0))
        if reset:
            text += f' · {reset} 后重置'
        self.usage_label.setText(text)

    def start_download(self):
        """开始/暂停切换"""
        if download_worker_running():
            stop_download_worker()
        else:
            start_download_worker()
        self._update_start_button()

    def _update_start_button(self):
        if download_worker_running():
            if stop_requested():
                # 已请求暂停，等待当前文件停到断点
                self.start_download_button.setText('暂停中…')
                self.start_download_button.setEnabled(False)
            else:
                self.start_download_button.setText('暂停下载')
                self.start_download_button.setEnabled(True)
        else:
            self.start_download_button.setText('开始下载')
            self.start_download_button.setEnabled(True)

    @staticmethod
    def _file_progress(uuid, status, db_long):
        """返回 (进度百分比, 实时速度 B/s 或 None)"""
        if status == '1':
            return 100, None
        if status == '3':
            info = DOWNLOAD_PROGRESS.get(uuid)
            if info and info.get('total'):
                return int(info['downloaded'] * 100 / info['total']), info.get('speed', 0.0)
        # 等待/失败/无实时数据时，退回数据库中记录的进度（断点续传的已完成部分）
        pct = int(db_long) if str(db_long).isdigit() else 0
        return min(pct, 100), None

    @staticmethod
    def _aggregate_status(statuses):
        done = statuses.count('1')
        if '3' in statuses:
            return f'下载中 {done}/{len(statuses)}', '#60a5fa'
        if '0' in statuses:
            return f'等待下载 {done}/{len(statuses)}', '#facc15'
        if '2' in statuses:
            return f'{statuses.count("2")} 个解析失败', '#f87171'
        return '已完成', '#4ade80'

    @staticmethod
    def _make_progress_bar(pct):
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setAlignment(Qt.AlignCenter)
        bar.setFixedHeight(16)
        return bar

    def refresh(self):
        self._update_start_button()
        sql = '''SELECT "UUID", "work_id", "url", "status", "long"
                 FROM "main"."download_list" ORDER BY rowid'''
        result = SQLiteDB().select(sql)
        if result is False:
            return
        flag, rows = result

        # 记住已展开的番号与滚动位置，刷新后恢复
        expanded = set()
        for i in range(self.download_tree.topLevelItemCount()):
            top = self.download_tree.topLevelItem(i)
            if top.isExpanded():
                expanded.add(top.text(0))
        scroll_pos = self.download_tree.verticalScrollBar().value()

        # 按番号分组，同一番号合并为一个父条目
        groups = {}
        for uuid, work_id, url, status, db_long in rows:
            groups.setdefault(work_id or '', []).append((uuid, url or '', status, db_long))

        self.download_tree.clear()
        for work_id, items in groups.items():
            statuses = [status for _, _, status, _ in items]
            agg_text, agg_color = self._aggregate_status(statuses)

            parent = QTreeWidgetItem([work_id, '', '', agg_text])
            parent.setForeground(3, QColor(agg_color))
            self.download_tree.addTopLevelItem(parent)

            total_pct = 0
            total_speed = 0.0
            for uuid, url, status, db_long in items:
                pct, speed = self._file_progress(uuid, status, db_long)
                total_pct += pct
                if speed:
                    total_speed += speed

                text, color = STATUS_MAP.get(status, (f'未知({status})', '#cdd3de'))
                child = QTreeWidgetItem([file_name_of(url), '', format_speed(speed) if speed else '', text])
                child.setForeground(0, QColor('#9aa3b2'))
                child.setForeground(3, QColor(color))
                parent.addChild(child)
                self.download_tree.setItemWidget(child, 1, self._make_progress_bar(pct))

            parent.setText(2, format_speed(total_speed) if total_speed else '')
            self.download_tree.setItemWidget(
                parent, 1, self._make_progress_bar(total_pct // len(items)))
            parent.setExpanded(work_id in expanded)

        self.download_tree.verticalScrollBar().setValue(scroll_pos)

    def clear_done(self):
        SQLiteDB().delete('''DELETE FROM "main"."download_list" WHERE "status" = '1' ''')
        self.refresh()

    def clear_all(self):
        if self.download_tree.topLevelItemCount() == 0:
            return
        answer = QMessageBox.question(
            self, '清空下载列表',
            '确定要清空整个下载列表吗？等待中的任务也会被删除。',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            # 没有下载完成就被删除的番号，从已下载（works 表）中移除
            result = SQLiteDB().select(
                '''SELECT DISTINCT "work_id" FROM "main"."download_list" WHERE "status" != '1' ''')
            if result is not False:
                for (work_id,) in result[1]:
                    SQLiteDB().delete(
                        f'''DELETE FROM "main"."works" WHERE "work_id" = '{work_id}' AND "state" = '下载中' ''')
            SQLiteDB().delete('''DELETE FROM "main"."download_list"''')
            self.refresh()
