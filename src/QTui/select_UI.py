import asyncio
import re
import uuid
import urllib.parse
import requests
from PyQt5.QtWidgets import (QMainWindow, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QStackedWidget, QLabel, QFrame, QHBoxLayout, QVBoxLayout, QMessageBox,
                             QWidget)
from PyQt5.QtGui import QPixmap, QIcon, QColor, QPainter, QPen
from PyQt5.uic import loadUi
from src.Anime_sharing.get_as_work_upgroup_url import as_work_url
from src.Anime_sharing.get_webdrive_url import get_work_down_url
from src.DLsite.DLapi_call import get_work_data
from src.module.conf_operate import Config
from src.module.datebase_execution import SQLiteDB
from src.module.time import Time_a
from src.web_drive.doun_url_test import check_url, make_session
from src.web_drive.debrid_link import start_download_worker
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer, QRectF


class LoadingOverlay(QWidget):
    """全屏半透明加载遮罩，中间显示转圈动画，挡住下层控件的鼠标操作"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.hide()

    def _rotate(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def show_on(self, widget):
        """覆盖到指定窗口上并开始转圈"""
        self.setParent(widget)
        self.setGeometry(widget.rect())
        self.raise_()
        self.show()
        self._timer.start(80)

    def stop(self):
        self._timer.stop()
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

        size = 48
        cx, cy = self.width() / 2, self.height() / 2
        pen = QPen(QColor('#8fa3ff'), 5, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        rect = QRectF(cx - size / 2, cy - size / 2, size, size)
        # Qt 角度单位为 1/16 度，画 270 度的弧并随定时器旋转
        painter.drawArc(rect, -self._angle * 16, 270 * 16)

        painter.setPen(QColor('#e6e9f0'))
        painter.drawText(QRectF(0, cy + size / 2 + 12, self.width(), 30),
                         Qt.AlignHCenter, '正在查询…')


class ThumbLoader(QThread):
    """后台下载搜索结果缩略图，每张图下载完成后通过信号通知 UI"""
    loaded = pyqtSignal(int, bytes)

    def __init__(self, urls, parent=None):
        super().__init__(parent)
        self.urls = urls

    def run(self):
        open_proxy, proxy_url = Config().read_proxy()
        session = requests.Session()
        if open_proxy is True:
            session.proxies.update(proxy_url)
        for i, url in enumerate(self.urls):
            if not url:
                continue
            try:
                response = session.get(url, timeout=15)
                if response.status_code == 200 and response.content:
                    self.loaded.emit(i, response.content)
            except Exception:
                pass


class HostChecker(QThread):
    """每个下载网站一个线程，直连检测该网站下所有链接是否有效（不经过中转站）"""
    progress = pyqtSignal(str, int, int, int)  # host, 已检测数, 有效数, 总数

    def __init__(self, host, urls, parent=None):
        super().__init__(parent)
        self.host = host
        self.urls = urls

    def run(self):
        session = make_session()
        checked = valid = 0
        for url in self.urls:
            ok = check_url(url, session)
            checked += 1
            if ok:
                valid += 1
            self.progress.emit(self.host, checked, valid, len(self.urls))


class SelectWindown(QMainWindow):
    THUMB_SIZE = QSize(72, 96)

    def __init__(self):
        super().__init__()
        self.results = []
        self.thumb_loader = None
        self.host_checkers = []
        self.host_groups = {}     # host -> 该网站的链接列表
        self.host_cards = {}      # host -> 卡片上的状态标签等控件
        self.host_status = {}     # host -> None=检测中 True=全部有效 False=失效/部分 'queued'=已加入下载
        self.down_url_list = []
        self.select_ID = None
        self.AS_title = None
        self.work_data = None     # 当前搜索作品的 DL API 数据，加入下载时写入 works 表
        self.push_download_list = []

        # 加载 .ui 文件
        loadUi("src/QTui/ui_file/select.ui", self)  # 请替换为你的 .ui 文件的路径

        # 从 .ui 文件中获取控件
        self.input = self.findChild(QLineEdit, 'select_benner')
        self.search_button = self.findChild(QPushButton, 'select_work')
        self.group_list_output = self.findChild(QListWidget, 'group_list_output')
        self.host_card_list = self.findChild(QListWidget, 'host_card_list')
        self.lists_stack = self.findChild(QStackedWidget, 'lists_stack')
        self.back_button = self.findChild(QPushButton, 'back_button')

        # 搜索结果列表：左侧显示作品缩略图
        self.group_list_output.setIconSize(self.THUMB_SIZE)
        self.group_list_output.setWordWrap(True)
        # 下载网站卡片列表
        self.host_card_list.setSpacing(4)

        # 全屏查询加载遮罩
        self.loading_overlay = LoadingOverlay(self)

        # 查询按钮
        # self.search_button.clicked.connect(self.show_select_button)
        self.search_button.clicked.connect(lambda: asyncio.create_task(self.show_select_button()))
        # 输入框回车触发查询
        self.input.returnPressed.connect(lambda: asyncio.create_task(self.show_select_button()))
        # 上传者列表按钮
        self.group_list_output.itemClicked.connect(self.group_list_item_click)
        # 返回搜索结果按钮：仅在下载网站详情页显示
        self.back_button.hide()
        self.back_button.clicked.connect(self.show_results_page)
        # 下载网站卡片：点击有效卡片加入下载
        self.host_card_list.itemClicked.connect(self.host_card_click)

    @staticmethod
    def _trim_snippet(snippet):
        """整理帖子摘要：去掉空行和多余空白，最多保留 6 行"""
        lines = [' '.join(line.split()) for line in snippet.splitlines()]
        lines = [line for line in lines if line]
        return '\n'.join(lines[:6])

    def ui_group_list(self, results):
        """将搜索结果（缩略图 + 标题 + 详情摘要）填充到列表中"""
        # 上一次搜索的缩略图加载线程还在跑时，断开信号避免错位
        if self.thumb_loader is not None and self.thumb_loader.isRunning():
            self.thumb_loader.loaded.disconnect()

        self.group_list_output.clear()  # 清除现有内容
        if not results:
            return

        placeholder = QPixmap(self.THUMB_SIZE)
        placeholder.fill(QColor('#232834'))
        for res in results:
            text = res['title']
            if res['minor']:
                text += '\n' + res['minor']
            snippet = self._trim_snippet(res.get('snippet', ''))
            if snippet:
                text += '\n' + snippet
            item = QListWidgetItem(QIcon(placeholder), text)
            self.group_list_output.addItem(item)

        self.thumb_loader = ThumbLoader([res.get('thumb', '') for res in results], self)
        self.thumb_loader.loaded.connect(self._set_thumbnail)
        self.thumb_loader.start()

    def _set_thumbnail(self, row, data):
        item = self.group_list_output.item(row)
        if item is None:
            return
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            item.setIcon(QIcon(pixmap.scaled(
                self.THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)))

    @staticmethod
    def _host_of(url):
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith('www.') else netloc

    def _stop_host_checkers(self):
        for checker in self.host_checkers:
            if checker.isRunning():
                checker.progress.disconnect()
        self.host_checkers = []

    def ui_host_cards(self, url_list):
        """按下载网站分组生成卡片，并为每个网站启动一个检测线程"""
        self._stop_host_checkers()
        self.host_card_list.clear()
        self.host_cards = {}
        self.host_status = {}

        # 按域名分组，保持链接出现顺序
        groups = {}
        for url in url_list:
            groups.setdefault(self._host_of(url), []).append(url)
        self.host_groups = groups

        for host, urls in groups.items():
            widget, status_label, count_label = self._build_host_card(host, len(urls))
            item = QListWidgetItem()
            item.setData(Qt.UserRole, host)
            item.setSizeHint(widget.sizeHint())
            self.host_card_list.addItem(item)
            self.host_card_list.setItemWidget(item, widget)
            self.host_cards[host] = {'status': status_label, 'count': count_label}
            self.host_status[host] = None

            checker = HostChecker(host, urls, self)
            checker.progress.connect(self._update_host_card)
            checker.start()
            self.host_checkers.append(checker)

    @staticmethod
    def _build_host_card(host, count):
        frame = QFrame()
        frame.setStyleSheet('QFrame { background-color: #232834; border-radius: 8px; }'
                            'QLabel { background: transparent; }')
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(2)
        name_label = QLabel(host)
        name_label.setStyleSheet('font-weight: 600; font-size: 14px;')
        count_label = QLabel(f'{count} 个文件')
        count_label.setStyleSheet('color: #8b93a3; font-size: 12px;')
        left.addWidget(name_label)
        left.addWidget(count_label)
        lay.addLayout(left)
        lay.addStretch(1)

        status_label = QLabel('检测中…')
        status_label.setStyleSheet('color: #8b93a3;')
        lay.addWidget(status_label)
        return frame, status_label, count_label

    def _update_host_card(self, host, checked, valid, total):
        card = self.host_cards.get(host)
        if card is None:
            return
        status_label = card['status']
        if checked < total:
            status_label.setText(f'检测中… {checked}/{total}')
            return
        if valid == total:
            self.host_status[host] = True
            status_label.setText('有效')
            status_label.setStyleSheet('color: #4ade80; font-weight: 600;')
        elif valid == 0:
            self.host_status[host] = False
            status_label.setText('失效')
            status_label.setStyleSheet('color: #f87171;')
        else:
            # 分卷不全等于不可用，不允许加入下载
            self.host_status[host] = False
            status_label.setText(f'部分有效 {valid}/{total}')
            status_label.setStyleSheet('color: #fbbf24;')

    def show_results_page(self):
        self.lists_stack.setCurrentIndex(0)
        self.back_button.hide()

    def show_detail_page(self):
        self.lists_stack.setCurrentIndex(1)
        self.back_button.show()

    def group_list_item_click(self, item):
        if self.results:
            row = self.group_list_output.row(item)  # 获取点击的行号
            self.host_card_list.clear()

            self.down_url_list, self.AS_title = get_work_down_url(self.results[row]['url'])
            if self.down_url_list:
                self.ui_host_cards(self.down_url_list)
                self.show_detail_page()

    def host_card_click(self, item):
        """点击检测通过的网站卡片，该网站全部链接通过 debrid-link 中转站下载"""
        host = item.data(Qt.UserRole)
        if self.host_status.get(host) is not True:
            return  # 失效、分卷不全或还在检测中的网站不加入下载
        for down_url in self.host_groups.get(host, []):
            sql = f'''INSERT INTO "main"."download_list" ("UUID", "work_id", "url", "status", "long", "delete")
             VALUES ('{uuid.uuid4()}', '{self.select_ID}', '{down_url}', '0', '0', '1');'''
            SQLiteDB().insert(sql)
        self.record_work()
        start_download_worker()

        self.host_status[host] = 'queued'
        status_label = self.host_cards[host]['status']
        status_label.setText('已加入下载')
        status_label.setStyleSheet('color: #8fa3ff; font-weight: 600;')

    def record_work(self):
        """把 DL API 返回的作品数据写入 works 表，状态为下载中，全部下载完成后由下载线程改为已下载"""
        work = self.work_data or {}

        def esc(value):
            return str(value if value is not None else '').replace("'", "''")

        sql = (f'INSERT OR REPLACE INTO "main"."works" '
               f'("work_id", "work_name", "maker_id", "maker_name", "work_type", '
               f'"intro_s", "age_category", "is_ana", "state", "down_time") VALUES '
               f"('{esc(self.select_ID)}', '{esc(work.get('work_name'))}', '{esc(work.get('maker_id'))}', "
               f"'{esc(work.get('maker_name'))}', '{esc(work.get('work_type'))}', '{esc(work.get('intro_s'))}', "
               f"'{esc(work.get('age_category'))}', '{esc(work.get('is_ana'))}', '下载中', '{Time_a().now_time()}')")
        SQLiteDB().insert(sql)

    def clear_display(self):
        self._stop_host_checkers()
        self.host_groups = {}
        self.host_cards = {}
        self.host_status = {}
        self.down_url_list = []
        self.show_results_page()
        self.group_list_output.clear()
        self.host_card_list.clear()

    async def show_select_button(self):
        self.clear_display()
        # 获取输入框的文本
        self.select_ID = self.input.text().strip().upper()
        if not self.select_ID:
            return
        # RJ 号格式校验
        if not re.fullmatch(r'RJ\d+', self.select_ID):
            QMessageBox.warning(self, 'RJ号错误', f'{self.select_ID} 不是有效的RJ号（格式：RJ + 数字）')
            return
        # 已下载过的作品提示用户
        result = SQLiteDB().select(
            f'''SELECT "work_name", "down_time" FROM "main"."works" WHERE "work_id" = '{self.select_ID}' ''')
        if result is not False and result[1]:
            work_name, down_time = result[1][0]
            ret = QMessageBox.question(
                self, '已下载',
                f'{self.select_ID} {work_name or ""}\n该作品已于 {str(down_time)[:19]} 加入过下载，是否继续搜索？',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        # 查询期间显示全屏转圈遮罩，网络请求放到线程池避免卡死界面
        self.loading_overlay.show_on(self.window())
        try:
            loop = asyncio.get_event_loop()
            self.work_data, self.results = await loop.run_in_executor(
                None, self._do_search, self.select_ID)
        finally:
            self.loading_overlay.stop()
        if not self.results:
            QMessageBox.information(self, '提示', '无匹配数据')
            return
        self.ui_group_list(self.results)

    @staticmethod
    def _do_search(work_id):
        """后台线程执行：从 DL API 获取作品数据 + 搜索 AS 论坛"""
        return get_work_data(work_id), as_work_url(work_id)
