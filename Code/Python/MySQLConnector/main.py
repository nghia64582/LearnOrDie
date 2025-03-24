import mysql.connector

# Database connection details
host = "mysql-host"       # Change to your MySQL server address if needed
user = "root"            # MySQL username
password = "nghia123456" # MySQL password
database = "auctions"     # Change to your actual database name
host_datas = [
    {
        "key": "host name",
        "value": "mysql-host"
    },
    {
        "key": "container name",
        "value": "mysql-container-1"
    },
    {
        "key": "localhost",
        "value": "localhost"
    }
]
for host_data in host_datas:
    try:
        # Establish the connection
        conn = mysql.connector.connect(
            host=host_data["value"],
            user=user,
            password=password,
            database=database
        )

        if conn.is_connected():
            print("✅ Connected to MySQL successfully by {}".format(host_data["key"]))

        # Create a cursor object
        cursor = conn.cursor()

        # Example query: Show databases
        cursor.execute("SHOW DATABASES")
        for db in cursor:
            s = db

        # Close connection
        cursor.close()
        conn.close()

    except mysql.connector.Error as e:
        print("Cannot connect to MySQL database by : {}".format(host_data["key"]))
        # print(f"❌ Error connecting to MySQL: {e}")
