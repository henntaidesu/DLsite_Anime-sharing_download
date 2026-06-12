from PyQt6.QtWidgets import (QMainWindow, QPushButton, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMenu)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi
from src.module.datebase_execution import SQLiteDB
from src.module.i18n import tr, notifier

# works.state（数据库原始值）-> 显示颜色
STATE_COLORS = {
    '已品悦': '#4ade80',
    '已下载': '#60a5fa',
    '下载中': '#facc15',
}


class DownloadedWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("src/QTui/ui_file/downloaded.ui", self)

        self.works_table = self.findChild(QTableWidget, 'works_table')
        self.refresh_button = self.findChild(QPushButton, 'refresh_button')
        self.count_label = self.findChild(QLabel, 'count_label')

        self.works_table.setColumnCount(6)
        self.works_table.setHorizontalHeaderLabels(
            [tr('RJ号'), tr('作品名称'), tr('社团'), tr('类型'), tr('状态'), tr('下载时间')])
        self.works_table.verticalHeader().setVisible(False)
        header = self.works_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, width in ((0, 110), (2, 150), (3, 70), (4, 80), (5, 160)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.works_table.setColumnWidth(col, width)

        self.refresh_button.clicked.connect(self.refresh)

        # 右键菜单：已下载的作品可标记为已品悦
        self.works_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.works_table.customContextMenuRequested.connect(self._show_context_menu)

        self.retranslate_ui()
        notifier.language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self):
        self.setWindowTitle(tr('已下载'))
        self.works_table.setHorizontalHeaderLabels(
            [tr('RJ号'), tr('作品名称'), tr('社团'), tr('类型'), tr('状态'), tr('下载时间')])
        self.refresh_button.setText(tr('刷新'))
        self.refresh()

    def _show_context_menu(self, pos):
        item = self.works_table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        work_id = self.works_table.item(row, 0).text()
        # 用 UserRole 中保存的数据库原始状态值比较，避免被翻译后的显示文本影响
        state = self.works_table.item(row, 4).data(Qt.ItemDataRole.UserRole)
        if state != '已下载':
            return
        menu = QMenu(self)
        mark_action = menu.addAction(tr('标记为已品悦'))
        if menu.exec(self.works_table.viewport().mapToGlobal(pos)) == mark_action:
            SQLiteDB().update(
                f'''UPDATE "main"."works" SET "state" = '已品悦' WHERE "work_id" = '{work_id}' ''')
            self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        sql = '''SELECT "work_id", "work_name", "maker_name", "work_type", "state", "down_time"
                 FROM "main"."works" ORDER BY "down_time" DESC, "work_id" DESC'''
        result = SQLiteDB().select(sql)
        if result is False:
            return
        rows = result[1]

        self.works_table.setSortingEnabled(False)
        self.works_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                text = '' if value is None else str(value)
                if c == 5:
                    text = text[:19]  # 下载时间不显示微秒
                if c == 4:
                    # 第 5 列是状态：显示译文，原始值存入 UserRole 供右键菜单/着色使用
                    item = QTableWidgetItem(tr(text))
                    item.setData(Qt.ItemDataRole.UserRole, text)
                    if text in STATE_COLORS:
                        item.setForeground(QColor(STATE_COLORS[text]))
                else:
                    item = QTableWidgetItem(text)
                self.works_table.setItem(r, c, item)
        self.works_table.setSortingEnabled(True)

        self.count_label.setText(tr('共 {n} 个作品').format(n=len(rows)))
