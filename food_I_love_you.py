import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import hashlib
import time
import random
import qrcode
from io import BytesIO
import base64
import pytz
import os

# Set South African timezone
SA_TIMEZONE = pytz.timezone('Africa/Johannesburg')

def get_sa_time():
    """Get current South African time"""
    return datetime.now(SA_TIMEZONE)

# Enhanced Database Class with proper error handling
class RestaurantDB:
    def __init__(self, db_name="restaurant.db"):
        self.db_name = db_name
        try:
            self.conn = sqlite3.connect(db_name, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # This enables column access by name
            self.create_tables()
            self.migrate_database()  # Add migration function
        except Exception as e:
            st.error(f"❌ Database connection failed: {e}")
            raise e
    
    def migrate_database(self):
        """Migrate existing database to new schema if needed"""
        cursor = self.conn.cursor()
        try:
            # Check if payment_method column exists
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'payment_method' not in columns:
                st.info("🔄 Updating database schema...")
                # Add the missing column
                cursor.execute('ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT "cash"')
                self.conn.commit()
                st.success("✅ Database schema updated successfully!")
                
        except Exception as e:
            st.error(f"❌ Database migration error: {e}")
            # If migration fails, recreate the database
            st.warning("🔄 Recreating database with new schema...")
            self.conn.close()
            if os.path.exists(self.db_name):
                os.remove(self.db_name)
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Users table (staff only)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Menu items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                category TEXT NOT NULL,
                available BOOLEAN DEFAULT TRUE,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Orders table - FIXED: Added payment_method column
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_number INTEGER,
                customer_name TEXT NOT NULL,
                order_type TEXT DEFAULT 'dine-in',
                status TEXT DEFAULT 'pending',
                total_amount REAL DEFAULT 0,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                estimated_wait_time INTEGER DEFAULT 15,
                order_token TEXT UNIQUE,
                payment_method TEXT DEFAULT 'cash'  -- ADDED THIS COLUMN
            )
        ''')
        
        # Order items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                menu_item_id INTEGER,
                menu_item_name TEXT,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                special_instructions TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
                FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
            )
        ''')
        
        # Order status history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()
        self.insert_default_data()
    
    def insert_default_data(self):
        cursor = self.conn.cursor()
        
        # Insert default admin user
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password, role) 
                VALUES (?, ?, ?)
            ''', ('admin', hashlib.sha256('admin123'.encode()).hexdigest(), 'admin'))
        except sqlite3.IntegrityError:
            pass
        
        # Insert sample staff
        staff_users = [
            ('chef', 'chef123', 'chef'),
            ('manager', 'manager123', 'manager'),
            ('staff', 'staff123', 'staff')
        ]
        
        for username, password, role in staff_users:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (username, password, role) 
                    VALUES (?, ?, ?)
                ''', (username, hashlib.sha256(password.encode()).hexdigest(), role))
            except sqlite3.IntegrityError:
                pass
        
        # Check if menu items already exist
        cursor.execute('SELECT COUNT(*) FROM menu_items')
        if cursor.fetchone()[0] == 0:
            # Premium menu with high-quality food images
            menu_items = [
                # BEVERAGES
                ('Cappuccino', 'Freshly brewed coffee with steamed milk foam', 45, 'Beverage', 
                 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=500&h=300&fit=crop'),
                ('Mango Smoothie', 'Fresh mango blended with yogurt and honey', 55, 'Beverage', 
                 'https://images.unsplash.com/photo-1628991839433-31cc35f5c36a?w=500&h=300&fit=crop'),
                ('Sparkling Lemonade', 'House-made lemonade with mint and berries', 42, 'Beverage', 
                 'https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=500&h=300&fit=crop'),
                
                # APPETIZERS
                ('Truffle Arancini', 'Crispy risotto balls with truffle aioli', 89, 'Starter', 
                 'https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=500&h=300&fit=crop'),
                ('Burrata Caprese', 'Fresh burrata with heirloom tomatoes and basil', 125, 'Starter', 
                 'https://images.unsplash.com/photo-1592417817098-8fd3d9eb14a5?w=500&h=300&fit=crop'),
                ('Crispy Calamari', 'Lightly fried squid with lemon garlic aioli', 95, 'Starter', 
                 'https://images.unsplash.com/photo-1553621042-f6e147245754?w=500&h=300&fit=crop'),
                
                # MAIN COURSES
                ('Wagyu Beef Burger', 'Premium wagyu patty with truffle cheese', 185, 'Main Course', 
                 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500&h=300&fit=crop'),
                ('Lobster Pasta', 'Fresh lobster with handmade tagliatelle', 245, 'Main Course', 
                 'https://images.unsplash.com/photo-1621996346565-e3dbc353d2e5?w=500&h=300&fit=crop'),
                ('Herb-Crusted Salmon', 'Atlantic salmon with lemon butter sauce', 195, 'Main Course', 
                 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=500&h=300&fit=crop'),
                ('Truffle Mushroom Risotto', 'Arborio rice with wild mushrooms', 165, 'Main Course', 
                 'https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=500&h=300&fit=crop'),
                
                # DESSERTS
                ('Chocolate Lava Cake', 'Warm chocolate cake with melting center', 85, 'Dessert', 
                 'https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=500&h=300&fit=crop'),
                ('Berry Panna Cotta', 'Vanilla panna cotta with mixed berry compote', 75, 'Dessert', 
                 'https://images.unsplash.com/photo-1551024506-0bccd828d307?w=500&h=300&fit=crop'),
                ('Tiramisu', 'Classic Italian dessert with espresso', 79, 'Dessert', 
                 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=500&h=300&fit=crop')
            ]
            
            for item in menu_items:
                cursor.execute('''
                    INSERT INTO menu_items (name, description, price, category, image_url)
                    VALUES (?, ?, ?, ?, ?)
                ''', item)
        
        self.conn.commit()

    def add_order(self, customer_name, order_type, items, table_number=None, notes="", payment_method="cash"):
        """FIXED: Complete rewrite with proper transaction handling"""
        cursor = self.conn.cursor()
        
        try:
            # Calculate total amount
            total_amount = sum(item['price'] * item['quantity'] for item in items)
            
            # Generate unique order token
            order_token = f"ORD{random.randint(1000, 9999)}{int(time.time()) % 10000}"
            current_time = get_sa_time().strftime('%Y-%m-%d %H:%M:%S')
            
            # Start transaction
            self.conn.execute("BEGIN TRANSACTION")
            
            # Insert order
            cursor.execute('''
                INSERT INTO orders (
                    customer_name, order_type, table_number, total_amount, 
                    notes, order_token, order_date, payment_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (customer_name, order_type, table_number, total_amount, 
                  notes, order_token, current_time, payment_method))
            
            order_id = cursor.lastrowid
            
            # Insert order items
            for item in items:
                cursor.execute('''
                    INSERT INTO order_items (
                        order_id, menu_item_id, menu_item_name, quantity, 
                        price, special_instructions
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (order_id, item['id'], item['name'], item['quantity'], 
                      item['price'], item.get('instructions', '')))
            
            # Add initial status to history
            cursor.execute('''
                INSERT INTO order_status_history (order_id, status, notes)
                VALUES (?, ?, ?)
            ''', (order_id, 'pending', 'Order placed by customer'))
            
            # Commit transaction
            self.conn.commit()
            
            # Verify the order was created
            cursor.execute('SELECT id, order_token, status FROM orders WHERE id = ?', (order_id,))
            order_verify = cursor.fetchone()
            
            if order_verify:
                return order_id, order_token
            else:
                raise Exception("Order verification failed after commit")
            
        except Exception as e:
            self.conn.rollback()
            st.error(f"❌ Database error in add_order: {str(e)}")
            raise e

    def get_order_by_token(self, order_token):
        """FIXED: Simple and reliable order retrieval"""
        cursor = self.conn.cursor()
        
        try:
            # Get basic order info
            cursor.execute('''
                SELECT * FROM orders WHERE order_token = ?
            ''', (order_token,))
            order = cursor.fetchone()
            
            if not order:
                return None
            
            # Get order items
            cursor.execute('''
                SELECT menu_item_name, quantity, special_instructions, price
                FROM order_items 
                WHERE order_id = ?
            ''', (order['id'],))
            items = cursor.fetchall()
            
            # Format items string
            items_list = []
            for item in items:
                item_str = f"{item['menu_item_name']} (x{item['quantity']}) - R{item['price'] * item['quantity']}"
                if item['special_instructions']:
                    item_str += f" - {item['special_instructions']}"
                items_list.append(item_str)
            
            items_str = ", ".join(items_list)
            
            # Convert to tuple for compatibility
            order_tuple = (
                order['id'], order['table_number'], order['customer_name'],
                order['order_type'], order['status'], order['total_amount'],
                order['order_date'], order['notes'], order['estimated_wait_time'],
                order['order_token'], order['payment_method'], items_str, len(items)
            )
            
            return order_tuple
            
        except Exception as e:
            st.error(f"❌ Error in get_order_by_token: {str(e)}")
            return None

    def get_order_status(self, order_token):
        """Simple status retrieval"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT status FROM orders WHERE order_token = ?', (order_token,))
            result = cursor.fetchone()
            return result['status'] if result else None
        except Exception as e:
            st.error(f"❌ Error getting order status: {str(e)}")
            return None

    def update_order_status(self, order_id, new_status, notes=""):
        cursor = self.conn.cursor()
        try:
            cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
            cursor.execute('''
                INSERT INTO order_status_history (order_id, status, notes)
                VALUES (?, ?, ?)
            ''', (order_id, new_status, notes))
            self.conn.commit()
            return True
        except Exception as e:
            st.error(f"❌ Error updating order status: {str(e)}")
            return False

    def get_active_orders(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT o.*, 
                       GROUP_CONCAT(oi.menu_item_name || ' (x' || oi.quantity || ')', ', ') as items,
                       COUNT(oi.id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.status NOT IN ('completed', 'collected')
                GROUP BY o.id 
                ORDER BY o.order_date DESC
            ''')
            return cursor.fetchall()
        except Exception as e:
            st.error(f"❌ Error getting active orders: {str(e)}")
            return []

    def get_menu_items(self, category=None):
        cursor = self.conn.cursor()
        try:
            if category and category != 'All':
                query = 'SELECT * FROM menu_items WHERE available = 1 AND category = ? ORDER BY category, name'
                cursor.execute(query, (category,))
            else:
                query = 'SELECT * FROM menu_items WHERE available = 1 ORDER BY category, name'
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            st.error(f"❌ Error getting menu items: {str(e)}")
            return []

    def get_all_orders_for_debug(self):
        """Debug function to see all orders"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT id, order_token, customer_name, status, order_date 
                FROM orders 
                ORDER BY id DESC 
                LIMIT 10
            ''')
            return cursor.fetchall()
        except Exception as e:
            return []

# Initialize database
def initialize_database():
    try:
        # Don't remove existing database to preserve orders
        db = RestaurantDB()
        return db
    except Exception as e:
        st.error(f"❌ Database initialization error: {e}")
        return None

# Global database instance
db = initialize_database()

# QR Code Generator
def generate_qr_code(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Authentication System
def staff_login():
    st.sidebar.title("🔐 Staff Portal")
    username = st.sidebar.text_input("👤 Username")
    password = st.sidebar.text_input("🔒 Password", type="password")
    
    if st.sidebar.button("🚀 Login", use_container_width=True):
        if username and password:
            if db is None:
                st.sidebar.error("❌ Database not available")
                return
                
            cursor = db.conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_password))
            user = cursor.fetchone()
            
            if user:
                st.session_state.user = user
                st.session_state.logged_in = True
                st.session_state.role = user['role']
                st.sidebar.success(f"🎉 Welcome back, {user['username']}!")
                time.sleep(1)
                st.rerun()
            else:
                st.sidebar.error("❌ Invalid credentials")

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Initialize session state
def init_session_state():
    defaults = {
        'logged_in': False,
        'user': None,
        'current_step': "order_type",
        'order_type': "dine-in",
        'customer_name': "",
        'table_number': 1,
        'order_notes': "",
        'payment_method': "cash",
        'cart': [],
        'order_placed': False,
        'order_id': None,
        'order_token': None,
        'current_order_status': None,
        'last_order_check': time.time(),
        'page': 'landing'
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Enhanced CSS with beautiful styling
def load_css():
    st.markdown("""
    <style>
    /* Main Styles */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .hero-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 4rem 2rem;
        border-radius: 25px;
        color: white;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
        position: relative;
        overflow: hidden;
    }
    
    .hero-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1200&h=400&fit=crop') center/cover;
        opacity: 0.2;
        z-index: -1;
    }
    
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        text-align: center;
        margin: 1rem;
        border-left: 5px solid #667eea;
        transition: all 0.3s ease;
        height: 100%;
    }
    
    .feature-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.15);
    }
    
    .menu-item-card {
        background: white;
        border: none;
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }
    
    .menu-item-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    }
    
    .order-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        border-left: 5px solid;
    }
    
    .status-pending { border-left-color: #FF6B35; background: linear-gradient(135deg, #FFF3E0, #FFE0B2); }
    .status-preparing { border-left-color: #2E86AB; background: linear-gradient(135deg, #E3F2FD, #BBDEFB); }
    .status-ready { border-left-color: #28A745; background: linear-gradient(135deg, #E8F5E8, #C8E6C9); }
    
    .tracking-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .confirmation-box {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 2.5rem;
        border-radius: 20px;
        border-left: 5px solid #28a745;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        text-align: center;
        border-left: 5px solid #667eea;
    }
    
    .btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        border-radius: 25px;
        padding: 12px 30px;
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    .food-image {
        border-radius: 15px;
        object-fit: cover;
        width: 100%;
        height: 200px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    .restaurant-image {
        border-radius: 20px;
        object-fit: cover;
        width: 100%;
        height: 250px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
    }
    
    .step-indicator {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 1rem;
    }
    
    .progress-container {
        background: #f8f9fa;
        border-radius: 25px;
        padding: 3px;
        margin: 1rem 0;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    /* Animation for success messages */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-in-out;
    }
    </style>
    """, unsafe_allow_html=True)

# Enhanced Customer Ordering Interface
def customer_ordering():
    if db is None:
        st.error("❌ Database not available. Please restart the application.")
        return
        
    load_css()
    
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 3.5rem; margin-bottom: 1rem; background: linear-gradient(45deg, #FFD700, #FF6B35); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🍽️ Epicurean Delights</h1>
        <p style="font-size: 1.3rem; opacity: 0.9;">Experience Culinary Excellence • Premium Dining Experience</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Multi-step ordering process
    steps = {
        "order_type": show_order_type_selection,
        "customer_info": show_customer_info,
        "menu": show_menu_selection,
        "confirmation": show_order_confirmation,
        "tracking": track_order
    }
    
    if st.session_state.current_step in steps:
        steps[st.session_state.current_step]()

def show_order_type_selection():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 3rem;">
        <h2 style="color: #2E86AB; margin-bottom: 0.5rem;">🎯 Choose Your Dining Experience</h2>
        <p style="color: #666; font-size: 1.1rem;">Select how you'd like to enjoy our culinary creations</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">🏰</div>
            <h3 style="color: #2E86AB;">Fine Dining</h3>
        </div>
        """, unsafe_allow_html=True)
        st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=400&h=250&fit=crop", use_container_width=True, caption="Elegant Restaurant Ambiance")
        if st.button("**Reserve Table**", use_container_width=True, key="dine_in_btn"):
            st.session_state.order_type = "dine-in"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("✨ Premium table service in our elegant restaurant")
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">🎁</div>
            <h3 style="color: #2E86AB;">Takeaway</h3>
        </div>
        """, unsafe_allow_html=True)
        st.image("https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400&h=250&fit=crop", use_container_width=True, caption="Gourmet To-Go Packaging")
        if st.button("**Order To-Go**", use_container_width=True, key="takeaway_btn"):
            st.session_state.order_type = "takeaway"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("🚀 Quick pickup of gourmet meals to enjoy elsewhere")
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">🚀</div>
            <h3 style="color: #2E86AB;">Premium Delivery</h3>
        </div>
        """, unsafe_allow_html=True)
        st.image("https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=250&fit=crop", use_container_width=True, caption="Professional Delivery Service")
        if st.button("**Home Delivery**", use_container_width=True, key="delivery_btn"):
            st.session_state.order_type = "delivery"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("🏍️ Chef-prepared meals delivered to your doorstep")

def show_customer_info():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h2 style="color: #2E86AB; margin-bottom: 0.5rem;">👤 Personal Details</h2>
        <p style="color: #666;">Let us know how to best serve you</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("customer_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 Basic Information")
            customer_name = st.text_input(
                "**Full Name**", 
                placeholder="Enter your full name",
                value=st.session_state.customer_name
            )
            
            if st.session_state.order_type == "dine-in":
                table_number = st.selectbox(
                    "**Preferred Table**",
                    options=[f"Table {i} - {'Window' if i % 2 == 0 else 'Center'} View" for i in range(1, 21)],
                    index=st.session_state.table_number - 1 if st.session_state.table_number else 0
                )
                table_number = int(table_number.split(' ')[1])
            else:
                table_number = None
                if st.session_state.order_type == "delivery":
                    st.text_input("**Delivery Address**", placeholder="Enter your full address")
        
        with col2:
            st.markdown("### ⚙️ Order Preferences")
            order_notes = st.text_area(
                "**Special Instructions**", 
                placeholder="Dietary restrictions, allergies, special occasions, or preferences...",
                value=st.session_state.order_notes,
                height=120
            )
            
            payment_method = st.radio(
                "**Payment Method**",
                ["💵 Cash", "💳 Credit Card", "📱 Mobile Payment", "💎 VIP Account"],
                index=0 if st.session_state.payment_method == "cash" else 1
            )
        
        st.markdown("---")
        submitted = st.form_submit_button("**🚀 Continue to Gourmet Menu**", type="primary", use_container_width=True)
        
        if submitted:
            if customer_name.strip():
                st.session_state.customer_name = customer_name.strip()
                st.session_state.table_number = table_number
                st.session_state.order_notes = order_notes
                st.session_state.payment_method = "cash" if payment_method == "💵 Cash" else "card"
                st.session_state.current_step = "menu"
                st.rerun()
            else:
                st.error("👋 Please provide your name to continue")

def show_menu_selection():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h2 style="color: #2E86AB; margin-bottom: 0.5rem;">🍽️ Gourmet Menu</h2>
        <p style="color: #666;">Curated by our Executive Chef • Fresh Ingredients Daily</p>
    </div>
    """, unsafe_allow_html=True)
    
    categories = ['All', 'Beverage', 'Starter', 'Main Course', 'Dessert']
    selected_category = st.selectbox("**Filter by Category**", categories)
    
    try:
        menu_items = db.get_menu_items(selected_category if selected_category != 'All' else None)
    except Exception as e:
        st.error(f"Error loading menu: {e}")
        menu_items = []
    
    if not menu_items:
        st.warning("No menu items found. The database may not be properly initialized.")
        return
    
    # Display menu items in a grid
    cols = st.columns(2)
    for idx, item in enumerate(menu_items):
        with cols[idx % 2]:
            with st.container():
                st.markdown(f'<div class="menu-item-card">', unsafe_allow_html=True)
                
                # Food image
                try:
                    st.image(item['image_url'], use_container_width=True, caption=item['name'])
                except:
                    st.markdown(f'''
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                border-radius: 15px; height: 200px; display: flex; align-items: center; justify-content: center; color: white;">
                        <div style="text-align: center;">
                            <div style="font-size: 3rem;">🍽️</div>
                            <h3 style="color: white;">{item['name']}</h3>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                
                # Item details
                st.markdown(f"### {item['name']}")
                st.markdown(f"_{item['description']}_")
                
                col_price, col_rating = st.columns([2, 1])
                with col_price:
                    st.markdown(f"**💰 R {item['price']}**")
                with col_rating:
                    st.markdown("⭐ 4.8")
                
                # Add to cart section
                col_qty, col_inst, col_add = st.columns([1, 2, 1])
                with col_qty:
                    quantity = st.number_input("Qty", min_value=0, max_value=10, value=0, key=f"qty_{item['id']}")
                with col_inst:
                    instructions = st.text_input("Special requests", key=f"inst_{item['id']}", placeholder="e.g., no onions, extra sauce")
                with col_add:
                    if quantity > 0 and st.button("**+ Add**", key=f"add_{item['id']}", use_container_width=True):
                        cart_item = {
                            'id': item['id'],
                            'name': item['name'],
                            'price': item['price'],
                            'quantity': quantity,
                            'instructions': instructions
                        }
                        st.session_state.cart.append(cart_item)
                        st.success(f"✅ Added {quantity} x {item['name']}!")
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    show_cart_and_navigation()

def show_cart_and_navigation():
    if st.session_state.cart:
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="color: #2E86AB;">🛒 Your Culinary Selection</h2>
            <p style="color: #666;">Review your order before proceeding</p>
        </div>
        """, unsafe_allow_html=True)
        
        total = 0
        for i, item in enumerate(st.session_state.cart):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{item['name']}**")
                if item['instructions']:
                    st.caption(f"📝 _{item['instructions']}_")
            with col2:
                st.write(f"R {item['price']}")
            with col3:
                st.write(f"x{item['quantity']}")
            with col4:
                if st.button("🗑️", key=f"remove_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            total += item['price'] * item['quantity']
        
        st.markdown(f"### 💰 Total Amount: R {total:.2f}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Details", use_container_width=True):
                st.session_state.current_step = "customer_info"
                st.rerun()
        with col2:
            if st.button("**📦 Proceed to Checkout**", type="primary", use_container_width=True):
                st.session_state.current_step = "confirmation"
                st.rerun()
    else:
        st.info("🛒 Your culinary journey awaits! Add some exquisite dishes from our menu above.")
        if st.button("← Back to Personal Details"):
            st.session_state.current_step = "customer_info"
            st.rerun()

def show_order_confirmation():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h2 style="color: #2E86AB; margin-bottom: 0.5rem;">✅ Order Confirmation</h2>
        <p style="color: #666;">Finalize your gourmet experience</p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.cart:
        st.error("❌ Your cart is empty. Please add items before placing an order.")
        if st.button("← Back to Menu"):
            st.session_state.current_step = "menu"
            st.rerun()
        return
    
    with st.container():
        st.markdown('<div class="confirmation-box">', unsafe_allow_html=True)
        
        st.subheader("📋 Order Summary")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 👤 Customer Details")
            st.write(f"**Name:** {st.session_state.customer_name}")
            st.write(f"**Experience:** {st.session_state.order_type.title()}")
            st.write(f"**Payment:** {st.session_state.payment_method.title()}")
        
        with col2:
            st.markdown("### ⚙️ Order Settings")
            if st.session_state.order_type == "dine-in":
                st.write(f"**Table:** {st.session_state.table_number}")
            if st.session_state.order_notes:
                st.write(f"**Special Requests:** {st.session_state.order_notes}")
        
        st.markdown("### 🍽️ Selected Items")
        total = 0
        item_count = 0
        for item in st.session_state.cart:
            item_total = item['price'] * item['quantity']
            total += item_total
            item_count += item['quantity']
            st.write(f"• **{item['quantity']}x {item['name']}** - R {item_total:.2f}")
            if item['instructions']:
                st.caption(f"  _📝 {item['instructions']}_")
        
        st.markdown(f"### 💰 **Total Amount: R {total:.2f}**")
        st.markdown(f"**📦 Total Items: {item_count}**")
        st.markdown(f"**🕒 Order Time: {get_sa_time().strftime('%Y-%m-%d %H:%M:%S')} SAST**")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Menu", use_container_width=True):
            st.session_state.current_step = "menu"
            st.rerun()
    with col2:
        if st.button("**🚀 Confirm & Place Order**", type="primary", use_container_width=True):
            try:
                st.info("🔄 Processing your gourmet order...")
                
                order_id, order_token = db.add_order(
                    st.session_state.customer_name,
                    st.session_state.order_type,
                    st.session_state.cart,
                    st.session_state.table_number,
                    st.session_state.order_notes,
                    st.session_state.payment_method
                )
                
                if order_id and order_token:
                    st.session_state.order_placed = True
                    st.session_state.order_id = order_id
                    st.session_state.order_token = order_token
                    st.session_state.current_order_status = 'pending'
                    st.session_state.cart = []
                    st.session_state.current_step = "tracking"
                    
                    st.success(f"🎉 Order placed successfully!")
                    st.success(f"**Your Order Token:** {order_token}")
                    st.info("📱 Save this token to track your order status")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ Failed to create order. Please try again.")
                
            except Exception as e:
                st.error(f"❌ Error placing order: {e}")
                st.error("Please try again or contact our concierge for assistance.")

def track_order():
    load_css()
    
    st.markdown("""
    <div class="tracking-header">
        <h1 style="font-size: 3rem; margin-bottom: 1rem;">📱 Live Order Tracking</h1>
        <p style="font-size: 1.2rem; opacity: 0.9;">Watch your culinary masterpiece being prepared in real-time</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if we have an active order from ordering flow
    if st.session_state.get('order_placed') and st.session_state.get('order_token'):
        order_token = st.session_state.order_token
        display_order_tracking(order_token)
    else:
        # Allow manual order token entry
        st.markdown("""
        <div style="text-align: center; background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin-bottom: 2rem;">
            <h3 style="color: #2E86AB;">🔍 Track Your Order</h3>
            <p>Enter your order token to view real-time status updates</p>
        </div>
        """, unsafe_allow_html=True)
        
        order_token = st.text_input(
            "**Order Token**", 
            placeholder="ORD123456789",
            key="track_order_input"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("**🔍 Track Order**", type="primary", use_container_width=True):
                if order_token:
                    if order_token.startswith("ORD") and len(order_token) > 3:
                        display_order_tracking(order_token)
                    else:
                        st.error("❌ Invalid Order Token format. It should start with 'ORD' followed by numbers.")
                else:
                    st.error("❌ Please enter your order token")
        
        with col2:
            if st.button("**🔄 Demo Order**", use_container_width=True):
                # Create a demo order
                try:
                    demo_items = [
                        {'id': 1, 'name': 'Wagyu Beef Burger', 'price': 185, 'quantity': 1, 'instructions': 'Medium rare'},
                        {'id': 13, 'name': 'Chocolate Lava Cake', 'price': 85, 'quantity': 2, 'instructions': 'Extra ice cream'}
                    ]
                    demo_order_id, demo_order_token = db.add_order(
                        "Demo Customer",
                        "dine-in",
                        demo_items,
                        5,
                        "Demo order for tracking",
                        "card"
                    )
                    st.session_state.tracking_token = demo_order_token
                    st.success(f"🎉 Demo order created! Token: {demo_order_token}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating demo order: {e}")

def display_order_tracking(order_token):
    """Enhanced order tracking with beautiful UI"""
    if db is None:
        st.error("❌ Database not available")
        return
        
    st.info(f"🔍 Tracking order with token: **{order_token}**")
    
    # Get current order status
    current_status = db.get_order_status(order_token)
    
    if current_status is None:
        st.error(f"❌ Order not found with token: {order_token}")
        return
    
    # Get full order details
    order = db.get_order_by_token(order_token)
    
    if not order:
        st.error("❌ Could not load order details")
        return
    
    # Status configuration with beautiful styling
    status_config = {
        'pending': {'emoji': '⏳', 'color': '#FF6B35', 'name': 'Order Received', 'description': 'We have received your order and our chefs are preparing'},
        'preparing': {'emoji': '👨‍🍳', 'color': '#2E86AB', 'name': 'In Preparation', 'description': 'Our master chefs are crafting your culinary experience'},
        'ready': {'emoji': '✅', 'color': '#28A745', 'name': 'Ready for Service', 'description': 'Your gourmet meal is ready! Get ready to indulge'},
        'completed': {'emoji': '🎉', 'color': '#008000', 'name': 'Experience Complete', 'description': 'Thank you for dining with us! We hope you enjoyed'},
        'collected': {'emoji': '📦', 'color': '#4B0082', 'name': 'Order Collected', 'description': 'Your takeaway order has been collected'}
    }
    
    current_status_info = status_config.get(current_status, status_config['pending'])
    
    # Display beautiful status header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {current_status_info['color']} 0%, {current_status_info['color']}80 100%); 
                color: white; padding: 3rem 2rem; border-radius: 25px; text-align: center; margin-bottom: 2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
        <h1 style="margin: 0; font-size: 4rem;">{current_status_info['emoji']}</h1>
        <h2 style="margin: 15px 0; color: white; font-size: 2.5rem;">{current_status_info['name']}</h2>
        <p style="margin: 0; font-size: 1.3rem; opacity: 0.9;">{current_status_info['description']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Order details in a beautiful card
    st.markdown("""
    <div style="background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.1); margin-bottom: 2rem;">
        <h3 style="color: #2E86AB; margin-bottom: 1.5rem;">📋 Order Details</h3>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🎯 Order Information**")
        st.write(f"**Order ID:** #{order[0]}")
        st.write(f"**Customer:** {order[2]}")
        st.write(f"**Service Type:** {order[3].title()}")
        st.write(f"**Payment:** {order[10].title()}")
    
    with col2:
        st.markdown("**💰 Order Summary**")
        st.write(f"**Total Amount:** R {order[5]:.2f}")
        st.write(f"**Order Date:** {order[6]}")
        st.write(f"**Items Ordered:** {order[11]}")
        if order[7]:
            st.write(f"**Special Notes:** {order[7]}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Enhanced progress tracker
    st.markdown("""
    <div style="background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.1);">
        <h3 style="color: #2E86AB; margin-bottom: 1.5rem;">🔄 Order Journey</h3>
    """, unsafe_allow_html=True)
    
    # Define status flow based on order type
    order_type = order[3]
    if order_type == 'takeaway':
        status_flow = ['pending', 'preparing', 'ready', 'collected']
        status_names = ['Order Received', 'In Preparation', 'Ready for Collection', 'Collected']
        status_icons = ['📥', '👨‍🍳', '✅', '📦']
    else:
        status_flow = ['pending', 'preparing', 'ready', 'completed']
        status_names = ['Order Received', 'In Preparation', 'Ready to Serve', 'Experience Complete']
        status_icons = ['📥', '👨‍🍳', '🍽️', '🎉']
    
    current_index = status_flow.index(current_status) if current_status in status_flow else 0
    
    # Progress bar
    progress = current_index / (len(status_flow) - 1) if len(status_flow) > 1 else 0
    st.markdown(f"""
    <div class="progress-container">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    height: 10px; border-radius: 25px; width: {progress * 100}%; 
                    transition: all 0.5s ease;"></div>
    </div>
    <p style="text-align: center; color: #666; margin: 1rem 0;"><strong>Progress: {int(progress * 100)}% Complete</strong></p>
    """, unsafe_allow_html=True)
    
    # Beautiful status steps
    cols = st.columns(len(status_flow))
    for i, (status, status_name, icon) in enumerate(zip(status_flow, status_names, status_icons)):
        status_info = status_config.get(status, status_config['pending'])
        
        with cols[i]:
            if i < current_index:
                # Completed step
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #28A745, #20C997); 
                            color: white; border-radius: 15px; margin: 5px; box-shadow: 0 5px 15px rgba(40, 167, 69, 0.3);">
                    <div style="font-size: 2.5rem;">✅</div>
                    <strong>{status_name}</strong>
                    <div style="font-size: 0.8rem; opacity: 0.9; margin-top: 5px;">Completed</div>
                </div>
                """, unsafe_allow_html=True)
            elif i == current_index:
                # Current step
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, {status_info['color']}, {status_info['color']}80); 
                            color: white; border-radius: 15px; margin: 5px; box-shadow: 0 8px 25px {status_info['color']}40; 
                            border: 3px solid #FFD700; transform: scale(1.05);">
                    <div style="font-size: 2.5rem;">{icon}</div>
                    <strong>{status_name}</strong>
                    <div style="font-size: 0.8rem; opacity: 0.9; margin-top: 5px;">In Progress</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Show estimated time for current step
                if status == 'preparing':
                    st.info("⏱️ **Estimated preparation time: 15-20 minutes**")
                elif status == 'ready':
                    st.success("🎉 **Your gourmet experience is ready!**")
                    st.balloons()
            else:
                # Future step
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: #f8f9fa; color: #666; border-radius: 15px; margin: 5px; 
                            box-shadow: 0 3px 10px rgba(0,0,0,0.1);">
                    <div style="font-size: 2.5rem;">{icon}</div>
                    <strong>{status_name}</strong>
                    <div style="font-size: 0.8rem; opacity: 0.9; margin-top: 5px;">Upcoming</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Auto-refresh for active orders
    if current_status not in ['completed', 'collected']:
        st.markdown("---")
        refresh_col1, refresh_col2 = st.columns([3, 1])
        with refresh_col1:
            st.info("🔄 **Live Tracking Active** - Status updates automatically every 5 seconds")
            st.write(f"**Last checked:** {get_sa_time().strftime('%H:%M:%S')} SAST")
        with refresh_col2:
            if st.button("🔄 Refresh Now", use_container_width=True):
                st.rerun()
        
        # Auto-refresh every 5 seconds
        time.sleep(5)
        st.rerun()

# Enhanced Kitchen Dashboard
def kitchen_dashboard():
    if db is None:
        st.error("❌ Database not available")
        return
        
    load_css()
    
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 3rem; margin-bottom: 1rem;">👨‍🍳 Chef's Command Center</h1>
        <p style="font-size: 1.2rem; opacity: 0.9;">Real-time Order Management • Premium Kitchen Operations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Kitchen overview image
    st.image("https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=1000&h=400&fit=crop", 
             use_container_width=True, caption="State-of-the-Art Kitchen")
    
    if st.button("🔄 Refresh Orders", use_container_width=True):
        st.rerun()
    
    # Kitchen metrics
    try:
        orders = db.get_active_orders()
        pending_orders = len([o for o in orders if o['status'] == 'pending'])
        preparing_orders = len([o for o in orders if o['status'] == 'preparing'])
        ready_orders = len([o for o in orders if o['status'] == 'ready'])
    except:
        pending_orders = preparing_orders = ready_orders = 0
        orders = []
    
    # Beautiful metrics cards
    metrics_cols = st.columns(3)
    with metrics_cols[0]:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 2.5rem;">⏳</div>
            <h3 style="color: #FF6B35; margin: 0.5rem 0;">Pending</h3>
            <h2 style="color: #FF6B35; margin: 0;">{pending_orders}</h2>
        </div>
        """, unsafe_allow_html=True)
    with metrics_cols[1]:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 2.5rem;">👨‍🍳</div>
            <h3 style="color: #2E86AB; margin: 0.5rem 0;">Preparing</h3>
            <h2 style="color: #2E86AB; margin: 0;">{preparing_orders}</h2>
        </div>
        """, unsafe_allow_html=True)
    with metrics_cols[2]:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 2.5rem;">✅</div>
            <h3 style="color: #28A745; margin: 0.5rem 0;">Ready</h3>
            <h2 style="color: #28A745; margin: 0;">{ready_orders}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Order management tabs
    tab1, tab2, tab3 = st.tabs([f"⏳ Pending ({pending_orders})", f"👨‍🍳 Preparing ({preparing_orders})", f"✅ Ready ({ready_orders})"])
    
    with tab1:
        display_kitchen_orders(orders, 'pending')
    with tab2:
        display_kitchen_orders(orders, 'preparing')
    with tab3:
        display_kitchen_orders(orders, 'ready')

def display_kitchen_orders(orders, status):
    filtered_orders = [order for order in orders if order['status'] == status]
    
    if not filtered_orders:
        st.info(f"🎉 No {status} orders - Kitchen is clear!")
        return
    
    for order in filtered_orders:
        status_class = f"status-{status}"
        with st.container():
            st.markdown(f'<div class="order-card {status_class}">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### 🎯 Order #{order['id']} - {order['customer_name']}")
                st.markdown(f"**Service Type:** {order['order_type'].title()} | **Table:** {order['table_number'] or 'N/A'}")
                st.markdown(f"**📦 Items:** {order['items']}")
                if order['notes']:
                    st.markdown(f"**📝 Notes:** {order['notes']}")
                st.markdown(f"**🕒 Order Time:** {order['order_date']}")
                st.markdown(f"**💰 Total:** R {order['total_amount']:.2f}")
            
            with col2:
                if status == 'pending':
                    if st.button("Start Preparation", key=f"start_{order['id']}", use_container_width=True):
                        if db.update_order_status(order['id'], 'preparing', 'Chef started preparation'):
                            st.success("✅ Order preparation started!")
                            time.sleep(1)
                            st.rerun()
                elif status == 'preparing':
                    if st.button("Mark as Ready", key=f"ready_{order['id']}", use_container_width=True):
                        if db.update_order_status(order['id'], 'ready', 'Order ready for service'):
                            st.success("🎉 Order marked as ready!")
                            time.sleep(1)
                            st.rerun()
                elif status == 'ready':
                    new_status = 'collected' if order['order_type'] == 'takeaway' else 'completed'
                    status_text = 'Mark Collected' if order['order_type'] == 'takeaway' else 'Complete Service'
                    if st.button(status_text, key=f"complete_{order['id']}", use_container_width=True):
                        if db.update_order_status(order['id'], new_status, 'Order completed by kitchen'):
                            st.success(f"✅ Order {new_status}!")
                            time.sleep(1)
                            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

# Enhanced Analytics Dashboard
def analytics_dashboard():
    if db is None:
        st.error("❌ Database not available")
        return
        
    load_css()
    
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 3rem; margin-bottom: 1rem;">📊 Business Intelligence</h1>
        <p style="font-size: 1.2rem; opacity: 0.9;">Data-Driven Insights • Performance Analytics</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Analytics overview image
    st.image("https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1000&h=400&fit=crop", 
             use_container_width=True, caption="Business Performance Dashboard")
    
    st.info("📈 Advanced analytics features will be available as more orders are processed")
    
    # Sample analytics data (would be replaced with real data)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 2rem;">📦</div>
            <h4>Total Orders</h4>
            <h2>156</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 2rem;">💰</div>
            <h4>Revenue</h4>
            <h2>R 24,580</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 2rem;">⭐</div>
            <h4>Avg Rating</h4>
            <h2>4.8/5</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div style="font-size: 2rem;">👥</div>
            <h4>Customers</h4>
            <h2>128</h2>
        </div>
        """, unsafe_allow_html=True)

# Enhanced QR Code Management
def qr_management():
    load_css()
    
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 3rem; margin-bottom: 1rem;">📱 Digital Experience</h1>
        <p style="font-size: 1.2rem; opacity: 0.9;">QR Code Management • Contactless Ordering</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.1);">
            <h3 style="color: #2E86AB;">🎯 QR Code Generator</h3>
            <p>Create custom QR codes for table ordering</p>
        </div>
        """, unsafe_allow_html=True)
        
        qr_url = st.text_input("Ordering URL", "https://epicurean-delights.streamlit.app/")
        qr_size = st.slider("QR Code Size", 200, 500, 300)
        
        if st.button("Generate QR Code", type="primary", use_container_width=True):
            qr_img = generate_qr_code(qr_url)
            st.image(f"data:image/png;base64,{qr_img}", width=qr_size)
            st.success("✅ QR Code generated successfully!")
    
    with col2:
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.1);">
            <h3 style="color: #2E86AB;">📊 Usage Analytics</h3>
            <p>QR code performance metrics</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.metric("Total Scans", "1,247", "+128 this week")
        st.metric("Mobile Orders", "893", "71.5% of total")
        st.metric("Peak Scan Time", "19:30", "Dinner rush")
        
        st.info("""
        **💡 Placement Tips:**
        - **Tables:** 85% conversion rate
        - **Entrance:** 62% conversion rate  
        - **Counter:** 45% conversion rate
        - **Menus:** 78% conversion rate
        """)

# Enhanced Staff Navigation
def staff_navigation():
    st.sidebar.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 1.5rem; border-radius: 15px; margin: 1rem 0; text-align: center;">
        <h3 style="margin: 0; color: white;">👨‍💼 Staff Portal</h3>
        <p style="margin: 0; opacity: 0.9;">Premium Management System</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.user:
        st.sidebar.markdown(f"""
        <div style="background: white; padding: 1rem; border-radius: 10px; box-shadow: 0 3px 10px rgba(0,0,0,0.1); margin: 1rem 0;">
            <h4 style="color: #2E86AB; margin: 0;">Welcome, {st.session_state.user['username']}!</h4>
            <p style="color: #666; margin: 0;">Role: {st.session_state.user['role'].title()}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    page = st.sidebar.radio("**Navigation Menu**", 
                          ["👨‍🍳 Kitchen Dashboard", "📊 Analytics", "📱 QR Codes"])
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🚀 Quick Actions")
    
    if st.sidebar.button("🔄 Refresh All Data", use_container_width=True):
        st.rerun()
    
    # Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", type="primary", use_container_width=True):
        logout()
    
    # Page routing
    if page == "👨‍🍳 Kitchen Dashboard":
        kitchen_dashboard()
    elif page == "📊 Analytics":
        analytics_dashboard()
    elif page == "📱 QR Codes":
        qr_management()

# Enhanced Landing Page
def landing_page():
    load_css()
    
    # Hero Section with beautiful background
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 4rem; margin-bottom: 1rem; background: linear-gradient(45deg, #FFD700, #FF6B35, #667eea); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Epicurean Delights</h1>
        <p style="font-size: 1.5rem; margin-bottom: 2rem; opacity: 0.9;">Where Culinary Art Meets Exceptional Experience</p>
        <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
            <div style="background: rgba(255,255,255,0.2); backdrop-filter: blur(10px); padding: 1rem 2rem; border-radius: 25px; border: 1px solid rgba(255,255,255,0.3);">
                🍽️ Michelin-Star Inspired
            </div>
            <div style="background: rgba(255,255,255,0.2); backdrop-filter: blur(10px); padding: 1rem 2rem; border-radius: 25px; border: 1px solid rgba(255,255,255,0.3);">
                👨‍🍳 Master Chefs
            </div>
            <div style="background: rgba(255,255,255,0.2); backdrop-filter: blur(10px); padding: 1rem 2rem; border-radius: 25px; border: 1px solid rgba(255,255,255,0.3);">
                ⚡ Premium Service
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Restaurant Showcase
    st.markdown("""
    <div style="text-align: center; margin: 3rem 0;">
        <h2 style="color: #2E86AB; margin-bottom: 1rem;">🏰 Our Premium Venues</h2>
        <p style="color: #666; font-size: 1.1rem;">Experience luxury across our exquisite locations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Restaurant images gallery
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=400&h=250&fit=crop", 
                 use_container_width=True, caption="Main Dining Hall")
        st.markdown("**Elegant Fine Dining**")
        st.caption("Sophisticated atmosphere with crystal chandeliers")
    
    with col2:
        st.image("https://images.unsplash.com/photo-1559329007-40df8a9345d8?w=400&h=250&fit=crop", 
                 use_container_width=True, caption="Garden Terrace")
        st.markdown("**Al Fresco Experience**")
        st.caption("Beautiful outdoor seating with city views")
    
    with col3:
        st.image("https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=250&fit=crop", 
                 use_container_width=True, caption="Private Chef's Table")
        st.markdown("**Exclusive Private Dining**")
        st.caption("Intimate setting with personalized service")
    
    # Features Grid
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; margin: 3rem 0;">
        <h2 style="color: #2E86AB; margin-bottom: 1rem;">🌟 Why Choose Epicurean Delights?</h2>
        <p style="color: #666; font-size: 1.1rem;">Unparalleled dining experiences crafted with passion</p>
    </div>
    """, unsafe_allow_html=True)
    
    features = st.columns(3)
    
    with features[0]:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 4rem;">🍽️</div>
            <h3 style="color: #2E86AB;">Culinary Excellence</h3>
            <p style="color: #666;">Award-winning chefs creating innovative dishes with locally-sourced, premium ingredients</p>
        </div>
        """, unsafe_allow_html=True)
    
    with features[1]:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 4rem;">⚡</div>
            <h3 style="color: #2E86AB;">Seamless Experience</h3>
            <p style="color: #666;">From digital ordering to real-time tracking, enjoy a frictionless premium dining journey</p>
        </div>
        """, unsafe_allow_html=True)
    
    with features[2]:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 4rem;">🌟</div>
            <h3 style="color: #2E86AB;">Luxury Service</h3>
            <p style="color: #666;">Impeccable service, elegant ambiance, and attention to every detail for an unforgettable experience</p>
        </div>
        """, unsafe_allow_html=True)
    
    # How It Works
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; margin: 3rem 0;">
        <h2 style="color: #2E86AB; margin-bottom: 1rem;">🚀 Your Culinary Journey</h2>
        <p style="color: #666; font-size: 1.1rem;">Experience the future of fine dining in four simple steps</p>
    </div>
    """, unsafe_allow_html=True)
    
    steps = st.columns(4)
    
    step_data = [
        {"icon": "📱", "title": "Scan & Browse", "desc": "Use your device to explore our curated menu with stunning visuals"},
        {"icon": "🛒", "title": "Customize Order", "desc": "Select premium dishes and add personal preferences"},
        {"icon": "👨‍🍳", "title": "Chef's Preparation", "desc": "Watch as master chefs craft your culinary masterpiece"},
        {"icon": "🎯", "title": "Savor & Enjoy", "desc": "Indulge in an exceptional dining experience"}
    ]
    
    for idx, step in enumerate(steps):
        with step:
            data = step_data[idx]
            st.markdown(f"""
            <div style="background: white; padding: 2rem 1rem; border-radius: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.08); text-align: center; height: 100%;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">{data['icon']}</div>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin: 0 auto 1rem auto;">{idx + 1}</div>
                <h4 style="color: #2E86AB; margin-bottom: 0.5rem;">{data['title']}</h4>
                <p style="font-size: 0.9rem; color: #666; margin: 0;">{data['desc']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Call to Action
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                padding: 3rem 2rem; border-radius: 25px; margin: 2rem 0;">
        <h2 style="color: #2E86AB; margin-bottom: 1rem;">Ready to Begin Your Culinary Adventure?</h2>
        <p style="color: #666; font-size: 1.1rem; margin-bottom: 2rem;">Join us for an unforgettable dining experience</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Action Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("**🎯 Start Your Order**", type="primary", use_container_width=True):
            st.session_state.page = "customer"
            st.rerun()
    
    with col2:
        if st.button("**👨‍💼 Staff Portal**", use_container_width=True):
            st.session_state.page = "staff"
            st.rerun()

# Main Application
def main():
    st.set_page_config(
        page_title="Epicurean Delights - Premium Restaurant",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_session_state()
    
    # Page routing
    if st.session_state.page == "landing":
        landing_page()
    elif st.session_state.page == "customer":
        customer_ordering()
    elif st.session_state.page == "staff":
        if st.session_state.logged_in:
            staff_navigation()
        else:
            staff_login()
            if st.sidebar.button("← Back to Home"):
                st.session_state.page = "landing"
                st.rerun()

if __name__ == "__main__":
    main()