import html
import os
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLabel, QLineEdit, QWidget,
                             QFrame, QScrollArea, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QDialog, QStackedWidget, QMessageBox, QTreeWidget,
                             QTreeWidgetItem, QSlider)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QPixmap
from PyQt5.uic import loadUi
from src.module.conf_operate import Config
from src.module.datebase_execution import SQLiteDB
from src.module.i18n import tr, notifier
from src.QTui.media_lib_setting_UI import MediaLibSettingDialog

CARD_GAP = 10
WORKS_PAGE = 30  # 作品卡片懒加载：每批数量
UNKNOWN_MAKER = ''  # maker_name 为空的作品归到"未知社团"

VIDEO_EXTS = ('.mp4', '.mkv', '.avi', '.wmv', '.mov', '.flv', '.webm', '.m4v',
              '.ts', '.mpg', '.mpeg')
AUDIO_EXTS = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.opus')

_AGE_MAP = {'1': '全年龄', '2': 'R-15', '3': 'R-18'}
# label → (db列名, 是否多值用 " / " 分割)
_LINK_COLS = {
    '社团': ('maker_name', False),
    '系列': ('series', False),
    '剧本': ('scenario', False),
    '插画': ('illust', False),
    '声优': ('voice_actor', True),
}


class ClickCard(QFrame):
    """可点击卡片（媒体库 / 社团）：标题 + 说明文字"""

    def __init__(self, title, caption, key, on_click, width, height, parent=None):
        super().__init__(parent)
        self.setProperty('class', 'libCard')
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)
        self.search_text = title.lower()
        self._key = key
        self._on_click = on_click

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet('font-weight: 600; font-size: 15px;')
        layout.addWidget(title_label)

        caption_label = QLabel(caption)
        caption_label.setProperty('class', 'caption')
        layout.addWidget(caption_label)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_click(self._key)
        super().mousePressEvent(event)


WORK_CARD_W, WORK_CARD_H = 210, 248  # 作品卡片固定大小
WORK_COVER_W, WORK_COVER_H = 186, 140  # 封面区固定大小
_BADGE_STYLE = ('background: rgba(0, 0, 0, 170); color: #e6e6e6; padding: 1px 6px; '
                'border-radius: 4px; font-size: 11px;')


class WorkCard(QFrame):
    """单个作品卡片（固定大小）：封面区左上角 RJ 号、右上角作品形式，下方仅作品标题，
    点击进入作品详情"""

    def __init__(self, work_id, work_name, maker_name, work_type, age_category, cover,
                 on_click, parent=None):
        super().__init__(parent)
        self.setProperty('class', 'card')
        self.setFixedSize(WORK_CARD_W, WORK_CARD_H)
        self.setCursor(Qt.PointingHandCursor)
        self.search_text = f'{work_id} {work_name or ""} {maker_name or ""}'.lower()
        self._work_id = work_id
        self._on_click = on_click
        self.setToolTip(work_name or work_id)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 封面区固定大小：图片按比例铺满裁切，无封面时显示纯色底
        cover_label = QLabel()
        cover_label.setFixedSize(WORK_COVER_W, WORK_COVER_H)
        cover_label.setAlignment(Qt.AlignCenter)
        cover_label.setStyleSheet('background: rgba(255, 255, 255, 12); border-radius: 4px;')
        if cover and os.path.exists(cover):
            pixmap = QPixmap(cover)
            if not pixmap.isNull():
                cover_label.setPixmap(pixmap.scaled(
                    WORK_COVER_W, WORK_COVER_H,
                    Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        layout.addWidget(cover_label)

        # RJ 号：封面左上角
        rj_badge = QLabel(work_id, cover_label)
        rj_badge.setStyleSheet(_BADGE_STYLE)
        rj_badge.adjustSize()
        rj_badge.move(4, 4)

        # 作品形式：封面右上角
        if work_type:
            type_badge = QLabel(str(work_type), cover_label)
            type_badge.setStyleSheet(_BADGE_STYLE)
            type_badge.adjustSize()
            max_w = WORK_COVER_W - rj_badge.width() - 12  # 避免与左上角 RJ 号重叠
            if type_badge.width() > max_w:
                type_badge.setFixedWidth(max_w)
            type_badge.move(WORK_COVER_W - type_badge.width() - 4, 4)

        name_label = QLabel(work_name or work_id)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        name_label.setStyleSheet('font-weight: 600;')
        layout.addWidget(name_label, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_click(self._work_id)
        super().mousePressEvent(event)


class _SliderThumb(QLabel):
    """轮播缩略图：点击切换大图"""

    def __init__(self, index, on_click, parent=None):
        super().__init__(parent)
        self._index = index
        self._on_click = on_click
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_click(self._index)
        super().mousePressEvent(event)


class ImageSlider(QFrame):
    """详情页图片区：大图 + 缩略图切换条（仿 DLsite 作品页）"""
    THUMB_W, THUMB_H = 64, 48
    _ASPECT = 390 / 520  # 主图高/宽比

    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self._paths = paths
        self._index = 0
        self._thumbs = []
        self._pixmap = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.main_label = QLabel()
        self.main_label.setFixedSize(520, 390)  # 初始尺寸，resizeEvent 中随宽度动态更新
        self.main_label.setAlignment(Qt.AlignCenter)
        self.main_label.setStyleSheet('background: rgba(255, 255, 255, 8); border-radius: 4px;')
        layout.addWidget(self.main_label)

        if len(paths) > 1:
            bar = QHBoxLayout()
            bar.setSpacing(6)
            prev_button = QPushButton('‹')
            prev_button.setFixedSize(28, self.THUMB_H + 4)
            prev_button.clicked.connect(lambda: self.set_index(self._index - 1))
            bar.addWidget(prev_button)

            scroll = QScrollArea()
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setFixedHeight(self.THUMB_H + 8)
            scroll.setWidgetResizable(True)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            container = QWidget()
            thumbs_layout = QHBoxLayout(container)
            thumbs_layout.setContentsMargins(0, 0, 0, 0)
            thumbs_layout.setSpacing(4)
            for i, path in enumerate(paths):
                thumb = _SliderThumb(i, self.set_index)
                thumb.setFixedSize(self.THUMB_W, self.THUMB_H)
                thumb.setAlignment(Qt.AlignCenter)
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    thumb.setPixmap(pixmap.scaled(
                        self.THUMB_W - 4, self.THUMB_H - 4,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation))
                thumbs_layout.addWidget(thumb)
                self._thumbs.append(thumb)
            thumbs_layout.addStretch()
            scroll.setWidget(container)
            bar.addWidget(scroll, 1)

            next_button = QPushButton('›')
            next_button.setFixedSize(28, self.THUMB_H + 4)
            next_button.clicked.connect(lambda: self.set_index(self._index + 1))
            bar.addWidget(next_button)
            layout.addLayout(bar)

        self.set_index(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = event.size().width()
        if w > 0:
            self.main_label.setFixedSize(w, max(1, int(w * self._ASPECT)))
            self._refresh_main()

    def set_index(self, index):
        if not self._paths:
            return
        self._index = index % len(self._paths)
        self._pixmap = QPixmap(self._paths[self._index])
        self._refresh_main()
        for i, thumb in enumerate(self._thumbs):
            thumb.setStyleSheet('border: 2px solid #5b8def;' if i == self._index
                                else 'border: 2px solid transparent;')

    def _refresh_main(self):
        if self._pixmap is None or self._pixmap.isNull():
            self.main_label.clear()
            return
        w, h = self.main_label.width(), self.main_label.height()
        if w > 0 and h > 0:
            self.main_label.setPixmap(self._pixmap.scaled(
                w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))


class _MoveLibDialog(QDialog):
    """移动媒体库对话框：选择目标媒体库（排除当前库），多文件夹时再选具体文件夹"""

    def __init__(self, current_lib, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('移动媒体库'))
        self.setModal(True)
        self.setMinimumWidth(420)
        self.selected = None  # (媒体库名, 文件夹)

        self._stack = QStackedWidget(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._stack)
        self._build_lib_page(current_lib)

    def _build_lib_page(self, current_lib):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        title = QLabel(tr('选择要移动到的媒体库'))
        title.setStyleSheet('font-weight: 600; font-size: 14px;')
        layout.addWidget(title)

        has_target = False
        for lib in Config().read_media_libs():
            if lib['name'] == current_lib:
                continue  # 排除当前所在媒体库
            folders = [f for f in lib.get('folders', []) if f]
            if not folders:
                continue
            has_target = True
            label = (f"{lib['name']}　{tr('{n} 个文件夹').format(n=len(folders))}"
                     if len(folders) > 1 else lib['name'])
            btn = QPushButton(label)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda checked, n=lib['name'], f=folders: self._pick_lib(n, f))
            layout.addWidget(btn)
        if not has_target:
            layout.addWidget(QLabel(tr('没有可移动到的其它媒体库')))

        layout.addStretch()
        cancel_btn = QPushButton(tr('取消'))
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        self._stack.addWidget(page)

    def _pick_lib(self, lib_name, folders):
        if len(folders) == 1:
            self.selected = (lib_name, folders[0])
            self.accept()
        else:
            self._show_folder_page(lib_name, folders)

    def _show_folder_page(self, lib_name, folders):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        title = QLabel(tr('选择目标文件夹'))
        title.setStyleSheet('font-weight: 600; font-size: 14px;')
        layout.addWidget(title)

        for folder in folders:
            btn = QPushButton(folder)
            btn.setMinimumHeight(40)
            btn.setToolTip(folder)
            btn.clicked.connect(lambda checked, f=folder: self._pick_folder(lib_name, f))
            layout.addWidget(btn)

        layout.addStretch()
        back_btn = QPushButton(tr('← 返回'))
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        layout.addWidget(back_btn)

        if self._stack.count() > 1:
            old = self._stack.widget(1)
            self._stack.removeWidget(old)
            old.deleteLater()
        self._stack.addWidget(page)
        self._stack.setCurrentIndex(1)

    def _pick_folder(self, lib_name, folder):
        self.selected = (lib_name, folder)
        self.accept()


class _MoveWorker(QThread):
    """后台执行作品文件夹移动 + 元数据同步，避免大文件夹移动卡住界面"""
    done = pyqtSignal(bool, str)

    def __init__(self, work_id, target_lib, target_folder, parent=None):
        super().__init__(parent)
        self._args = (work_id, target_lib, target_folder)

    def run(self):
        from src.module.import_local_works import move_work_to_library
        try:
            ok, msg = move_work_to_library(*self._args)
        except Exception as e:
            ok, msg = False, str(e)
        self.done.emit(ok, msg)


class ImageViewerDialog(QDialog):
    """程序内看图：大图自适应窗口，左右键 / 按钮切换同文件夹的所有图片"""

    def __init__(self, paths, index, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('查看图片'))
        self.resize(960, 720)
        self._paths = paths
        self._index = index
        self._pixmap = QPixmap()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet('background: #111; border-radius: 4px;')
        layout.addWidget(self._label, 1)

        bar = QHBoxLayout()
        prev_button = QPushButton('‹ ' + tr('上一张'))
        prev_button.clicked.connect(self._prev)
        next_button = QPushButton(tr('下一张') + ' ›')
        next_button.clicked.connect(self._next)
        self._counter = QLabel()
        self._counter.setAlignment(Qt.AlignCenter)
        bar.addWidget(prev_button)
        bar.addWidget(self._counter, 1)
        bar.addWidget(next_button)
        layout.addLayout(bar)

        self._load()

    def _load(self):
        self._pixmap = QPixmap(self._paths[self._index])
        self._counter.setText(f'{self._index + 1} / {len(self._paths)}')
        self.setWindowTitle(os.path.basename(self._paths[self._index]))
        self._rescale()

    def _rescale(self):
        if self._pixmap.isNull():
            self._label.setText(tr('无法显示该图片'))
            return
        self._label.setPixmap(self._pixmap.scaled(
            self._label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _prev(self):
        self._index = (self._index - 1) % len(self._paths)
        self._load()

    def _next(self):
        self._index = (self._index + 1) % len(self._paths)
        self._load()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self._prev()
        elif event.key() == Qt.Key_Right:
            self._next()
        elif event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)


class MediaPlayerDialog(QDialog):
    """程序内嵌播放器：视频用 QVideoWidget，音频只显示文件名，含播放/暂停与进度条"""

    def __init__(self, path, is_video, parent=None):
        super().__init__(parent)
        from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
        from PyQt5.QtMultimediaWidgets import QVideoWidget

        self.setWindowTitle(os.path.basename(path))
        self.resize(960, 680) if is_video else self.resize(520, 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._player = QMediaPlayer(self)
        if is_video:
            video = QVideoWidget()
            video.setStyleSheet('background: #000;')
            layout.addWidget(video, 1)
            self._player.setVideoOutput(video)
        else:
            name = QLabel(os.path.basename(path))
            name.setWordWrap(True)
            name.setAlignment(Qt.AlignCenter)
            name.setStyleSheet('font-size: 15px;')
            layout.addWidget(name, 1)

        self._play_button = QPushButton(tr('暂停'))
        self._play_button.setFixedWidth(72)
        self._play_button.clicked.connect(self._toggle)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.sliderMoved.connect(self._player.setPosition)
        self._time = QLabel('00:00 / 00:00')
        bar = QHBoxLayout()
        bar.addWidget(self._play_button)
        bar.addWidget(self._slider, 1)
        bar.addWidget(self._time)
        layout.addLayout(bar)

        self._player.durationChanged.connect(self._on_duration)
        self._player.positionChanged.connect(self._on_position)
        self._player.stateChanged.connect(self._on_state)
        self._player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        self._player.play()

    def _toggle(self):
        from PyQt5.QtMultimedia import QMediaPlayer
        if self._player.state() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_state(self, state):
        from PyQt5.QtMultimedia import QMediaPlayer
        self._play_button.setText(
            tr('暂停') if state == QMediaPlayer.PlayingState else tr('播放'))

    def _on_duration(self, duration):
        self._slider.setRange(0, duration)
        self._update_time(self._player.position(), duration)

    def _on_position(self, position):
        if not self._slider.isSliderDown():
            self._slider.setValue(position)
        self._update_time(position, self._player.duration())

    def _update_time(self, position, duration):
        self._time.setText(f'{self._fmt(position)} / {self._fmt(duration)}')

    @staticmethod
    def _fmt(ms):
        secs = max(0, ms) // 1000
        return f'{secs // 60:02d}:{secs % 60:02d}'

    def closeEvent(self, event):
        self._player.stop()
        super().closeEvent(event)


class MediaLibWindow(QMainWindow):
    """媒体库页面：媒体库卡片 → 社团卡片 → 作品卡片 三级浏览"""

    def __init__(self):
        super().__init__()
        loadUi("src/QTui/ui_file/media_lib.ui", self)

        self.back_button = self.findChild(QPushButton, 'back_button')
        self.count_label = self.findChild(QLabel, 'count_label')
        self.search_edit = self.findChild(QLineEdit, 'search_edit')
        self.genre_button = self.findChild(QPushButton, 'genre_button')
        self.lib_setting_button = self.findChild(QPushButton, 'lib_setting_button')
        self.open_folder_button = self.findChild(QPushButton, 'open_folder_button')
        self.view_files_button = self.findChild(QPushButton, 'view_files_button')
        self.move_lib_button = self.findChild(QPushButton, 'move_lib_button')
        self.cards_scroll = self.findChild(QScrollArea, 'cards_scroll')
        self.cards_container = self.cards_scroll.widget()

        self.grid = QGridLayout(self.cards_container)
        self.grid.setContentsMargins(0, 0, 6, 0)
        self.grid.setSpacing(CARD_GAP)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.cards = []
        self._columns = 0
        self._card_width = 240
        self._root = 'libs'   # 根视图：'libs'=媒体库页 / 'genres'=标签页
        self._level = 'libs'  # 'libs' / 'makers' / 'works' / 'detail' / 'genres'
        self._current_lib = None
        self._current_maker = None  # None=未选社团；UNKNOWN_MAKER=未知社团
        self._current_genre = None  # 非 None 时作品视图按标签查询
        self._current_work = None
        self._detail_widget = None
        self._total_works = 0
        self._works_scroll_pos = 0
        self._current_work_folder = None
        self._filter_col = None
        self._filter_val = None
        self._work_rows = []      # 作品视图：全部查询结果
        self._filtered_rows = []  # 作品视图：搜索过滤后的结果（懒加载来源）
        self.setting_dialog = None

        self.back_button.clicked.connect(self.go_back)
        self.genre_button.clicked.connect(self.show_genres)
        self.lib_setting_button.clicked.connect(self.open_lib_settings)
        self.open_folder_button.clicked.connect(self._open_work_folder)
        self.open_folder_button.setVisible(False)
        self.view_files_button.clicked.connect(self._toggle_file_tree)
        self.view_files_button.setVisible(False)
        self._detail_right_stack = None  # 详情页右侧 信息/文件树 切换栈
        self.move_lib_button.clicked.connect(self._move_work_library)
        self.move_lib_button.setVisible(False)
        self._move_worker = None
        self.search_edit.textChanged.connect(self._apply_filter)
        self.cards_scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.retranslate_ui()
        notifier.language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self):
        self.setWindowTitle(tr('标签') if self._root == 'genres' else tr('媒体库'))
        self.back_button.setText(tr('← 返回'))
        self.genre_button.setText(tr('作品标签'))
        self.lib_setting_button.setText(tr('媒体库设置'))
        self.open_folder_button.setText(tr('打开文件夹'))
        self.view_files_button.setText(tr('查看作品'))
        self.move_lib_button.setText(tr('移动媒体库'))
        self.search_edit.setPlaceholderText(tr('搜索 RJ号 / 作品名 / 社团'))
        self.refresh()

    def showEvent(self, event):
        """切换到本页时重新加载数据：先丢弃配置缓存，再重查数据库刷新当前视图"""
        super().showEvent(event)
        Config().reload()
        self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._level != 'detail' and self._column_count() != self._columns:
            self._relayout()

    def open_lib_settings(self):
        """打开媒体库设置弹窗（常驻实例，扫描线程随其存活）"""
        if self.setting_dialog is None:
            self.setting_dialog = MediaLibSettingDialog(self)
            self.setting_dialog.libs_changed.connect(self.refresh)
            self.setting_dialog.scan_done.connect(self.refresh)
        self.setting_dialog.show()
        self.setting_dialog.raise_()
        self.setting_dialog.activateWindow()

    # ---------- 导航 ----------

    def _open_lib(self, name):
        """点击媒体库卡片：进入该库的社团视图"""
        self._current_lib = name
        self._current_maker = None
        self._current_genre = None
        self._show_makers()

    def _open_maker(self, maker):
        """点击社团卡片：显示该社团的作品"""
        self._current_maker = maker
        self._show_works()

    def show_genres(self):
        """点击"作品标签"按钮：进入标签视图（全部媒体库范围）"""
        self._current_lib = None
        self._current_maker = None
        self._current_genre = None
        self._current_work = None
        self._show_genres()

    def _open_genre(self, genre):
        """点击标签卡片 / 详情页标签链接：显示拥有该标签作品的社团"""
        self._current_genre = genre
        self._show_makers()

    def _open_work(self, work_id):
        """点击作品卡片：显示作品详情"""
        self._works_scroll_pos = self.cards_scroll.verticalScrollBar().value()
        self._current_work = work_id
        self._show_detail()

    def go_back(self):
        if self._level == 'filtered_works':
            self._show_detail()
        elif self._level == 'detail':
            self._current_work = None
            self._show_works()
            self._restore_works_scroll()
        elif self._level == 'works':
            self._current_maker = None
            self._show_makers()
        elif self._level == 'makers':
            if self._current_genre is not None:
                self._current_genre = None
                self._show_genres()
            else:
                self._show_libs()
        elif self._level == 'genres' and self._root != 'genres':
            self._show_libs()

    def _open_work_folder(self):
        if self._current_work_folder and os.path.isdir(self._current_work_folder):
            os.startfile(self._current_work_folder)

    def _toggle_file_tree(self):
        """详情页右侧在“信息面板”与“文件树”之间切换"""
        stack = self._detail_right_stack
        if stack is None or not self._current_work_folder:
            return
        if stack.currentIndex() == 0:
            if stack.count() < 2:  # 首次切换时才构建文件树
                stack.addWidget(self._build_file_tree(self._current_work_folder))
            stack.setCurrentIndex(1)
            self.view_files_button.setText(tr('作品信息'))
        else:
            stack.setCurrentIndex(0)
            self.view_files_button.setText(tr('查看作品'))

    def _build_file_tree(self, root):
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setMinimumHeight(360)
        self._populate_tree(tree.invisibleRootItem(), root)
        tree.itemClicked.connect(self._on_tree_item_clicked)
        return tree

    def _populate_tree(self, parent_item, path):
        """递归填充：文件夹在前、文件在后，各自按名称排序"""
        try:
            names = os.listdir(path)
        except OSError:
            return
        names.sort(key=lambda n: (not os.path.isdir(os.path.join(path, n)), n.lower()))
        for name in names:
            full = os.path.join(path, name)
            item = QTreeWidgetItem(parent_item, [name])
            item.setData(0, Qt.UserRole, full)
            if os.path.isdir(full):
                self._populate_tree(item, full)

    def _on_tree_item_clicked(self, item, column):
        """点击文件：图片→程序内看图（左右切换），视频/音频→内嵌播放器，其它→系统默认程序"""
        from src.DLsite.DLsite_page import IMAGE_EXTS
        path = item.data(0, Qt.UserRole)
        if not path or os.path.isdir(path):
            return  # 文件夹交给树自身展开/折叠
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXTS:
            folder = os.path.dirname(path)
            images = [os.path.join(folder, f) for f in sorted(os.listdir(folder))
                      if f.lower().endswith(IMAGE_EXTS)]
            ImageViewerDialog(images, images.index(path), self).exec_()
        elif ext in VIDEO_EXTS or ext in AUDIO_EXTS:
            MediaPlayerDialog(path, ext in VIDEO_EXTS, self).exec_()
        else:
            os.startfile(path)

    def _move_work_library(self):
        """把当前作品移动到另一个媒体库：移动文件夹 + 改库 + 同步元数据，旧库自动移除"""
        work_id = self._current_work
        if not work_id:
            return
        if not (self._current_work_folder and os.path.isdir(self._current_work_folder)):
            QMessageBox.warning(self, tr('移动媒体库'), tr('作品文件夹不存在，无法移动'))
            return
        result = SQLiteDB().select(
            f'''SELECT "library" FROM "main"."works" WHERE "work_id" = '{work_id}' ''')
        current_lib = result[1][0][0] if result is not False and result[1] else None

        dlg = _MoveLibDialog(current_lib, self)
        if dlg.exec_() != QDialog.Accepted or not dlg.selected:
            return
        target_lib, target_folder = dlg.selected
        answer = QMessageBox.question(
            self, tr('移动媒体库'),
            tr('确定将 {id} 移动到媒体库“{lib}”吗？').format(id=work_id, lib=target_lib),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return

        self.move_lib_button.setEnabled(False)
        self.move_lib_button.setText(tr('移动中…'))
        self._move_worker = _MoveWorker(work_id, target_lib, target_folder, self)
        self._move_worker.done.connect(self._on_move_done)
        self._move_worker.start()

    def _on_move_done(self, ok, msg):
        self.move_lib_button.setEnabled(True)
        self.move_lib_button.setText(tr('移动媒体库'))
        if ok:
            QMessageBox.information(self, tr('移动媒体库'), tr('已移动到新媒体库'))
            self.refresh()  # 重新载入详情，反映新的媒体库与文件夹
        else:
            QMessageBox.warning(self, tr('移动媒体库'), msg)

    def _open_filter(self, column, value):
        """点击详情页可跳转字段：按列过滤作品"""
        self._filter_col = column
        self._filter_val = value
        self._show_filtered_works()

    def _show_filtered_works(self):
        """按单列值过滤的作品视图（跨所有媒体库）"""
        self._level = 'filtered_works'
        self._card_width = WORK_CARD_W
        self.back_button.setVisible(True)
        val_esc = self._filter_val.replace("'", "''")
        if self._filter_col == 'voice_actor':
            cond = f'"voice_actor" LIKE \'%{val_esc}%\''
        else:
            cond = f'"{self._filter_col}" = \'{val_esc}\''
        sql = (f'SELECT "work_id", "work_name", "maker_name", "work_type", "age_category", "cover"'
               f' FROM "main"."works" WHERE "state" = \'已品悦\' AND {cond}'
               f' ORDER BY "work_id" DESC')
        result = SQLiteDB().select(sql)
        if result is False:
            return
        self._work_rows = result[1]
        self._apply_filter()

    def _restore_works_scroll(self):
        target = self._works_scroll_pos
        if target <= 0:
            return
        # 预加载直到内容高度能容纳目标滚动位置
        while (len(self.cards) < len(self._filtered_rows)
               and self.cards_container.sizeHint().height()
                   < target + self.cards_scroll.viewport().height()):
            self._load_more_works()
        QTimer.singleShot(0, lambda: self.cards_scroll.verticalScrollBar().setValue(target))

    def _show_root(self):
        if self._root == 'genres':
            self._show_genres()
        else:
            self._show_libs()

    def refresh(self):
        """重新加载当前层级的视图"""
        names = {lib['name'] for lib in Config().read_media_libs()}
        if self._current_lib is not None and self._current_lib not in names:
            # 当前库已被删除/改名，回到根视图
            self._show_root()
        elif self._level == 'filtered_works' and self._filter_col:
            self._show_filtered_works()
        elif self._level == 'detail' and self._current_work:
            self._show_detail()
        elif self._level in ('works', 'detail') and self._current_maker is not None:
            self._show_works()
        elif self._level == 'makers' and (self._current_lib is not None
                                          or self._current_genre is not None):
            self._show_makers()
        elif self._level == 'genres':
            self._show_genres()
        else:
            self._show_root()

    # ---------- 三级视图 ----------

    def _clear_cards(self):
        for card in self.cards:
            card.deleteLater()
        self.cards = []
        if self._detail_widget is not None:
            self._detail_widget.deleteLater()
            self._detail_widget = None
        self.open_folder_button.setVisible(False)
        self.view_files_button.setVisible(False)
        self.view_files_button.setText(tr('查看作品'))
        self._detail_right_stack = None
        self.move_lib_button.setVisible(False)
        self._current_work_folder = None

    def _show_libs(self):
        """一级：媒体库卡片"""
        self._level = 'libs'
        self._current_lib = None
        self._current_maker = None
        self._card_width = WORK_CARD_W
        self.back_button.setVisible(False)
        counts = {}
        result = SQLiteDB().select('''SELECT "library", COUNT(*) FROM "main"."works"
                                      WHERE "state" = '已品悦' GROUP BY "library"''')
        if result is not False:
            counts = {row[0]: row[1] for row in result[1]}
        self._total_works = sum(counts.values())
        self._clear_cards()
        self.cards = [
            ClickCard(lib['name'],
                      tr('{works} 个作品 · {folders} 个文件夹').format(
                          works=counts.get(lib['name'], 0), folders=len(lib['folders'])),
                      lib['name'], self._open_lib, WORK_CARD_W, 110, parent=self.cards_container)
            for lib in Config().read_media_libs()
        ]
        self._apply_filter()

    def _show_makers(self):
        """二级：当前媒体库（或当前标签）下的社团卡片"""
        self._level = 'makers'
        self._current_maker = None
        self._card_width = WORK_CARD_W
        self.back_button.setVisible(True)
        if self._current_genre is not None:
            genre_esc = self._current_genre.replace("'", "''")
            sql = f'''SELECT w."maker_name", COUNT(*) FROM "main"."works" w
                      JOIN "main"."work_genres" g ON g."work_id" = w."work_id"
                      WHERE w."state" = '已品悦' AND g."genre" = '{genre_esc}'
                      GROUP BY w."maker_name" ORDER BY COUNT(*) DESC'''
        else:
            lib_esc = self._current_lib.replace("'", "''")
            sql = f'''SELECT "maker_name", COUNT(*) FROM "main"."works"
                      WHERE "state" = '已品悦' AND "library" = '{lib_esc}'
                      GROUP BY "maker_name" ORDER BY COUNT(*) DESC'''
        result = SQLiteDB().select(sql)
        if result is False:
            return
        self._total_works = sum(row[1] for row in result[1])
        self._clear_cards()
        self.cards = [
            ClickCard(maker or tr('未知社团'), tr('{count} 个作品').format(count=count),
                      maker or UNKNOWN_MAKER, self._open_maker, WORK_CARD_W, 110,
                      parent=self.cards_container)
            for maker, count in result[1]
        ]
        self._apply_filter()

    def _show_genres(self):
        """标签视图：全部已品悦作品的ジャンル标签卡片"""
        self._level = 'genres'
        self._card_width = WORK_CARD_W
        self.back_button.setVisible(self._root != 'genres')
        db = SQLiteDB()
        result = db.select('''SELECT g."genre", COUNT(*) FROM "main"."work_genres" g
                              JOIN "main"."works" w ON w."work_id" = g."work_id"
                              WHERE w."state" = '已品悦'
                              GROUP BY g."genre" ORDER BY COUNT(*) DESC''')
        if result is False:
            return
        total = db.select('''SELECT COUNT(DISTINCT g."work_id") FROM "main"."work_genres" g
                             JOIN "main"."works" w ON w."work_id" = g."work_id"
                             WHERE w."state" = '已品悦' ''')
        self._total_works = total[1][0][0] if total is not False else 0
        self._clear_cards()
        self.cards = [
            ClickCard(genre, tr('{count} 个作品').format(count=count), genre,
                      self._open_genre, WORK_CARD_W, 110, parent=self.cards_container)
            for genre, count in result[1]
        ]
        self._apply_filter()

    def _show_works(self):
        """三级：当前社团的作品卡片（标签流程下为 标签+社团）"""
        self._level = 'works'
        self._card_width = WORK_CARD_W
        self.back_button.setVisible(True)
        if self._current_maker == UNKNOWN_MAKER:
            maker_cond = '''("maker_name" IS NULL OR "maker_name" = '')'''
        else:
            maker_cond = f'''"maker_name" = '{self._current_maker.replace("'", "''")}' '''
        if self._current_genre is not None:
            genre_esc = self._current_genre.replace("'", "''")
            sql = f'''SELECT w."work_id", w."work_name", w."maker_name", w."work_type",
                             w."age_category", w."cover"
                      FROM "main"."works" w
                      JOIN "main"."work_genres" g ON g."work_id" = w."work_id"
                      WHERE w."state" = '已品悦' AND g."genre" = '{genre_esc}' AND {maker_cond}
                      ORDER BY w."work_id" DESC'''
        else:
            lib_esc = (self._current_lib or '').replace("'", "''")
            sql = f'''SELECT "work_id", "work_name", "maker_name", "work_type", "age_category", "cover"
                      FROM "main"."works" WHERE "state" = '已品悦'
                      AND "library" = '{lib_esc}' AND {maker_cond}
                      ORDER BY "work_id" DESC'''
        result = SQLiteDB().select(sql)
        if result is False:
            return
        self._work_rows = result[1]
        self._apply_filter()

    def _show_detail(self):
        """四级：作品详情（全部图片 + 数据库字段）"""
        result = SQLiteDB().select(
            f'''SELECT "work_id", "work_name", "maker_name", "sell_date", "series",
                       "scenario", "illust", "voice_actor", "age_category", "work_type",
                       "genre", "file_size", "intro_s", "folder"
                FROM "main"."works" WHERE "work_id" = '{self._current_work}' ''')
        if result is False or not result[1]:
            return
        (work_id, work_name, maker_name, sell_date, series, scenario, illust,
         voice_actor, age_category, work_type, genre, file_size, intro_s,
         work_folder) = result[1][0]

        self._level = 'detail'
        self.back_button.setVisible(True)
        self.count_label.setText(work_id)
        self._clear_cards()
        if work_folder and os.path.isdir(work_folder):
            self._current_work_folder = work_folder
            self.open_folder_button.setVisible(True)
            self.view_files_button.setVisible(True)
            self.move_lib_button.setVisible(True)

        widget = QFrame(self.cards_container)
        widget.setProperty('class', 'card')
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel(work_name or work_id)
        title.setWordWrap(True)
        title.setStyleSheet('font-weight: 600; font-size: 18px;')
        layout.addWidget(title)

        from src.DLsite.DLsite_page import (DATA_SOURCE_DIR, DESCRIPTION_TXT,
                                            IMAGE_EXTS, BODY_IMAGE_RE)
        folder = os.path.join(work_folder, DATA_SOURCE_DIR) if work_folder else ''
        if not os.path.isdir(folder):
            folder = os.path.join('images', work_id)

        # 正文：按 [img:文件名] 占位标记拆成 文本/图片 块
        body_blocks = []
        body_files = set()
        txt_path = os.path.join(folder, DESCRIPTION_TXT)
        if os.path.isfile(txt_path):
            try:
                with open(txt_path, encoding='utf-8') as f:
                    body_text = f.read().strip()
            except OSError:
                body_text = ''
            buf = []
            for line in body_text.splitlines():
                match = BODY_IMAGE_RE.match(line.strip())
                if match:
                    if buf:
                        body_blocks.append(('text', '\n'.join(buf)))
                        buf = []
                    body_blocks.append(('image', match.group(1)))
                    body_files.add(match.group(1))
                else:
                    buf.append(line)
            if buf:
                body_blocks.append(('text', '\n'.join(buf)))

        # 轮播图：数据源中除正文图片外的图片，主图排最前
        slider_paths = []
        if os.path.isdir(folder):
            names = [f for f in sorted(os.listdir(folder))
                     if f.lower().endswith(IMAGE_EXTS) and f not in body_files]
            names.sort(key=lambda f: (0 if 'img_main' in f.lower() else 1, f))
            slider_paths = [os.path.join(folder, f) for f in names]

        # 标签来自 work_genres 表，渲染为可点击链接；没有记录时退回 genre 字符串
        genre_links = None
        tags_result = SQLiteDB().select(
            f'''SELECT "genre" FROM "main"."work_genres" WHERE "work_id" = '{work_id}' ''')
        if tags_result is not False and tags_result[1]:
            genre_links = QLabel('　'.join(
                f'<a href="{html.escape(tag, quote=True)}">{html.escape(tag)}</a>'
                for tag, in tags_result[1]))
            genre_links.setWordWrap(True)
            genre_links.setTextFormat(Qt.RichText)
            genre_links.linkActivated.connect(self._open_genre)

        fields = [('社团', maker_name), ('販売日', sell_date),
                  ('系列', series), ('剧本', scenario), ('插画', illust),
                  ('声优', voice_actor), ('年龄分级', age_category), ('作品形式', work_type),
                  ('类型', genre), ('文件容量', file_size), ('简介', intro_s)]
        form = QGridLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(6)
        form.setColumnStretch(1, 1)
        row = 0
        for label, value in fields:
            if label == '类型' and genre_links is not None:
                value_label = genre_links
            elif not value:
                continue
            elif label == '年龄分级':
                display = tr(_AGE_MAP.get(str(value), str(value)))
                value_label = QLabel(
                    f'<a href="{html.escape(str(value), quote=True)}">{html.escape(display)}</a>')
                value_label.setWordWrap(True)
                value_label.setTextFormat(Qt.RichText)
                value_label.linkActivated.connect(
                    lambda v, c='age_category': self._open_filter(c, v))
            elif label in _LINK_COLS:
                col, is_multi = _LINK_COLS[label]
                parts = ([p.strip() for p in str(value).split(' / ') if p.strip()]
                         if is_multi else [str(value).strip()])
                links_html = ' / '.join(
                    f'<a href="{html.escape(p, quote=True)}">{html.escape(p)}</a>'
                    for p in parts if p)
                value_label = QLabel(links_html)
                value_label.setWordWrap(True)
                value_label.setTextFormat(Qt.RichText)
                value_label.linkActivated.connect(
                    lambda v, c=col: self._open_filter(c, v))
            else:
                value_label = QLabel(str(value))
                value_label.setWordWrap(True)
                value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            key_label = QLabel(tr(label))
            key_label.setProperty('class', 'caption')
            form.addWidget(key_label, row, 0, Qt.AlignTop)
            form.addWidget(value_label, row, 1)
            row += 1

        # 上半部分：左边轮播图（1/3），右边字段详情（2/3）。
        # 右侧用 QStackedWidget 承载“信息面板 / 文件树”两页，由“查看作品”按钮切换。
        content = QHBoxLayout()
        content.setSpacing(20)
        if slider_paths:
            content.addWidget(ImageSlider(slider_paths, widget), 1, Qt.AlignTop)
        info_page = QWidget()
        info_layout = QVBoxLayout(info_page)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addLayout(form)
        info_layout.addStretch()
        right_stack = QStackedWidget()
        right_stack.addWidget(info_page)
        self._detail_right_stack = right_stack
        content.addWidget(right_stack, 2)
        layout.addLayout(content)

        # 正文：文本与图片按原文顺序嵌入
        max_width = max(360, self.cards_scroll.viewport().width() - 100)
        for kind, value in body_blocks:
            if kind == 'text':
                if not value.strip():
                    continue
                body_label = QLabel(value)
                body_label.setWordWrap(True)
                body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                layout.addWidget(body_label)
            else:
                pixmap = QPixmap(os.path.join(folder, value))
                if pixmap.isNull():
                    continue
                if pixmap.width() > max_width:
                    pixmap = pixmap.scaledToWidth(max_width, Qt.SmoothTransformation)
                image_label = QLabel()
                image_label.setPixmap(pixmap)
                layout.addWidget(image_label)

        self._detail_widget = widget
        self.grid.addWidget(widget, 0, 0)
        widget.setVisible(True)
        self.cards_scroll.verticalScrollBar().setValue(0)

    # ---------- 过滤与布局 ----------

    def _apply_filter(self):
        if self._level == 'detail':
            return
        keyword = self.search_edit.text().strip().lower()
        if self._level in ('works', 'filtered_works'):
            # 作品视图：在全量查询结果上过滤，再懒加载
            if keyword:
                self._filtered_rows = [
                    row for row in self._work_rows
                    if keyword in f'{row[0]} {row[1] or ""} {row[2] or ""}'.lower()]
            else:
                self._filtered_rows = list(self._work_rows)
            self._clear_cards()
            self._load_more_works()
            # 首屏未填满（出不来滚动条）时继续加载
            while (len(self.cards) < len(self._filtered_rows)
                   and self.cards_container.sizeHint().height()
                   <= self.cards_scroll.viewport().height()):
                self._load_more_works()
            return
        shown = 0
        for card in self.cards:
            visible = (not keyword) or (keyword in card.search_text)
            card.setVisible(visible)
            if visible:
                shown += 1
        self._relayout()
        total = len(self.cards)
        unit = tr({'libs': '个媒体库', 'makers': '个社团', 'genres': '个标签'}[self._level])
        if keyword:
            self.count_label.setText(
                tr('共 {total} {unit}，匹配 {shown} 个').format(total=total, unit=unit, shown=shown))
        else:
            self.count_label.setText(
                tr('共 {total} {unit}，{works} 个作品').format(
                    total=total, unit=unit, works=self._total_works))

    def _load_more_works(self):
        """作品视图：追加加载下一批卡片"""
        batch = self._filtered_rows[len(self.cards):len(self.cards) + WORKS_PAGE]
        for row in batch:
            card = WorkCard(*row, on_click=self._open_work, parent=self.cards_container)
            card.setVisible(True)
            self.cards.append(card)
        if batch:
            self._relayout()
        keyword = self.search_edit.text().strip()
        total, matched, loaded = len(self._work_rows), len(self._filtered_rows), len(self.cards)
        text = (tr('共 {total} 个作品，匹配 {matched} 个').format(total=total, matched=matched)
                if keyword else tr('共 {total} 个作品').format(total=total))
        if loaded < matched:
            text += tr('（已加载 {loaded}）').format(loaded=loaded)
        self.count_label.setText(text)

    def _on_scroll(self, value):
        """滚动接近底部时加载下一批作品卡片"""
        if self._level not in ('works', 'filtered_works') or len(self.cards) >= len(self._filtered_rows):
            return
        bar = self.cards_scroll.verticalScrollBar()
        if value >= bar.maximum() - 300:
            self._load_more_works()

    def _column_count(self):
        width = self.cards_scroll.viewport().width()
        return max(1, (width - CARD_GAP) // (self._card_width + CARD_GAP))

    def _relayout(self):
        """把可见卡片按当前宽度重排成网格"""
        self._columns = self._column_count()
        while self.grid.count():
            self.grid.takeAt(0)
        row = col = 0
        for card in self.cards:
            if card.isHidden():
                continue
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= self._columns:
                col = 0
                row += 1


class TagWindow(MediaLibWindow):
    """标签页面：标签 → 社团 → 作品 三级浏览（复用媒体库实现，根视图为标签）"""

    def __init__(self):
        super().__init__()
        self._root = 'genres'
        self._level = 'genres'
        self.genre_button.setVisible(False)       # 根视图就是标签页
        self.lib_setting_button.setVisible(False)  # 媒体库管理只保留在媒体库页
