import sys
from src.module.log import Log
import sqlite3


class SQLiteDB:
    def __init__(self):
        self.print_log = Log()
        self.db = None
        self.db_path = "DASD.db"
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
