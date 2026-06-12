import os
from PyQt5.QtWidgets import (QDialog, QPushButton, QLabel, QFrame, QScrollArea, QWidget,
                             QFileDialog, QInputDialog, QMessageBox, QHBoxLayout, QVBoxLayout)
from PyQt5.QtCore import QStandardPaths, QThread, pyqtSignal
from src.module.conf_operate import Config
from src.module.datebase_execution import SQLiteDB
from src.module.i18n import tr, notifier
from src.QTui.style.theme import enable_dark_title_bar


class MediaLibScanner(QThread):
    """后台扫描媒体库：导入全部文件夹的 RJ 号并调用 DL API 补全数据。
    已扫描过元数据的作品跳过，新发现的作品正常补全；force 为 True 时强制全部重新获取。"""
    progress = pyqtSignal(str)
    done = pyqtSignal(str)

    def __init__(self, lib_name, folders, force=False, parent=None):
        super().__init__(parent)
        self.lib_name = lib_name
        self.folders = folders
        self.force = force

    def run(self):
        from src.module.import_local_works import (import_media_lib, backfill_works_from_api,
                                                   backfill_work_pages)
        added = total = 0
        for folder in self.folders:
            folder_added, folder_total = import_media_lib(folder, self.lib_name)
            added += folder_added
            total += folder_total
        self.progress.emit(tr('已导入 {total} 个作品（新增 {added}），正在从 DL API 补全数据…').format(
            total=total, added=added))
        filled, _, _ = backfill_works_from_api(delay=0.5, progress=self._on_backfill,
                                               library=self.lib_name, force=self.force)
        self.progress.emit(tr('正在抓取 DLsite 作品页元数据与图片…'))
        page_filled, page_missed, _ = backfill_work_pages(delay=1.0, progress=self._on_page,
                                                          library=self.lib_name, force=self.force)
        self.done.emit(tr('扫描完成：导入 {total} 个，API 补全 {filled} 个，作品页补全 {page_filled} 个（失败 {page_missed}）').format(
            total=total, filled=filled, page_filled=page_filled, page_missed=page_missed))

    def _on_backfill(self, i, total, rj, ok):
        if i % 10 == 0 or i == total:
            self.progress.emit(tr('DL API 数据补全中… {i}/{total}').format(i=i, total=total))

    def _on_page(self, i, total, rj, ok):
        self.progress.emit(tr('作品页抓取中… {i}/{total}（{rj}）').format(i=i, total=total, rj=rj))


class MediaLibSettingDialog(QDialog):
    """媒体库设置弹窗：新建/删除媒体库、管理文件夹、触发扫描"""

    libs_changed = pyqtSignal()  # 媒体库增删 / 文件夹增删
    scan_done = pyqtSignal()     # 一次扫描结束（作品数据有更新）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('媒体库设置'))
        self.resize(680, 480)
        enable_dark_title_bar(self)

        self.conf = Config()
        self.media_libs = []  # [{'name': 名称, 'folders': [文件夹]}]
        self.media_lib_scanner = None
        self.media_lib_pending = []  # 扫描队列：[(库名, 是否强制)]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        self.media_lib_status = QLabel('')
        self.media_lib_status.setProperty('class', 'caption')
        header.addWidget(self.media_lib_status)
        header.addStretch()
        self.create_button = QPushButton(tr('新建媒体库'))
        self.create_button.setMinimumSize(108, 28)
        self.create_button.clicked.connect(self.create_media_lib)
        header.addWidget(self.create_button)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.media_lib_cards_layout = QVBoxLayout(container)
        self.media_lib_cards_layout.setContentsMargins(0, 0, 6, 0)
        self.media_lib_cards_layout.setSpacing(8)
        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.media_libs = self.conf.read_media_libs()
        self._rebuild_media_lib_cards()
        notifier.language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self):
        self.setWindowTitle(tr('媒体库设置'))
        self.create_button.setText(tr('新建媒体库'))
        self._rebuild_media_lib_cards()

    @staticmethod
    def default_down_path():
        """用户的“下载”文件夹"""
        return os.path.normpath(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation))

    def _find_media_lib(self, name):
        for lib in self.media_libs:
            if lib['name'] == name:
                return lib
        return None

    def _save_media_libs(self):
        self.conf.write_media_libs(self.media_libs)
        self._rebuild_media_lib_cards()
        self.libs_changed.emit()

    def _rebuild_media_lib_cards(self):
        """按当前媒体库列表重建卡片"""
        while self.media_lib_cards_layout.count():
            item = self.media_lib_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.media_libs:
            tip = QLabel(tr('还没有媒体库，点击"新建媒体库"创建。'))
            tip.setProperty('class', 'caption')
            self.media_lib_cards_layout.addWidget(tip)
        else:
            for lib in self.media_libs:
                self.media_lib_cards_layout.addWidget(self._build_media_lib_card(lib))
        self.media_lib_cards_layout.addStretch()

    def _build_media_lib_card(self, lib):
        card = QFrame()
        card.setProperty('class', 'card')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        name_label = QLabel(lib['name'])
        name_label.setStyleSheet('font-weight: 600; font-size: 14px;')
        header.addWidget(name_label)
        count_label = QLabel(tr('{n} 个文件夹').format(n=len(lib['folders'])))
        count_label.setProperty('class', 'caption')
        header.addWidget(count_label)
        header.addStretch()
        add_button = QPushButton(tr('添加文件夹'))
        add_button.clicked.connect(lambda _, n=lib['name']: self.add_media_lib_folder(n))
        header.addWidget(add_button)
        scan_button = QPushButton(tr('扫描元数据'))
        scan_button.clicked.connect(lambda _, n=lib['name']: self.scan_media_lib(n))
        header.addWidget(scan_button)
        rescan_button = QPushButton(tr('重新扫描元数据'))
        rescan_button.clicked.connect(lambda _, n=lib['name']: self.scan_media_lib(n, force=True))
        header.addWidget(rescan_button)
        delete_button = QPushButton(tr('删除'))
        delete_button.clicked.connect(lambda _, n=lib['name']: self.delete_media_lib(n))
        header.addWidget(delete_button)
        layout.addLayout(header)

        for folder in lib['folders']:
            row = QHBoxLayout()
            row.setSpacing(8)
            path_label = QLabel(folder)
            path_label.setProperty('class', 'caption')
            row.addWidget(path_label)
            row.addStretch()
            remove_button = QPushButton(tr('移除'))
            remove_button.setFixedSize(52, 24)
            remove_button.clicked.connect(
                lambda _, n=lib['name'], f=folder: self.remove_media_lib_folder(n, f))
            row.addWidget(remove_button)
            layout.addLayout(row)
        return card

    def create_media_lib(self):
        name, ok = QInputDialog.getText(self, tr('新建媒体库'), tr('媒体库名称：'))
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        if self._find_media_lib(name):
            QMessageBox.information(self, tr('媒体库'), tr('已存在同名媒体库。'))
            return
        self.media_libs.append({'name': name, 'folders': []})
        self._save_media_libs()

    def add_media_lib_folder(self, lib_name):
        lib = self._find_media_lib(lib_name)
        if lib is None:
            return
        path = QFileDialog.getExistingDirectory(self, tr('选择媒体库文件夹'), self.default_down_path())
        if not path:
            return
        path = os.path.normpath(path)
        for other in self.media_libs:
            if path in other['folders']:
                QMessageBox.information(self, tr('媒体库'),
                                       tr('该文件夹已在媒体库"{name}"中。').format(name=other["name"]))
                return
        # 只登记文件夹，扫描由"扫描元数据"按钮触发
        lib['folders'].append(path)
        self._save_media_libs()

    def remove_media_lib_folder(self, lib_name, folder):
        lib = self._find_media_lib(lib_name)
        if lib is None or folder not in lib['folders']:
            return
        lib['folders'].remove(folder)
        self._save_media_libs()

    def delete_media_lib(self, lib_name):
        lib = self._find_media_lib(lib_name)
        if lib is None:
            return
        answer = QMessageBox.question(
            self, tr('删除媒体库'),
            tr('确定删除媒体库"{name}"吗？\n不会删除本地文件，已导入的作品记录保留。').format(name=lib_name))
        if answer != QMessageBox.Yes:
            return
        self.media_libs.remove(lib)
        self.media_lib_pending = [p for p in self.media_lib_pending if p[0] != lib_name]
        self._save_media_libs()
        name_esc = lib_name.replace("'", "''")
        SQLiteDB().update(
            f'''UPDATE "main"."works" SET "library" = NULL WHERE "library" = '{name_esc}' ''')

    def scan_media_lib(self, lib_name, force=False):
        """扫描媒体库下的全部文件夹；force 为 True 时强制重新获取全部元数据"""
        lib = self._find_media_lib(lib_name)
        if lib is None or not lib['folders']:
            return
        if self.media_lib_scanner is not None and self.media_lib_scanner.isRunning():
            if (lib_name, force) not in self.media_lib_pending:
                self.media_lib_pending.append((lib_name, force))
        else:
            self._start_media_lib_scan(lib_name, force)

    def _start_media_lib_scan(self, lib_name, force):
        """后台扫描媒体库：导入 RJ 号并调用 DL API 补全（文件夹列表在启动时快照）"""
        lib = self._find_media_lib(lib_name)
        if lib is None or not lib['folders']:
            # 排队期间库被删除/清空，跳到下一个
            if self.media_lib_pending:
                self._start_media_lib_scan(*self.media_lib_pending.pop(0))
            return
        self.media_lib_status.setText(tr('正在扫描媒体库"{name}"…').format(name=lib_name))
        self.media_lib_scanner = MediaLibScanner(lib_name, list(lib['folders']), force, self)
        self.media_lib_scanner.progress.connect(self.media_lib_status.setText)
        self.media_lib_scanner.done.connect(self._on_media_lib_scan_done)
        self.media_lib_scanner.start()

    def _on_media_lib_scan_done(self, msg):
        """当前扫描结束：队列里还有待扫描的文件夹则继续"""
        self.media_lib_status.setText(msg)
        self.scan_done.emit()
        if self.media_lib_pending:
            self._start_media_lib_scan(*self.media_lib_pending.pop(0))
