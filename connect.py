from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
app = Flask(__name__, template_folder='flask/', static_folder='flask/')
CORS(app)
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",      
        user="root",             
        password="Satheesh@11",  
        database="IIP"         
    )
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    print(f"Received email: {email}, password: {password}, role: {role}")
    if not email or not password or not role:
        return jsonify({'status': 'error', 'message': 'Please provide email, password, and role'}), 400
    db = get_db_connection()
    cursor = db.cursor()
    query = """
        SELECT email, password, role
        FROM users
        WHERE email = %s AND password= %s
    """
    cursor.execute(query, (email, password))
    result = cursor.fetchone()

    if result:
        if result[2] == role:
            return jsonify({'status': 'success', 'role': role}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Incorrect role selected'}), 401
    else:
        return jsonify({'status': 'error', 'message': 'Invalid email or password'}), 401
    cursor.close()
    db.close()
if __name__ == '__main__':
    app.run(debug=True, port=5500)