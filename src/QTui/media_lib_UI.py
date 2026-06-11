from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLabel, QLineEdit, QComboBox,
                             QFrame, QScrollArea, QGridLayout, QVBoxLayout)
from PyQt5.QtCore import Qt
from PyQt5.uic import loadUi
from src.module.conf_operate import Config
from src.module.datebase_execution import SQLiteDB
from src.QTui.media_lib_setting_UI import MediaLibSettingDialog

CARD_WIDTH = 210
CARD_GAP = 10
ALL_LIBS = '全部媒体库'


class WorkCard(QFrame):
    """单个作品卡片：作品名 / RJ号·类型·年龄分级 / 社团"""

    def __init__(self, work_id, work_name, maker_name, work_type, age_category, parent=None):
        super().__init__(parent)
        self.setProperty('class', 'card')
        self.setFixedWidth(CARD_WIDTH)
        self.search_text = f'{work_id} {work_name or ""} {maker_name or ""}'.lower()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

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


class MediaLibWindow(QMainWindow):
    """媒体库页面：卡片网格展示已品悦（媒体库导入）的作品，可按媒体库筛选"""

    def __init__(self):
        super().__init__()
        loadUi("src/QTui/ui_file/media_lib.ui", self)

        self.count_label = self.findChild(QLabel, 'count_label')
        self.lib_choose = self.findChild(QComboBox, 'lib_choose')
        self.search_edit = self.findChild(QLineEdit, 'search_edit')
        self.refresh_button = self.findChild(QPushButton, 'refresh_button')
        self.lib_setting_button = self.findChild(QPushButton, 'lib_setting_button')
        self.cards_scroll = self.findChild(QScrollArea, 'cards_scroll')
        self.cards_container = self.cards_scroll.widget()

        self.grid = QGridLayout(self.cards_container)
        self.grid.setContentsMargins(0, 0, 6, 0)
        self.grid.setSpacing(CARD_GAP)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.cards = []
        self._columns = 0
        self.setting_dialog = None

        self.refresh_button.clicked.connect(self.refresh)
        self.lib_setting_button.clicked.connect(self.open_lib_settings)
        self.search_edit.textChanged.connect(self._apply_filter)
        self.lib_choose.currentIndexChanged.connect(self.refresh)

    def showEvent(self, event):
        super().showEvent(event)
        self._reload_libs()
        self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._column_count() != self._columns:
            self._relayout()

    def open_lib_settings(self):
        """打开媒体库设置弹窗（常驻实例，扫描线程随其存活）"""
        if self.setting_dialog is None:
            self.setting_dialog = MediaLibSettingDialog(self)
            self.setting_dialog.libs_changed.connect(self._reload_libs)
            self.setting_dialog.scan_done.connect(self.refresh)
        self.setting_dialog.show()
        self.setting_dialog.raise_()
        self.setting_dialog.activateWindow()

    def _reload_libs(self):
        """刷新媒体库下拉框，保持当前选择"""
        current = self.lib_choose.currentText()
        names = [ALL_LIBS] + [lib['name'] for lib in Config().read_media_libs()]
        self.lib_choose.blockSignals(True)
        self.lib_choose.clear()
        self.lib_choose.addItems(names)
        if current in names:
            self.lib_choose.setCurrentText(current)
        self.lib_choose.blockSignals(False)

    def refresh(self):
        lib = self.lib_choose.currentText()
        sql = '''SELECT "work_id", "work_name", "maker_name", "work_type", "age_category"
                 FROM "main"."works" WHERE "state" = '已品悦' '''
        if lib and lib != ALL_LIBS:
            sql += f''' AND "library" = '{lib.replace("'", "''")}' '''
        sql += ' ORDER BY "work_id" DESC'
        result = SQLiteDB().select(sql)
        if result is False:
            return
        for card in self.cards:
            card.deleteLater()
        self.cards = [WorkCard(*row, parent=self.cards_container) for row in result[1]]
        self._apply_filter()

    def _apply_filter(self):
        keyword = self.search_edit.text().strip().lower()
        shown = 0
        for card in self.cards:
            visible = (not keyword) or (keyword in card.search_text)
            card.setVisible(visible)
            if visible:
                shown += 1
        self._relayout()
        total = len(self.cards)
        if keyword:
            self.count_label.setText(f'共 {total} 个作品，匹配 {shown} 个')
        else:
            self.count_label.setText(f'共 {total} 个作品')

    def _column_count(self):
        width = self.cards_scroll.viewport().width()
        return max(1, (width - CARD_GAP) // (CARD_WIDTH + CARD_GAP))

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
