#!/usr/bin/env python3
"""
Migration script for v1.3 - Add new fields to ideas table
Run this script to add the new columns to an existing database.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'innovation.db')

def migrate():
    """Add new columns to ideas table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(ideas)")
    columns = [col[1] for col in cursor.fetchall()]
    
    migrations = []
    
    # Add target_completion_date if not exists
    if 'target_completion_date' not in columns:
        cursor.execute('ALTER TABLE ideas ADD COLUMN target_completion_date DATE')
        migrations.append('target_completion_date')
    
    # Add target_pi if not exists
    if 'target_pi' not in columns:
        cursor.execute('ALTER TABLE ideas ADD COLUMN target_pi TEXT')
        migrations.append('target_pi')
    
    # hours_saved already exists from v1.2
    if 'hours_saved' not in columns:
        cursor.execute('ALTER TABLE ideas ADD COLUMN hours_saved REAL')
        migrations.append('hours_saved')
    
    # savings_measurement already exists from v1.2
    if 'savings_measurement' not in columns:
        cursor.execute('ALTER TABLE ideas ADD COLUMN savings_measurement TEXT')
        migrations.append('savings_measurement')
    
    conn.commit()
    conn.close()
    
    if migrations:
        print(f'✅ Added columns: {", ".join(migrations)}')
    else:
        print('✅ All columns already exist. No migration needed.')

if __name__ == '__main__':
    migrate()
