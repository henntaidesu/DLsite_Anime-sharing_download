from PyQt5.QtWidgets import (QMainWindow, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QMessageBox, QProgressBar, QLabel)
from PyQt5.QtGui import QColor, QPainter, QFont
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QRectF
from PyQt5.uic import loadUi
from src.module.datebase_execution import SQLiteDB
from src.module.i18n import tr, notifier
from src.web_drive.debrid_link import (start_download_worker, stop_download_worker,
                                       download_worker_running, stop_requested,
                                       DOWNLOAD_PROGRESS, UNZIP_PROGRESS)

class RoundProgressBar(QProgressBar):
    """自绘圆角进度条：填充始终保持药丸形，最小宽度等于高度，
    避免低百分比时 QSS 的 ::chunk 圆角塌成方块/圆点。"""

    def __init__(self, track, chunk, fg, parent=None):
        super().__init__(parent)
        self._track = QColor(track)
        self._chunk = QColor(chunk)
        self._fg = QColor(fg)
        self.setTextVisible(False)  # 文字自己画，避免与自绘填充错位
        # 关掉控件自身背景，圆角外的四角露出行底色而不是方形底
        self.setStyleSheet('QProgressBar { background: transparent; border: none; }')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = rect.height() / 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._track)
        painter.drawRoundedRect(rect, radius, radius)

        span = max(1, self.maximum() - self.minimum())
        frac = min(1.0, max(0.0, (self.value() - self.minimum()) / span))
        if frac > 0:
            # 最小宽度取高度，保证再小的进度也是圆角药丸而不是方块
            fill_w = min(rect.width(), max(rect.height(), frac * rect.width()))
            painter.setBrush(self._chunk)
            painter.drawRoundedRect(
                QRectF(rect.left(), rect.top(), fill_w, rect.height()), radius, radius)

        painter.setPen(self._fg)
        painter.drawText(rect, Qt.AlignCenter, self.text())


# download_list.status -> 显示文本（中文原文，渲染时经 tr() 翻译）与颜色
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
        self.download_tree.setHeaderLabels(
            [tr('番号 / 文件'), tr('下载进度'), tr('速度'), tr('状态')])
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

        self.retranslate_ui()
        notifier.language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self):
        self.setWindowTitle(tr('下载'))
        self.download_tree.setHeaderLabels(
            [tr('番号 / 文件'), tr('下载进度'), tr('速度'), tr('状态')])
        self.refresh_button.setText(tr('刷新'))
        self.clear_done_button.setText(tr('清除已完成'))
        self.clear_all_button.setText(tr('清空列表'))
        self._update_start_button()
        self.refresh()

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
            self.usage_label.setText(tr('debrid-link 使用量 --'))
            self.usage_bar.setValue(0)
            return
        self.usage_bar.setValue(min(100, int(round(current))))
        text = tr('debrid-link 使用量')
        reset = format_reset((value.get('nextResetSeconds') or {}).get('value', 0))
        if reset:
            text += tr(' · {reset} 后重置').format(reset=reset)
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
                self.start_download_button.setText(tr('暂停中…'))
                self.start_download_button.setEnabled(False)
            else:
                self.start_download_button.setText(tr('暂停下载'))
                self.start_download_button.setEnabled(True)
        else:
            self.start_download_button.setText(tr('开始下载'))
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
    def _aggregate_status(work_id, statuses):
        done = statuses.count('1')
        if '3' in statuses:
            return tr('下载中 {done}/{total}').format(done=done, total=len(statuses)), '#60a5fa'
        if '0' in statuses:
            return tr('等待下载 {done}/{total}').format(done=done, total=len(statuses)), '#facc15'
        if '2' in statuses:
            return tr('{n} 个解析失败').format(n=statuses.count("2")), '#f87171'
        # 全部分卷已下载完成：解压前/解压中/移动中显示对应状态，全部结束（或未开启自动解压）才算已完成
        unzip = UNZIP_PROGRESS.get(work_id)
        if unzip:
            if unzip.get('state') == 'pending':
                return tr('待解压'), '#facc15'
            if unzip.get('state') == 'moving':
                return tr('移动中 {pct}%').format(pct=unzip.get('pct', 0)), '#a78bfa'
            return tr('解压中 {pct}%').format(pct=unzip.get('pct', 0)), '#60a5fa'
        return tr('已完成'), '#4ade80'

    @staticmethod
    def _make_progress_bar(pct, is_parent=True):
        """番号(父行)用更高更亮的进度条，文件(子行)用更矮更暗的，靠颜色与高度区分层级"""
        if is_parent:
            height, track, chunk, fg = 20, '#232834', '#4f7cff', '#e6e9ef'
        else:
            height, track, chunk, fg = 12, '#1c2130', '#39507e', '#9aa3b2'
        bar = RoundProgressBar(track, chunk, fg)
        bar.setRange(0, 100)
        bar.setValue(pct)
        bar.setFixedHeight(height)
        font = QFont(bar.font())
        font.setPixelSize(11 if is_parent else 10)
        bar.setFont(font)
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
            agg_text, agg_color = self._aggregate_status(work_id, statuses)

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

                raw_text, color = STATUS_MAP.get(status, (None, '#cdd3de'))
                text = tr(raw_text) if raw_text else tr('未知({status})').format(status=status)
                child = QTreeWidgetItem([file_name_of(url), '', format_speed(speed) if speed else '', text])
                child.setForeground(0, QColor('#9aa3b2'))
                child.setForeground(3, QColor(color))
                parent.addChild(child)
                self.download_tree.setItemWidget(child, 1, self._make_progress_bar(pct, is_parent=False))

            parent.setText(2, format_speed(total_speed) if total_speed else '')
            # 解压中时父进度条改为显示解压进度，否则显示分卷下载进度均值
            unzip = UNZIP_PROGRESS.get(work_id)
            parent_pct = unzip.get('pct', 0) if unzip else total_pct // len(items)
            self.download_tree.setItemWidget(
                parent, 1, self._make_progress_bar(parent_pct, is_parent=True))
            parent.setExpanded(work_id in expanded)

        self.download_tree.verticalScrollBar().setValue(scroll_pos)

    def clear_done(self):
        # 正在解压（待解压/解压中）的番号其分卷虽已是 '1'，但还未真正完成，保留不清除
        sql = '''DELETE FROM "main"."download_list" WHERE "status" = '1' '''
        unzipping = list(UNZIP_PROGRESS.keys())
        if unzipping:
            keep = ','.join("'" + w.replace("'", "''") + "'" for w in unzipping)
            sql += f''' AND "work_id" NOT IN ({keep}) '''
        SQLiteDB().delete(sql)
        self.refresh()

    def clear_all(self):
        if self.download_tree.topLevelItemCount() == 0:
            return
        answer = QMessageBox.question(
            self, tr('清空下载列表'),
            tr('确定要清空整个下载列表吗？等待中的任务也会被删除。'),
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
