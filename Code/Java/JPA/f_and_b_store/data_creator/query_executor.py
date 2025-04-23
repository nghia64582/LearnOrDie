import mysql.connector
import os

def execute_queries_from_file(database, user, password, host, file_path):
    try:
        # Connect to the database
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = connection.cursor()

        # Get the absolute path of the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct absolute path to the SQL file
        absolute_file_path = os.path.join(script_dir, file_path)

        # Read queries from the file
        with open(absolute_file_path, 'r') as file:
            queries = file.read()

        # Execute each query
        for query in queries.split(';'):
            query = query.strip()
            if query:
                cursor.execute(query)
                print(f"Executed: {query}")

        # Commit changes
        connection.commit()
        print("All queries executed successfully.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Database connection closed.")

if __name__ == "__main__":
    execute_queries_from_file(
        database="f_and_b_store",
        user="root",
        password="nghia123456",
        host="localhost",
        file_path="query/create_table.sql"
    )