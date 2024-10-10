import sys
from src.module.log import Log
from src.module.conf_operate import Config
from src.module.log import err1
import sqlite3


def TrimString(Str):
    # if '\n' in Str:
    #     Str = Str.replace('\n', ' ')
    # if ' ' in Str:
    #     Str = Str.replace(' ', '')
    # if '/' in Str:
    #     Str = Str.replace('/', ' ')
    if "'" in Str:
        Str = Str.replace("'", "\\'")
    if '"' in Str:
        Str = Str.replace('"', '\\"')
    return Str


class MySQLDB:
    print_log = Log()

    def __init__(self):
        read_db_conf = Config()
        self.db = read_db_conf.read_database()

    def insert(self, sql):
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            self.db.close()
            return True
        except Exception as e:
            if "index.PRIMARY" in str(e):
                self.print_log.write_log(f"重复数据 : {sql} ", "warning")
                return '重复数据'
            elif "timed out" in str(e):
                self.print_log.write_log("连接数据库超时", 'error')
                sys.exit()
            else:
                err1(e)
                self.print_log.write_log(sql, 'error')
                return False

    def update(self, sql):
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            cursor.close()
            return True
        except Exception as e:
            err1(e)
            if "timed out" in str(e):
                self.print_log.write_log("连接数据库超时", 'error')
            self.print_log.write_log(sql, 'error')
            return False
        finally:
            if hasattr(self, 'db') and self.db:
                self.db.close()

    def select(self, sql):
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            result = cursor.fetchall()
            cursor.close()
            return True, result
        except Exception as e:
            err1(e)
            if "timed out" in str(e):
                self.print_log.write_log("连接数据库超时", 'error')
            self.print_log.write_log(sql, 'error')
        finally:
            if hasattr(self, 'db') and self.db:
                self.db.close()

    def delete(self, sql):
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()  # 提交事务，保存删除操作
            cursor.close()
        except Exception as e:
            err1(e)
            if "timed out" in str(e):
                self.print_log.write_log("连接数据库超时", 'error')
            self.print_log.write_log(sql, 'error')
            self.db.rollback()  # 回滚事务，撤销删除操作
        finally:
            if hasattr(self, 'db') and self.db:
                self.db.close()


class SQLiteDB:
    def __init__(self):
        self.print_log = Log()
        self.db = None
        self.db_path = "db.db"
        self.connect_db()

    def connect_db(self):
        """连接SQLite数据库"""
        try:
            self.db = sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            self.print_log.write_log(f"数据库连接失败: {str(e)}", 'error')
            sys.exit()

    def execute_query(self, sql, query_type='select'):
        """
        执行SQL查询，根据类型返回不同的结果。
        query_type: select, insert, update, delete
        """
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)

            if query_type == 'select':
                result = cursor.fetchall()
                return True, result
            elif query_type in ['insert', 'update', 'delete']:
                self.db.commit()  # 对于修改操作，提交更改
                return True
        except sqlite3.Error as e:
            self.print_log.write_log(f"数据库操作失败: {str(e)}", 'error')
            self.print_log.write_log(sql, 'error')
            return False
        finally:
            if hasattr(cursor, 'close'):
                cursor.close()

    def insert(self, sql):
        return self.execute_query(sql, 'insert')

    def update(self, sql):
        return self.execute_query(sql, 'update')

    def select(self, sql):
        return self.execute_query(sql, 'select')

    def delete(self, sql):
        return self.execute_query(sql, 'delete')

    def close_connection(self):
        if hasattr(self, 'db') and self.db:
            self.db.close()
