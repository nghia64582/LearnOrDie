import mysql.connector

# Database connection details
host = "localhost"       # Change to your MySQL server address if needed
user = "root"            # MySQL username
password = "nghia123456" # MySQL password
database = "auctions"     # Change to your actual database name

try:
    # Establish the connection
    conn = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    
    if conn.is_connected():
        print("✅ Connected to MySQL successfully!")

    # Create a cursor object
    cursor = conn.cursor()

    # Example query: Show databases
    cursor.execute("SHOW DATABASES")
    for db in cursor:
        print(db)

    # Close connection
    cursor.close()
    conn.close()

except mysql.connector.Error as e:
    print(f"❌ Error connecting to MySQL: {e}")
