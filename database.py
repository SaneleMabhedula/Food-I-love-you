import sqlite3
import json
from datetime import datetime
import pandas as pd

class RestaurantDB:
    def __init__(self):
        self.conn = sqlite3.connect('restaurant_orders.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Enhanced orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE,
                table_number INTEGER,
                customer_name TEXT,
                order_type TEXT DEFAULT 'dine_in',  -- 'dine_in' or 'takeaway'
                items TEXT,  -- JSON with individual item status
                total_amount REAL,
                status TEXT DEFAULT 'received',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                hour INTEGER,
                item_id TEXT,
                item_name TEXT,
                category TEXT,
                quantity INTEGER,
                revenue REAL,
                order_type TEXT
            )
        ''')
        
        self.conn.commit()
    
    def create_order(self, table_number, customer_name, items, total_amount, order_type='dine_in'):
        import uuid
        
        order_id = str(uuid.uuid4())[:8].upper()
        
        # Add individual item status
        enhanced_items = []
        for item in items:
            enhanced_items.append({
                **item,
                'item_status': 'pending',  # pending, preparing, ready, served
                'item_id': f"{item['id']}_{uuid.uuid4().hex[:4]}"
            })
        
        items_json = json.dumps(enhanced_items)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO orders (order_id, table_number, customer_name, items, total_amount, order_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_id, table_number, customer_name, items_json, total_amount, order_type))
        
        # Update analytics
        for item in enhanced_items:
            cursor.execute('''
                INSERT INTO analytics (date, hour, item_id, item_name, category, quantity, revenue, order_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().date(),
                datetime.now().hour,
                item['id'],
                item['name'],
                item.get('category', 'unknown'),
                item['quantity'],
                item['price'] * item['quantity'],
                order_type
            ))
        
        self.conn.commit()
        return order_id
    
    def get_orders(self, status=None):
        cursor = self.conn.cursor()
        if status:
            cursor.execute('''
                SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC
            ''', (status,))
        else:
            cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
        
        orders = []
        for row in cursor.fetchall():
            orders.append({
                'id': row[0],
                'order_id': row[1],
                'table_number': row[2],
                'customer_name': row[3],
                'order_type': row[4],
                'items': json.loads(row[5]),
                'total_amount': row[6],
                'status': row[7],
                'created_at': row[8],
                'status_updated_at': row[9]
            })
        return orders
    
    def update_order_status(self, order_id, new_status):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE orders 
            SET status = ?, status_updated_at = CURRENT_TIMESTAMP 
            WHERE order_id = ?
        ''', (new_status, order_id))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def update_item_status(self, order_id, item_id, new_status):
        """Update status of individual item"""
        cursor = self.conn.cursor()
        
        # Get current order
        cursor.execute('SELECT items FROM orders WHERE order_id = ?', (order_id,))
        result = cursor.fetchone()
        
        if result:
            items = json.loads(result[0])
            
            # Update specific item status
            for item in items:
                if item.get('item_id') == item_id:
                    item['item_status'] = new_status
                    break
            
            # Update order status based on item statuses
            all_items_status = [item['item_status'] for item in items]
            if all(status == 'ready' for status in all_items_status):
                new_order_status = 'ready'
            elif any(status == 'ready' for status in all_items_status):
                new_order_status = 'partially_ready'
            else:
                new_order_status = 'preparing'
            
            # Save updated items and order status
            cursor.execute('''
                UPDATE orders 
                SET items = ?, status = ?, status_updated_at = CURRENT_TIMESTAMP 
                WHERE order_id = ?
            ''', (json.dumps(items), new_order_status, order_id))
            
            self.conn.commit()
            return True
        
        return False
    
    def get_customer_order(self, order_id):
        """Get order for customer view"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                'id': result[0],
                'order_id': result[1],
                'table_number': result[2],
                'customer_name': result[3],
                'order_type': result[4],
                'items': json.loads(result[5]),
                'total_amount': result[6],
                'status': result[7],
                'created_at': result[8],
                'status_updated_at': result[9]
            }
        return None