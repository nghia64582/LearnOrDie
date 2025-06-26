# app.py

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# --- MySQL Configuration (for PythonAnywhere) ---
# Replace with your actual PythonAnywhere MySQL credentials
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+mysqlconnector://"
    f"nghia64582:nghia123456@"  # Username:Password
    f"nghia64582.mysql.pythonanywhere-services.com/" # Hostname
    f"nghia64582$default"      # Database Name
)
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+mysqlconnector://"
    f"root:nghia123456@"  # Username:Password
    f"localhost/" # Hostname
    f"nghia-db"      # Database Name
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Model ---
class KeyValue(db.Model):
    __tablename__ = 'key_value_store' # Link to your existing table
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    value = db.Column(db.Text)

    def __repr__(self):
        return f"<KeyValue {self.key}: {self.value}>"

# --- API Endpoints ---

@app.route('/keyvalue/<string:key>', methods=['GET'])
def get_key_value(key):
    """Fetches data by key."""
    kv_pair = KeyValue.query.filter_by(key=key).first()
    if kv_pair:
        return jsonify({'key': kv_pair.key, 'value': kv_pair.value})
    return jsonify({'message': 'Key not found'}), 404

@app.route('/keyvalue', methods=['POST'])
def create_key_value():
    """Creates a new key-value pair."""
    data = request.get_json()
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({'message': 'Missing key or value in request body'}), 400

    key = data['key']
    value = data['value']
    print("Key : " + key)
    print("Value : " + value)

    existing_kv = KeyValue.query.filter_by(key=key).first()
    if existing_kv:
        return jsonify({'message': 'Key already exists'}), 409 # Conflict

    new_kv = KeyValue(key=key, value=value)
    db.session.add(new_kv)
    db.session.commit()
    return jsonify({'message': 'Key-value pair created', 'key': new_kv.key}), 201

@app.route('/keyvalue/<string:key>', methods=['PUT'])
def update_key_value(key):
    """Updates an existing key-value pair."""
    data = request.get_json()
    if not data or 'value' not in data:
        return jsonify({'message': 'Missing value in request body'}), 400

    kv_pair = KeyValue.query.filter_by(key=key).first()
    if not kv_pair:
        return jsonify({'message': 'Key not found'}), 404

    kv_pair.value = data['value']
    db.session.commit()
    return jsonify({'message': 'Key-value pair updated', 'key': kv_pair.key})

@app.route('/keyvalue/<string:key>', methods=['DELETE'])
def delete_key_value(key):
    """Deletes a key-value pair."""
    kv_pair = KeyValue.query.filter_by(key=key).first()
    if not kv_pair:
        return jsonify({'message': 'Key not found'}), 404

    db.session.delete(kv_pair)
    db.session.commit()
    return jsonify({'message': 'Key-value pair deleted', 'key': key})

# Optional: Initialize database (only run this ONCE if you want SQLAlchemy to create tables)
# On PythonAnywhere, it's often better to create tables manually as shown above.
# with app.app_context():
#     db.create_all()

if __name__ == '__main__':
    app.run(debug=True) # debug=True for local testing, set to False in production