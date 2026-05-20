import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'innovation.db')

def init_db():
    """Initializes the database from schema.sql and seeds it."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Read and execute schema
    schema_path = os.path.join(os.path.dirname(__file__), 'db', 'schema.sql')
    with open(schema_path, 'r') as f:
        cursor.executescript(f.read())
        
    # Read and execute seed data
    seed_path = os.path.join(os.path.dirname(__file__), 'db', 'seeds.sql')
    with open(seed_path, 'r') as f:
        cursor.executescript(f.read())
        
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
