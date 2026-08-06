"""
PayDOD Core Engine - Part 1: Setup & Database
Production-ready backend core built for high performance and mobile execution.
"""

from flask import Flask, request, jsonify, render_template_string
import sqlite3

app = Flask(__name__)

def init_db():
    """Initialize SQLite database and seed test data."""
    conn = sqlite3.connect('paydod.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shipments (
            order_id TEXT PRIMARY KEY,
            customer_name TEXT,
            amount REAL,
            status TEXT DEFAULT 'Pending'
        )
    ''')
    # Seed initial test record matching brand flow
    cursor.execute("INSERT OR IGNORE INTO shipments VALUES ('1001', 'John Doe', 350.00, 'Pending')")
    conn.commit()
    conn.close()

# Initialize the database upon module load
init_db()
