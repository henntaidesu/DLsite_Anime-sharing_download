import os
import sys

QSS_PATH = os.path.join(os.path.dirname(__file__), 'dark_theme.qss')


def apply_dark_theme(app):
    """对 QApplication 应用全局暗色主题（Fusion 风格 + 暗色调色板 + QSS）"""
    from PyQt5.QtGui import QPalette, QColor

    app.setStyle('Fusion')

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor('#15171c'))
    palette.setColor(QPalette.WindowText, QColor('#e6e9ef'))
    palette.setColor(QPalette.Base, QColor('#1d2027'))
    palette.setColor(QPalette.AlternateBase, QColor('#1b1e25'))
    palette.setColor(QPalette.Text, QColor('#e6e9ef'))
    palette.setColor(QPalette.Button, QColor('#262b35'))
    palette.setColor(QPalette.ButtonText, QColor('#e6e9ef'))
    palette.setColor(QPalette.ToolTipBase, QColor('#1d2027'))
    palette.setColor(QPalette.ToolTipText, QColor('#e6e9ef'))
    palette.setColor(QPalette.Highlight, QColor('#4f7cff'))
    palette.setColor(QPalette.HighlightedText, QColor('#ffffff'))
    palette.setColor(QPalette.PlaceholderText, QColor('#6b7280'))
    palette.setColor(QPalette.Link, QColor('#6189ff'))
    app.setPalette(palette)

    try:
        with open(QSS_PATH, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    except OSError as e:
        print(f'加载暗色主题样式失败: {e}')


def enable_dark_title_bar(window):
    """Windows 下将窗口标题栏切换为深色，其他平台无操作"""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        hwnd = int(window.winId())
        value = ctypes.c_int(1)
        # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE（Win10 2004+），旧版本用 19
        for attr in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
            if result == 0:
                break
    except Exception:
        pass
