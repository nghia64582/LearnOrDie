import csv
import mysql.connector

def get_data():
    global data
    lines = open("data.txt").readlines()
    data = []
    for line in lines:
        if line != "":
            eles = line.split('\t')
            if len(eles) < 4 or eles[3] == "":
                print(eles)
                continue
            try:
                month, day, name, score = eles
                day = int(day)
                month = int(month)
                score = int(score)
                if data == []:
                    year = 0
                else:
                    year = data[-1]["year"] + (1 if month == 1 and data[-1]["month"] == 12 else 0)
                data.append({
                    "month": month,
                    "day": day,
                    "name": name,
                    "score": score,
                    "year": year
                })
            except:
                pass

    delta_year = 2025 - data[-1]["year"]
    for i in range(len(data)):
        data[i]["year"] += delta_year

    print(data[:3])
    print(data[-3:])

def insert_data():
    # Connect to the MySQL database
    db = mysql.connector.connect(
        host="nghia64582.online",
        user="qrucoqmt_nghia64582",
        password="Nghi@131299",
        database="qrucoqmt_nghia64582"
    )
    # Insert data into the database one by one for easier debugging
    cursor = db.cursor()
    insert_query = (
        "INSERT INTO extraunary (created_at, name, score) VALUES (%s, %s, %s)"
    )
    for i in range(0, len(data), 50):
        batch = data[i:i + 50]
        values = [
            (f"{entry['year']}-{entry['month']:02d}-{entry['day']:02d}", entry['name'], entry['score'])
            for entry in batch
        ]
        try:
            cursor.executemany(insert_query, values)
            print(f"Successfully inserted {cursor.rowcount} rows.")
        except mysql.connector.Error as err:
            print("Error during batch insert:")
            print(f"Error message: {err}")
    db.commit()
    # Close the database connection
    cursor.close()
    db.close()

get_data()
insert_data()