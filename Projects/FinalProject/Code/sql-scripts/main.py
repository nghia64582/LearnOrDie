import mysql.connector

config = {
    'user': 'root',
    'password': 'nghia123456',
    'host': 'localhost',
    'database': 'test',
}

db_connection = mysql.connector.connect(**config)
db_cursor = db_connection.cursor()
