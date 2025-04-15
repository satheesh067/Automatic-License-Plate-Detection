import mysql.connector

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",       # or your MySQL host
    user="root",   # your MySQL username
    password="Satheesh@11",  # your MySQL password
    database="IIP"  # your DB name
)

cursor = db.cursor()

# Query the plate info from the database
plate_1_text = "MH 20 EE 7598"  # Example detected plate

query = "SELECT * FROM vehicle_registry WHERE plate_number LIKE %s"
query_param = "%" + plate_1_text + "%"  # Adding the wildcards for LIKE

# Debug: Print the query and parameter to ensure correctness
print("Executing Query:", query)
print("With parameter:", query_param)

cursor.execute(query, (query_param,))
result = cursor.fetchone()

if result:
    print("Result found:", result)
else:
    print("No matching vehicle found.")

cursor.close()
db.close()
