from scan_service.lib.vars import global_var
import pymysql

class DB:
    def __init__(self):
        self.conn = self.connect()
        self.db_info = global_var.global_config["db_info"]

    def connect(self):
        conn = pymysql.connect(host = self.db_info["host"],
                               port = int(self.db_info["port"]),
                               user = self.db_info["user"],
                               password = self.db_info["passwd"],
                               database = self.db_info["db_name"],
                               charset = "utf8"
                               )
        return conn

    def exec_sql(self, sql, fetch = "Many", num = 0):
        cursor = self.conn.cursor()
        cursor.execute(sql)
        if fetch == "Many":
            return cursor.fetchall()
        elif fetch == "One":
            return cursor.fetchone()
        else:
            return cursor.fetchmany(num)