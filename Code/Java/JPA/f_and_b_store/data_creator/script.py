import mysql.connector
import argparse
import random
import string

# === Configuration ===
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'nghia123456',
    'database': 'f_and_b_store'
}

# === Sample table list for demonstration (replace with your actual 11 tables) ===
TABLES = ['customers', 'orders', 'products']

# === Connect to DB ===
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

# === Generate Random Data Queries ===
def create_random_data():
    queries = []
    for _ in range(10):  # Create 10 random rows per table
        name = ''.join(random.choices(string.ascii_letters, k=8))
        queries.append(f"INSERT INTO customers (name) VALUES ('{name}');")

        product = ''.join(random.choices(string.ascii_letters, k=5))
        price = round(random.uniform(1.0, 100.0), 2)
        queries.append(f"INSERT INTO products (name, price) VALUES ('{product}', {price});")

        queries.append(f"INSERT INTO orders (customer_id, product_id) VALUES ({random.randint(1,5)}, {random.randint(1,5)});")

    return queries

# === Execute a list of queries ===
def run_queries(queries):
    conn = get_connection()
    cursor = conn.cursor()
    for query in queries:
        try:
            cursor.execute(query)
        except mysql.connector.Error as err:
            print(f"Error: {err}\nQuery: {query}")
    conn.commit()
    cursor.close()
    conn.close()

# === Run Query: Create Data ===
def run_query_create_data():
    queries = create_random_data_queries()
    run_queries(queries)
    print("Inserted random data.")

# === Run Query: Delete Data ===
def run_query_delete_data():
    conn = get_connection()
    cursor = conn.cursor()
    for table in TABLES:
        cursor.execute(f"DELETE FROM {table};")
    conn.commit()
    cursor.close()
    conn.close()
    print("Deleted all data from tables.")

# === Run All: Delete -> Create ===
def run_all():
    run_query_delete_data()
    run_query_create_data()

# === CLI ===
def main():
    parser = argparse.ArgumentParser(description="Manage f_and_b_store database")
    parser.add_argument("command", choices=["create_random_data_queries", "run_query_create_data", "run_query_delete_data", "run_all"])

    args = parser.parse_args()
    if args.command == "create_random_data":
        queries = create_random_data()
        print("\n".join(queries))
    elif args.command == "run_query_create_data":
        run_query_create_data()
    elif args.command == "run_query_delete_data":
        run_query_delete_data()
    elif args.command == "run_all":
        run_all()

if __name__ == "__main__":
    main()
