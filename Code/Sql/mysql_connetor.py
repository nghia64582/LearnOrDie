import mysql.connector
from mysql.connector import Error

class MysqlConnector:
    def __init__(self, host, database, user, password):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    def connect(self):
        """Thiết lập kết nối tới MySQL database."""
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connection = mysql.connector.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password
                )
                print(f"--- Kết nối thành công tới database: {self.database} ---")
        except Error as e:
            print(f"Lỗi khi kết nối MySQL: {e}, code: {e.errno}")
            self.connection = None

    def disconnect(self):
        """Đóng kết nối database."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("--- Đã đóng kết nối database ---")

    def execute_query(self, query, params=None):
        """Thực thi các câu lệnh thay đổi dữ liệu (INSERT, UPDATE, DELETE)."""
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            self.connection.commit()
            print("Thực thi truy vấn thành công.")
            return cursor.rowcount
        except Error as e:
            print(f"Lỗi thực thi query: {e}")
            self.connection.rollback()
            return None
        finally:
            cursor.close()

    def fetch_data(self, query, params=None):
        """Thực thi câu lệnh SELECT và trả về kết quả."""
        self.connect()
        cursor = self.connection.cursor(dictionary=True) # Trả về dạng dict cho dễ dùng
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Error as e:
            print(f"Lỗi lấy dữ liệu: {e}")
            return None
        finally:
            cursor.close()
