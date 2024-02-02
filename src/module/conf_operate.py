import pymysql
import configparser


class ReadConf:
    config = None

    def __init__(self):
        # 如果配置信息尚未加载，则加载配置文件
        if not ReadConf.config:
            ReadConf.config = self._load_config()

    def _load_config(self):
        self.config = configparser.ConfigParser()
        self.config.read('conf.ini', encoding='utf-8')
        return self.config

    def database(self):
        host = self.config.get('database', 'host')
        port = self.config.get('database', 'port')
        port = int(port)
        user = self.config.get('database', 'user')
        password = self.config.get('database', 'password')
        data_base = self.config.get('database', 'database')
        db = pymysql.connect(host=host, port=port, user=user, password=password, database=data_base)
        return db

    def file_down_path(self):
        folder_path = self.config.get('DownPath', 'DownPath')
        if '\\' in folder_path:
            folder_path = folder_path.replace('\\', '\\\\')
        return folder_path

    def proxy(self):
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

    def katfile_cookie(self):
        user = self.config.get('katfile', 'User')
        xfss = self.config.get('katfile', 'xfss')
        cookie = "login=" + user + ";" + "xfss=" + xfss
        return cookie

    def katfile_use(self):
        user = self.config.get('katfile', 'User')
        pass_wd = self.config.get('katfile', 'PassWD')
        return user, pass_wd

    def log_level(self):
        level = self.config.get('LogLevel', 'level')
        return level

    def processes(self):
        processes = self.config.get('processes', 'processes')
        return processes

    def sys_encoding(self):
        encoding = self.config.get('encoding', 'encoding')
        return encoding

class WriteConf:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('conf.ini', encoding='utf-8')

    def katfile_xfss(self, XFSS_code):
        self.config.set('katfile', 'xfss', XFSS_code)
        with open('conf.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
