import configparser
import json
import os


# 默认配置：首次运行（数据库中无对应配置项且无 conf.ini 可迁移）时写入 conf 表
DEFAULT_CONF = {
    'start_type': {'type': 'GUI'},
    'processes': {'processes': '5'},
    'downpath': {'downpath': ''},
    'debrid': {'api_key': ''},
    'proxy': {'openproxy': 'False', 'host': '127.0.0.1', 'port': '7890', 'type': 'http'},
    'loglevel': {'level': 'info'},
    'encoding': {'encoding': 'cp437'},
    'max_key': {'rj': '0', 'vj': '0'},
    'down_list': {'auto_download': 'False', 'auto_unzip': 'False', 'download_processes': '5', 'folder_name': 'rj'},
    'api': {'address': '127.0.0.1', 'port': '5000'},
    'media_lib': {'libs': '[]'},
}


class Config:
    """配置读写，数据保存在 SQLite 的 conf 表中（section / key / value）"""

    config = None  # 类级缓存：{section: {key: value}}，全部小写

    def __init__(self):
        if Config.config is None:
            Config.config = self._load_config()

    @staticmethod
    def _db():
        # 延迟导入，避免 conf_operate -> datebase_execution -> log -> conf_operate 循环导入
        from src.module.datebase_execution import SQLiteDB
        return SQLiteDB()

    @staticmethod
    def _esc(value):
        return str(value).replace("'", "''")

    @classmethod
    def _write_db(cls, db, section, key, value):
        db.insert(
            f'INSERT OR REPLACE INTO "conf" ("section", "key", "value") '
            f"VALUES ('{cls._esc(section.lower())}', '{cls._esc(key.lower())}', '{cls._esc(value)}')"
        )

    def _load_config(self):
        db = self._db()  # SQLiteDB 初始化时创建数据库与 conf 表

        # 旧版 conf.ini 存在时：迁移进数据库后删除
        if os.path.exists('conf.ini'):
            parser = configparser.ConfigParser()
            parser.read('conf.ini', encoding='utf-8')
            for section in parser.sections():
                for key, value in parser.items(section):
                    self._write_db(db, section, key, value)
            os.remove('conf.ini')

        # 补齐缺失的默认配置项
        for section, items in DEFAULT_CONF.items():
            for key, value in items.items():
                db.insert(
                    f'INSERT OR IGNORE INTO "conf" ("section", "key", "value") '
                    f"VALUES ('{section}', '{key}', '{self._esc(value)}')"
                )

        conf = {}
        result = db.select('SELECT "section", "key", "value" FROM "conf"')
        if result and result[0]:
            for section, key, value in result[1]:
                conf.setdefault(section, {})[key] = value
        return conf

    # ---------- 通用读写 ----------

    def read_value(self, section, key, fallback=None):
        return Config.config.get(section.lower(), {}).get(key.lower(), fallback)

    def write_value(self, section, key, value):
        self._write_db(self._db(), section, key, value)
        Config.config.setdefault(section.lower(), {})[key.lower()] = str(value)

    # ---------- 读取 ----------

    def read_start_type(self):
        return self.read_value('start_type', 'type') == 'GUI'

    def read_file_down_path(self):
        folder_path = self.read_value('DownPath', 'DownPath', '')
        if '\\' in folder_path:
            folder_path = folder_path.replace('\\', '\\\\')
        return folder_path

    def read_proxy(self):
        if_true = self.read_value('Proxy', 'OpenProxy')
        host = self.read_value('Proxy', 'host')
        port = self.read_value('Proxy', 'port')
        proxy_url = f"http://{host}:{port}"

        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        if if_true == "True":
            return True, proxies
        else:
            return False, proxies

    def read_setting_proxy(self):
        if_true = self.read_value('Proxy', 'OpenProxy')
        host = self.read_value('Proxy', 'host')
        port = self.read_value('Proxy', 'port')
        proxy_type = self.read_value('Proxy', 'type')
        return if_true, host, port, proxy_type

    def read_debrid_api_key(self):
        return self.read_value('debrid', 'api_key', '')

    def read_log_level(self):
        return self.read_value('LogLevel', 'level', 'info')

    def read_processes(self):
        return self.read_value('processes', 'processes')

    def read_sys_encoding(self):
        return self.read_value('encoding', 'encoding')

    def read_max_RJ(self):
        return int(self.read_value('max_key', 'RJ', '0'))

    def read_max_VJ(self):
        return int(self.read_value('max_key', 'VJ', '0'))

    def read_download_list(self):
        auto_download = self.read_value('down_list', 'auto_download') == 'True'
        download_processes = int(self.read_value('down_list', 'download_processes', '1'))
        return auto_download, download_processes

    def read_auto_unzip(self):
        return self.read_value('down_list', 'auto_unzip') == 'True'

    def read_folder_name(self):
        """下载文件夹命名方式：'rj'=按RJ号，'work_name'=按作品名称"""
        return self.read_value('down_list', 'folder_name', 'rj')

    def read_media_libs(self):
        """媒体库列表：[{'name': 名称, 'folders': [文件夹, ...]}, ...]"""
        try:
            libs = json.loads(self.read_value('media_lib', 'libs', '[]'))
        except (TypeError, ValueError):
            libs = []
        if not isinstance(libs, list):
            libs = []
        libs = [lib for lib in libs
                if isinstance(lib, dict) and lib.get('name') and isinstance(lib.get('folders'), list)]
        if not libs:
            # 旧版扁平文件夹列表迁移为一个默认媒体库
            try:
                folders = json.loads(self.read_value('media_lib', 'folders', '[]'))
            except (TypeError, ValueError):
                folders = []
            if isinstance(folders, list) and folders:
                libs = [{'name': '默认媒体库', 'folders': folders}]
                self.write_media_libs(libs)
        return libs

    def read_HOME_API(self):
        address = self.read_value('API', 'address', '127.0.0.1')
        port = self.read_value('API', 'port', '5000')
        return r"http://" + address + ":" + port

    # ---------- 写入 ----------

    def write_max_RJ(self, max_RJ):
        self.write_value('max_key', 'RJ', max_RJ)

    def write_debrid_api_key(self, api_key):
        self.write_value('debrid', 'api_key', api_key)

    def write_download_path(self, down_path):
        self.write_value('DownPath', 'DownPath', down_path)

    def write_proxy(self, address, port):
        self.write_value('Proxy', 'host', address)
        self.write_value('Proxy', 'port', port)

    def write_proxy_status(self, status):
        self.write_value('Proxy', 'OpenProxy', status)

    def write_proxy_type(self, proxy_type):
        self.write_value('Proxy', 'type', proxy_type)

    def write_media_libs(self, libs):
        self.write_value('media_lib', 'libs', json.dumps(libs, ensure_ascii=False))


class WriteConf:
    """兼容旧接口，转发到 Config"""

    def __init__(self):
        self.conf = Config()

    def download_path(self, down_path):
        self.conf.write_download_path(down_path)

    def proxy(self, address, port):
        self.conf.write_proxy(address, port)

    def proxy_status(self, status):
        self.conf.write_proxy_status(status)
