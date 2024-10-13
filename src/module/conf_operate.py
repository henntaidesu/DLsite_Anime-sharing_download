import pymysql
import configparser


class Config:
    config = None

    def __init__(self):
        # 如果配置信息尚未加载，则加载配置文件
        if not Config.config:
            Config.config = self._load_config()

    def _load_config(self):
        self.config = configparser.ConfigParser()
        self.config.read('conf.ini', encoding='utf-8')
        return self.config

    def read_start_type(self):
        start_type = self.config.get('start_type', 'type')
        if start_type == 'GUI':
            return True
        else:
            return False

    def open_DB(self):
        open_DB = self.config.get('database', 'open_DB')
        if open_DB == 'True':
            return True
        else:
            return False

    def read_database(self):
        host = self.config.get('database', 'host')
        port = self.config.get('database', 'port')
        port = int(port)
        user = self.config.get('database', 'user')
        password = self.config.get('database', 'password')
        data_base = self.config.get('database', 'database')
        open_DB = self.config.get('database', 'open_DB')

        if open_DB == 'True':
            db = pymysql.connect(host=host, port=port, user=user, password=password, database=data_base)
            return db

    def read_file_down_path(self):
        folder_path = self.config.get('DownPath', 'DownPath')
        if '\\' in folder_path:
            folder_path = folder_path.replace('\\', '\\\\')
        return folder_path

    def read_proxy(self):
        if_true = self.config.get('Proxy', 'OpenProxy')
        host = self.config.get('Proxy', 'host')
        port = self.config.get('Proxy', 'port')
        proxy_url = f"http://{host}:{port}"

        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }

        # print(type(if_true))
        if if_true == "True":
            return True, proxies
        else:
            return False, proxies

    def read_setting_proxy(self):
        if_true = self.config.get('Proxy', 'OpenProxy')
        host = self.config.get('Proxy', 'host')
        port = self.config.get('Proxy', 'port')
        proxy_type = self.config.get('Proxy', 'type')
        return if_true, host, port, proxy_type

    def read_katfile_cookie(self):
        user = self.config.get('katfile', 'User')
        xfss = self.config.get('katfile', 'xfss')
        cookie = "login=" + user + ";" + "xfss=" + xfss
        return cookie

    def read_katfile_use(self):
        user = self.config.get('katfile', 'User')
        pass_wd = self.config.get('katfile', 'PassWD')
        xfss = self.config.get('katfile', 'xfss')
        return user, pass_wd, xfss

    def read_log_level(self):
        level = self.config.get('LogLevel', 'level')
        return level

    def read_processes(self):
        processes = self.config.get('processes', 'processes')
        return processes

    def read_sys_encoding(self):
        encoding = self.config.get('encoding', 'encoding')
        return encoding

    def read_max_RJ(self):
        max_RJ = int(self.config.get('max_RJ', 'max'))
        return max_RJ

    def read_download_list(self):
        auto_download = self.config.get('down_list', 'auto_download')
        if auto_download == 'True':
            auto_download = True
        else:
            auto_download = False
        download_processes = int(self.config.get('down_list', 'download_processes'))

        return auto_download, download_processes

    def write_katfile_xfss(self, XFSS_code):
        self.config.set('katfile', 'xfss', XFSS_code)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def write_download_path(self, down_path):
        self.config.set('DownPath', 'DownPath', down_path)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def write_proxy(self, address, port):
        self.config.set('Proxy', 'host', address)
        self.config.set('Proxy', 'Port', port)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def write_proxy_status(self, status):
        self.config.set('Proxy', 'OpenProxy', status)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def write_proxy_type(self, proxy_type):
        self.config.set('Proxy', 'type', proxy_type)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def write_katfile_user(self, user, passwd):
        self.config.set('katfile', 'user', user)
        self.config.set('katfile', 'passwd', passwd)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)


class WriteConf:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('conf.ini', encoding='utf-8')

    def katfile_xfss(self, XFSS_code):
        self.config.set('katfile', 'xfss', XFSS_code)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def download_path(self, down_path):
        self.config.set('DownPath', 'DownPath', down_path)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def proxy(self, address, port):
        self.config.set('Proxy', 'host', address)
        self.config.set('Proxy', 'Port', port)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def proxy_status(self, status):
        self.config.set('Proxy', 'OpenProxy', status)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
