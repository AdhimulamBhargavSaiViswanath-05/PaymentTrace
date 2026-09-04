"""
Database initialization and connection management for PaymentTrace.
"""

import aiosqlite
import json
from pathlib import Path
from typing import Optional

DATABASE_PATH = Path(__file__).parent.parent / "paymenttrace.db"


async def get_db_connection():
    """
    Get an async database connection.
    
    Returns:
        aiosqlite.Connection: Database connection
    """
    conn = await aiosqlite.connect(DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


async def initialize_database():
    """
    Initialize the database schema.
    Creates tables if they don't exist.
    """
    conn = await get_db_connection()
    
    try:
        # Orders table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                merchant_status TEXT
            )
        """)
        
        # Payment attempts table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_attempts (
                attempt_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                payment_id TEXT NOT NULL,
                method TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (order_id)
            )
        """)
        
        # Payment events table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_events (
                event_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                payment_id TEXT,
                event_type TEXT NOT NULL,
                status TEXT,
                timestamp TEXT NOT NULL,
                error_code TEXT,
                metadata_json TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (order_id)
            )
        """)
        
        await conn.commit()
        
    finally:
        await conn.close()


async def clear_database():
    """
    Clear all data from database tables.
    Useful for testing and fixture loading.
    """
    conn = await get_db_connection()
    
    try:
        await conn.execute("DELETE FROM payment_events")
        await conn.execute("DELETE FROM payment_attempts")
        await conn.execute("DELETE FROM orders")
        await conn.commit()
        
    finally:
        await conn.close()


async def insert_order(order_id: str, created_at: str, amount: int, 
                       currency: str, merchant_status: Optional[str] = None):
    """Insert an order record."""
    conn = await get_db_connection()
    
    try:
        await conn.execute(
            """
            INSERT INTO orders (order_id, created_at, amount, currency, merchant_status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (order_id, created_at, amount, currency, merchant_status)
        )
        await conn.commit()
        
    finally:
        await conn.close()


async def insert_payment_attempt(attempt_id: str, order_id: str, payment_id: str,
                                 method: str, attempt_number: int, status: str,
                                 created_at: str):
    """Insert a payment attempt record."""
    conn = await get_db_connection()
    
    try:
        await conn.execute(
            """
            INSERT INTO payment_attempts 
            (attempt_id, order_id, payment_id, method, attempt_number, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (attempt_id, order_id, payment_id, method, attempt_number, status, created_at)
        )
        await conn.commit()
        
    finally:
        await conn.close()


async def insert_payment_event(event_id: str, order_id: str, payment_id: Optional[str],
                               event_type: str, status: Optional[str], timestamp: str,
                               error_code: Optional[str] = None, 
                               metadata: Optional[dict] = None):
    """Insert a payment event record."""
    conn = await get_db_connection()
    
    metadata_json = json.dumps(metadata) if metadata else None
    
    try:
        await conn.execute(
            """
            INSERT INTO payment_events 
            (event_id, order_id, payment_id, event_type, status, timestamp, error_code, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, order_id, payment_id, event_type, status, timestamp, error_code, metadata_json)
        )
        await conn.commit()
        
    finally:
        await conn.close()
