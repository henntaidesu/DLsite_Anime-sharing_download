import os
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLabel, QLineEdit,
                             QFrame, QScrollArea, QGridLayout, QVBoxLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.uic import loadUi
from src.module.conf_operate import Config
from src.module.datebase_execution import SQLiteDB
from src.QTui.media_lib_setting_UI import MediaLibSettingDialog

CARD_GAP = 10
WORKS_PAGE = 30  # 作品卡片懒加载：每批数量
UNKNOWN_MAKER = ''  # maker_name 为空的作品归到"未知社团"


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


class WorkCard(QFrame):
    """单个作品卡片：封面图 / 作品名 / RJ号·类型·年龄分级 / 社团，点击进入作品详情"""

    def __init__(self, work_id, work_name, maker_name, work_type, age_category, cover,
                 on_click, parent=None):
        super().__init__(parent)
        self.setProperty('class', 'card')
        self.setFixedWidth(210)
        self.setCursor(Qt.PointingHandCursor)
        self.search_text = f'{work_id} {work_name or ""} {maker_name or ""}'.lower()
        self._work_id = work_id
        self._on_click = on_click

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        if cover and os.path.exists(cover):
            pixmap = QPixmap(cover)
            if not pixmap.isNull():
                cover_label = QLabel()
                cover_label.setAlignment(Qt.AlignCenter)
                cover_label.setPixmap(pixmap.scaled(
                    186, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                layout.addWidget(cover_label)

        name_label = QLabel(work_name or work_id)
        name_label.setWordWrap(True)
        name_label.setStyleSheet('font-weight: 600;')
        layout.addWidget(name_label)

        meta = ' · '.join(str(x) for x in (work_id, work_type, age_category) if x)
        meta_label = QLabel(meta)
        meta_label.setProperty('class', 'caption')
        layout.addWidget(meta_label)

        if maker_name:
            maker_label = QLabel(str(maker_name))
            maker_label.setProperty('class', 'caption')
            layout.addWidget(maker_label)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_click(self._work_id)
        super().mousePressEvent(event)


class MediaLibWindow(QMainWindow):
    """媒体库页面：媒体库卡片 → 社团卡片 → 作品卡片 三级浏览"""

    def __init__(self):
        super().__init__()
        loadUi("src/QTui/ui_file/media_lib.ui", self)

        self.back_button = self.findChild(QPushButton, 'back_button')
        self.count_label = self.findChild(QLabel, 'count_label')
        self.search_edit = self.findChild(QLineEdit, 'search_edit')
        self.lib_setting_button = self.findChild(QPushButton, 'lib_setting_button')
        self.cards_scroll = self.findChild(QScrollArea, 'cards_scroll')
        self.cards_container = self.cards_scroll.widget()

        self.grid = QGridLayout(self.cards_container)
        self.grid.setContentsMargins(0, 0, 6, 0)
        self.grid.setSpacing(CARD_GAP)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.cards = []
        self._columns = 0
        self._card_width = 240
        self._level = 'libs'  # 'libs' / 'makers' / 'works' / 'detail'
        self._current_lib = None
        self._current_maker = None  # None=未选社团；UNKNOWN_MAKER=未知社团
        self._current_work = None
        self._detail_widget = None
        self._total_works = 0
        self._work_rows = []      # 作品视图：全部查询结果
        self._filtered_rows = []  # 作品视图：搜索过滤后的结果（懒加载来源）
        self.setting_dialog = None

        self.back_button.clicked.connect(self.go_back)
        self.lib_setting_button.clicked.connect(self.open_lib_settings)
        self.search_edit.textChanged.connect(self._apply_filter)
        self.cards_scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

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
        self._show_makers()

    def _open_maker(self, maker):
        """点击社团卡片：显示该社团的作品"""
        self._current_maker = maker
        self._show_works()

    def _open_work(self, work_id):
        """点击作品卡片：显示作品详情"""
        self._current_work = work_id
        self._show_detail()

    def go_back(self):
        if self._level == 'detail':
            self._current_work = None
            self._show_works()
        elif self._level == 'works':
            self._current_maker = None
            self._show_makers()
        elif self._level == 'makers':
            self._show_libs()

    def refresh(self):
        """重新加载当前层级的视图"""
        names = {lib['name'] for lib in Config().read_media_libs()}
        if self._level != 'libs' and self._current_lib not in names:
            # 当前库已被删除/改名，回到媒体库视图
            self._show_libs()
        elif self._level == 'detail' and self._current_work:
            self._show_detail()
        elif self._level in ('works', 'detail') and self._current_maker is not None:
            self._show_works()
        elif self._level == 'makers':
            self._show_makers()
        else:
            self._show_libs()

    # ---------- 三级视图 ----------

    def _clear_cards(self):
        for card in self.cards:
            card.deleteLater()
        self.cards = []
        if self._detail_widget is not None:
            self._detail_widget.deleteLater()
            self._detail_widget = None

    def _show_libs(self):
        """一级：媒体库卡片"""
        self._level = 'libs'
        self._current_lib = None
        self._current_maker = None
        self._card_width = 240
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
                      f"{counts.get(lib['name'], 0)} 个作品 · {len(lib['folders'])} 个文件夹",
                      lib['name'], self._open_lib, 240, 130, parent=self.cards_container)
            for lib in Config().read_media_libs()
        ]
        self._apply_filter()

    def _show_makers(self):
        """二级：当前媒体库下的社团卡片"""
        lib = self._current_lib
        self._level = 'makers'
        self._current_maker = None
        self._card_width = 220
        self.back_button.setVisible(True)
        sql = f'''SELECT "maker_name", COUNT(*) FROM "main"."works"
                  WHERE "state" = '已品悦' AND "library" = '{lib.replace("'", "''")}'
                  GROUP BY "maker_name" ORDER BY COUNT(*) DESC'''
        result = SQLiteDB().select(sql)
        if result is False:
            return
        self._total_works = sum(row[1] for row in result[1])
        self._clear_cards()
        self.cards = [
            ClickCard(maker or '未知社团', f'{count} 个作品',
                      maker or UNKNOWN_MAKER, self._open_maker, 220, 110,
                      parent=self.cards_container)
            for maker, count in result[1]
        ]
        self._apply_filter()

    def _show_works(self):
        """三级：当前社团的作品卡片"""
        self._level = 'works'
        self._card_width = 210
        self.back_button.setVisible(True)
        lib_esc = (self._current_lib or '').replace("'", "''")
        if self._current_maker == UNKNOWN_MAKER:
            maker_cond = '''("maker_name" IS NULL OR "maker_name" = '')'''
        else:
            maker_cond = f'''"maker_name" = '{self._current_maker.replace("'", "''")}' '''
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

        widget = QFrame(self.cards_container)
        widget.setProperty('class', 'card')
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel(work_name or work_id)
        title.setWordWrap(True)
        title.setStyleSheet('font-weight: 600; font-size: 18px;')
        layout.addWidget(title)

        fields = [('RJ号', work_id), ('社团', maker_name), ('販売日', sell_date),
                  ('系列', series), ('剧本', scenario), ('插画', illust),
                  ('声优', voice_actor), ('年龄分级', age_category), ('作品形式', work_type),
                  ('类型', genre), ('文件容量', file_size), ('简介', intro_s)]
        form = QGridLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(6)
        form.setColumnStretch(1, 1)
        row = 0
        for label, value in fields:
            if not value:
                continue
            key_label = QLabel(label)
            key_label.setProperty('class', 'caption')
            value_label = QLabel(str(value))
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addWidget(key_label, row, 0, Qt.AlignTop)
            form.addWidget(value_label, row, 1)
            row += 1
        layout.addLayout(form)

        from src.DLsite.DLsite_page import DATA_SOURCE_DIR, DESCRIPTION_TXT
        folder = os.path.join(work_folder, DATA_SOURCE_DIR) if work_folder else ''
        if not os.path.isdir(folder):
            folder = os.path.join('images', work_id)

        # 作品页正文文本（扫描时保存的 description.txt）
        txt_path = os.path.join(folder, DESCRIPTION_TXT)
        if os.path.isfile(txt_path):
            try:
                with open(txt_path, encoding='utf-8') as f:
                    body_text = f.read().strip()
            except OSError:
                body_text = ''
            if body_text:
                body_label = QLabel(body_text)
                body_label.setWordWrap(True)
                body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                layout.addWidget(body_label)

        # 已下载的全部图片（img_main 排在最前）
        if os.path.isdir(folder):
            max_width = max(360, self.cards_scroll.viewport().width() - 100)
            for filename in sorted(os.listdir(folder)):
                pixmap = QPixmap(os.path.join(folder, filename))
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
        if self._level == 'works':
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
        unit = {'libs': '个媒体库', 'makers': '个社团'}[self._level]
        if keyword:
            self.count_label.setText(f'共 {total} {unit}，匹配 {shown} 个')
        else:
            self.count_label.setText(f'共 {total} {unit}，{self._total_works} 个作品')

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
        text = f'共 {total} 个作品，匹配 {matched} 个' if keyword else f'共 {total} 个作品'
        if loaded < matched:
            text += f'（已加载 {loaded}）'
        self.count_label.setText(text)

    def _on_scroll(self, value):
        """滚动接近底部时加载下一批作品卡片"""
        if self._level != 'works' or len(self.cards) >= len(self._filtered_rows):
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
