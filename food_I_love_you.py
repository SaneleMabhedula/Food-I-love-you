import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
import time
import random
import qrcode
from io import BytesIO
import base64
import pytz
import os
import requests

# Set South African timezone
SA_TIMEZONE = pytz.timezone('Africa/Johannesburg')

def get_sa_time():
    """Get current South African time"""
    return datetime.now(SA_TIMEZONE)

# Database setup with migration support
class RestaurantDB:
    def __init__(self, db_name="restaurant.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Drop and recreate all tables to ensure fresh start
        cursor.execute("DROP TABLE IF EXISTS order_status_history")
        cursor.execute("DROP TABLE IF EXISTS order_items") 
        cursor.execute("DROP TABLE IF EXISTS orders")
        cursor.execute("DROP TABLE IF EXISTS menu_items")
        cursor.execute("DROP TABLE IF EXISTS users")
        
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
        
        # Orders table
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
                payment_method TEXT DEFAULT 'cash'
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
                FOREIGN KEY (order_id) REFERENCES orders (id),
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
                FOREIGN KEY (order_id) REFERENCES orders (id)
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
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password, role) 
                VALUES (?, ?, ?)
            ''', ('chef', hashlib.sha256('chef123'.encode()).hexdigest(), 'chef'))
        except sqlite3.IntegrityError:
            pass
        
        # Clear existing menu items and insert new menu with reliable images
        cursor.execute('DELETE FROM menu_items')
        
        # SIMPLIFIED MENU WITH RELIABLE IMAGES
        menu_items = [
            # BEVERAGES
            ('Cappuccino', 'Freshly brewed coffee with steamed milk', 25, 'Beverage', 'https://images.unsplash.com/photo-1561047029-3000c68339ca?ixlib=rb-4.0.3'),
            ('Coca-Cola', 'Ice cold Coca-Cola', 18, 'Beverage', 'https://images.unsplash.com/photo-1622483767028-3f66f32aef97?ixlib=rb-4.0.3'),
            ('Orange Juice', 'Freshly squeezed orange juice', 22, 'Beverage', 'https://images.unsplash.com/photo-1613478223719-2ab802602423?ixlib=rb-4.0.3'),
            ('Bottled Water', '500ml still water', 15, 'Beverage', 'bottled_water.jpg'),  # Local image
            
            # BURGERS
            ('Beef Burger', 'Classic beef burger with cheese and veggies', 65, 'Main Course', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?ixlib=rb-4.0.3'),
            ('Chicken Burger', 'Grilled chicken breast with mayo and lettuce', 55, 'Main Course', 'chicken_burger.jpg'),  # Local image
            ('Cheese Burger', 'Double beef patty with extra cheese', 75, 'Main Course', 'https://images.unsplash.com/photo-1607013251379-e6eecfffe234?ixlib=rb-4.0.3'),
            
            # GRILLED ITEMS
            ('Grilled Chicken', 'Tender grilled chicken breast with herbs', 85, 'Main Course', 'https://images.unsplash.com/photo-1532550907401-a500c9a57435?ixlib=rb-4.0.3'),
            ('Beef Steak', 'Juicy beef steak with pepper sauce', 120, 'Main Course', 'beef_steak.jpg'),  # Local image
            ('Grilled Fish', 'Fresh fish with lemon butter sauce', 95, 'Main Course', 'grilled_fish.jpg'),  # Local image
            
            # DESSERTS
            ('Chocolate Cake', 'Rich chocolate cake with ganache', 35, 'Dessert', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?ixlib=rb-4.0.3'),
            ('Ice Cream', 'Vanilla ice cream with chocolate sauce', 25, 'Dessert', 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?ixlib=rb-4.0.3'),
            ('Apple Pie', 'Warm apple pie with cinnamon', 30, 'Dessert', 'apple_pie.jpg'),  # Local image
            
            # SIDES
            ('French Fries', 'Crispy golden fries', 25, 'Starter', 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?ixlib=rb-4.0.3'),
            ('Onion Rings', 'Beer-battered onion rings', 28, 'Starter', 'onion_rings.jpg'),  # Local image
            ('Garlic Bread', 'Toasted bread with garlic butter', 20, 'Starter', 'garlic_bread.jpg')  # Local image
        ]
        
        for item in menu_items:
            cursor.execute('''
                INSERT INTO menu_items (name, description, price, category, image_url)
                VALUES (?, ?, ?, ?, ?)
            ''', item)
        
        self.conn.commit()

    def get_real_analytics(self, days=30):
        """Get real analytics data from the database"""
        cursor = self.conn.cursor()
        
        try:
            # Total revenue and orders for the period
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_orders,
                    COALESCE(SUM(total_amount), 0) as total_revenue,
                    COALESCE(AVG(total_amount), 0) as avg_order_value
                FROM orders 
                WHERE order_date >= datetime('now', '-' || ? || ' days')
            ''', (days,))
            totals = cursor.fetchone()
            
            # Daily revenue trend
            cursor.execute('''
                SELECT 
                    date(order_date) as order_day,
                    COUNT(*) as daily_orders,
                    COALESCE(SUM(total_amount), 0) as daily_revenue
                FROM orders 
                WHERE order_date >= datetime('now', '-' || ? || ' days')
                GROUP BY order_day
                ORDER BY order_day
            ''', (days,))
            daily_data = cursor.fetchall()
            
            # Revenue by hour
            cursor.execute('''
                SELECT 
                    strftime('%H', order_date) as hour,
                    COUNT(*) as order_count,
                    COALESCE(SUM(total_amount), 0) as hourly_revenue
                FROM orders 
                WHERE order_date >= datetime('now', '-' || ? || ' days')
                GROUP BY hour
                ORDER BY hour
            ''', (days,))
            hourly_data = cursor.fetchall()
            
            # Popular dishes
            cursor.execute('''
                SELECT 
                    oi.menu_item_name,
                    SUM(oi.quantity) as total_quantity,
                    SUM(oi.quantity * oi.price) as total_revenue,
                    COUNT(DISTINCT oi.order_id) as order_count
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.order_date >= datetime('now', '-' || ? || ' days')
                GROUP BY oi.menu_item_name
                ORDER BY total_quantity DESC
                LIMIT 10
            ''', (days,))
            popular_dishes = cursor.fetchall()
            
            # Category distribution
            cursor.execute('''
                SELECT 
                    mi.category,
                    SUM(oi.quantity) as total_quantity,
                    SUM(oi.quantity * oi.price) as total_revenue,
                    COUNT(DISTINCT oi.order_id) as order_count
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE o.order_date >= datetime('now', '-' || ? || ' days')
                GROUP BY mi.category
                ORDER BY total_quantity DESC
            ''', (days,))
            category_distribution = cursor.fetchall()
            
            # Payment method distribution
            cursor.execute('''
                SELECT 
                    payment_method,
                    COUNT(*) as order_count,
                    COALESCE(SUM(total_amount), 0) as total_revenue
                FROM orders 
                WHERE order_date >= datetime('now', '-' || ? || ' days')
                GROUP BY payment_method
            ''', (days,))
            payment_distribution = cursor.fetchall()
            
            # Order type distribution
            cursor.execute('''
                SELECT 
                    order_type,
                    COUNT(*) as order_count,
                    COALESCE(SUM(total_amount), 0) as total_revenue
                FROM orders 
                WHERE order_date >= datetime('now', '-' || ? || ' days')
                GROUP BY order_type
            ''', (days,))
            order_type_distribution = cursor.fetchall()
            
            return {
                'totals': totals,
                'daily_trend': daily_data,
                'hourly_data': hourly_data,
                'popular_dishes': popular_dishes,
                'category_distribution': category_distribution,
                'payment_distribution': payment_distribution,
                'order_type_distribution': order_type_distribution
            }
            
        except Exception as e:
            st.error(f"Error in get_real_analytics: {e}")
            # Return sample data for demo
            return self.get_sample_analytics_data(days)
    
    def get_sample_analytics_data(self, days=30):
        """Generate sample analytics data for demonstration"""
        # Generate sample daily data
        daily_data = []
        base_date = datetime.now() - timedelta(days=days)
        for i in range(days):
            date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
            orders = random.randint(5, 20)
            revenue = random.randint(800, 3000)
            daily_data.append((date, orders, revenue))
        
        # Generate sample hourly data
        hourly_data = []
        for hour in range(8, 22):  # 8 AM to 10 PM
            order_count = random.randint(2, 15)
            hourly_revenue = random.randint(200, 1200)
            hourly_data.append((f"{hour:02d}", order_count, hourly_revenue))
        
        # Sample popular dishes
        popular_dishes = [
            ('Beef Burger', 45, 2925, 38),
            ('Chicken Burger', 32, 1760, 28),
            ('Grilled Chicken', 28, 2380, 25),
            ('Cappuccino', 56, 1400, 45),
            ('French Fries', 42, 1050, 35),
            ('Chocolate Cake', 25, 875, 22),
            ('Beef Steak', 18, 2160, 16),
            ('Orange Juice', 30, 660, 26),
            ('Cheese Burger', 15, 1125, 13),
            ('Garlic Bread', 22, 440, 18)
        ]
        
        # Sample category distribution
        category_distribution = [
            ('Main Course', 124, 9230, 98),
            ('Beverage', 86, 2060, 71),
            ('Starter', 64, 1490, 53),
            ('Dessert', 41, 1315, 35)
        ]
        
        # Sample payment distribution
        payment_distribution = [
            ('cash', 215, 12560),
            ('card', 85, 5120)
        ]
        
        # Sample order type distribution
        order_type_distribution = [
            ('dine-in', 185, 11240),
            ('takeaway', 95, 5480),
            ('delivery', 20, 960)
        ]
        
        totals = (300, 17680, 58.93)
        
        return {
            'totals': totals,
            'daily_trend': daily_data,
            'hourly_data': hourly_data,
            'popular_dishes': popular_dishes,
            'category_distribution': category_distribution,
            'payment_distribution': payment_distribution,
            'order_type_distribution': order_type_distribution
        }
    
    def get_todays_orders_count(self):
        """Get count of orders from today only"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT COUNT(*) 
                FROM orders 
                WHERE date(order_date) = date('now')
            ''')
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            st.error(f"Error getting today's orders: {e}")
            return 0
    
    def get_all_orders(self, status=None):
        """Get orders with optional status filter"""
        cursor = self.conn.cursor()
        if status:
            cursor.execute('SELECT * FROM orders WHERE status = ? ORDER BY order_date DESC', (status,))
        else:
            cursor.execute('SELECT * FROM orders ORDER BY order_date DESC')
        return cursor.fetchall()
    
    def get_active_orders(self):
        """Get orders that are not completed/collected"""
        cursor = self.conn.cursor()
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
    
    def get_recent_orders(self, limit=25):
        """Get recent orders with proper ordering"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT o.*, 
                   GROUP_CONCAT(oi.menu_item_name || ' (x' || oi.quantity || ')', ', ') as items,
                   COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id 
            ORDER BY o.order_date DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_menu_items(self, category=None):
        cursor = self.conn.cursor()
        query = 'SELECT * FROM menu_items WHERE available = 1'
        if category:
            query += f" AND category = '{category}'"
        query += " ORDER BY category, name"
        
        cursor.execute(query)
        return cursor.fetchall()

    def add_order(self, customer_name, order_type, items, table_number=None, notes="", payment_method="cash"):
        cursor = self.conn.cursor()
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        # Generate unique order token
        order_token = f"ORD{random.randint(1000, 9999)}{int(time.time()) % 10000}"
        
        # Use current South African timestamp for order date
        current_time = get_sa_time().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute('''
                INSERT INTO orders (customer_name, order_type, table_number, total_amount, notes, order_token, order_date, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (customer_name, order_type, table_number, total_amount, notes, order_token, current_time, payment_method))
            
            order_id = cursor.lastrowid
            
            # Debug: Show what we're inserting
            st.success(f"✅ Debug: Creating order #{order_id} with token: {order_token}")
            
            for item in items:
                cursor.execute('''
                    INSERT INTO order_items (order_id, menu_item_id, menu_item_name, quantity, price, special_instructions)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (order_id, item['id'], item['name'], item['quantity'], item['price'], item.get('instructions', '')))
            
            # Add initial status to history
            cursor.execute('''
                INSERT INTO order_status_history (order_id, status, notes)
                VALUES (?, ?, ?)
            ''', (order_id, 'pending', 'Order placed by customer'))
            
            self.conn.commit()
            
            # Verify the order was created
            cursor.execute('SELECT order_token FROM orders WHERE id = ?', (order_id,))
            verify_token = cursor.fetchone()
            if verify_token:
                st.success(f"✅ Debug: Order verified - token in database: {verify_token[0]}")
            else:
                st.error("❌ Debug: Order verification failed!")
            
            return order_id, order_token
            
        except Exception as e:
            st.error(f"❌ Debug: Error in add_order: {e}")
            self.conn.rollback()
            raise e
    
    def update_order_status(self, order_id, new_status, notes=""):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE orders SET status = ? WHERE id = ?
        ''', (new_status, order_id))
        
        cursor.execute('''
            INSERT INTO order_status_history (order_id, status, notes)
            VALUES (?, ?, ?)
        ''', (order_id, new_status, notes))
        
        self.conn.commit()
        return True
    
    def get_order_by_token(self, order_token):
        """FIXED VERSION: Get order details by token with proper error handling"""
        cursor = self.conn.cursor()
        
        # First, let's check if the order exists at all
        cursor.execute('SELECT id FROM orders WHERE order_token = ?', (order_token,))
        order_exists = cursor.fetchone()
        
        if not order_exists:
            st.error(f"❌ Debug: No order found with token: {order_token}")
            # Let's see what tokens exist for debugging
            cursor.execute('SELECT order_token FROM orders ORDER BY id DESC LIMIT 5')
            recent_tokens = cursor.fetchall()
            if recent_tokens:
                st.info(f"🔍 Recent order tokens in system: {[token[0] for token in recent_tokens]}")
            return None
        
        # Now get the full order details with a simpler query
        try:
            cursor.execute('''
                SELECT o.*, 
                       (SELECT GROUP_CONCAT(oi.menu_item_name || ' (x' || oi.quantity || ')', ', ') 
                        FROM order_items oi 
                        WHERE oi.order_id = o.id) as items,
                       (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) as item_count
                FROM orders o
                WHERE o.order_token = ?
            ''', (order_token,))
            result = cursor.fetchone()
            
            if result:
                st.success(f"✅ Debug: Found order with token {order_token}")
                return result
            else:
                st.error(f"❌ Debug: Query returned no results for token: {order_token}")
                return None
                
        except Exception as e:
            st.error(f"❌ Debug: Error in get_order_by_token: {e}")
            # Fallback to simple order query
            try:
                cursor.execute('SELECT * FROM orders WHERE order_token = ?', (order_token,))
                simple_result = cursor.fetchone()
                if simple_result:
                    st.info("ℹ️ Debug: Using simple query - order found but item details missing")
                    # Add placeholder for items and item_count
                    if simple_result:
                        simple_result = list(simple_result)
                        simple_result.append("Items details unavailable")  # items
                        simple_result.append(0)  # item_count
                        simple_result.append(simple_result[8] if len(simple_result) > 8 else "")  # order_notes
                    return tuple(simple_result) if simple_result else None
                return None
            except Exception as e2:
                st.error(f"❌ Debug: Fallback query also failed: {e2}")
                return None
    
    def get_order_status_history(self, order_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM order_status_history 
            WHERE order_id = ? 
            ORDER BY created_at DESC
        ''', (order_id,))
        return cursor.fetchall()
    
    def get_order_status(self, order_token):
        """Get just the current status of an order for live updates"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT status FROM orders WHERE order_token = ?', (order_token,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                st.error(f"❌ Debug: No status found for token: {order_token}")
                return None
        except Exception as e:
            st.error(f"❌ Debug: Error in get_order_status: {e}")
            return None

# Initialize database with forced reset
try:
    # Delete existing database to force fresh start
    if os.path.exists("restaurant.db"):
        os.remove("restaurant.db")
    db = RestaurantDB()
except Exception as e:
    st.error(f"Database initialization error: {e}")
    import sqlite3
    conn = sqlite3.connect("restaurant.db", check_same_thread=False)
    db = type('obj', (object,), {'conn': conn})

# QR Code Generator
def generate_qr_code(url, size=300):
    """Generate QR code for the given URL"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return img_str

def get_qr_download_link(img_str, filename="sanele_ordering_qr.png"):
    """Generate download link for QR code"""
    href = f'<a href="data:image/png;base64,{img_str}" download="{filename}" style="display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">📱 Download QR Code</a>'
    return href

# Smart Device Detection
def is_mobile_device():
    """Smart detection for mobile devices"""
    try:
        return False  # Default to desktop for now
    except:
        return False

# Authentication for staff
def staff_login():
    st.sidebar.title("🔐 Staff Portal")
    st.sidebar.markdown("---")
    
    username = st.sidebar.text_input("👤 Username")
    password = st.sidebar.text_input("🔒 Password", type="password")
    
    if st.sidebar.button("🚀 Login", type="primary", use_container_width=True):
        if username and password:
            cursor = db.conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_password))
            user = cursor.fetchone()
            
            if user:
                st.session_state.user = user
                st.session_state.logged_in = True
                st.session_state.role = user[3]
                st.sidebar.success(f"🎉 Welcome back, {user[1]}!")
                time.sleep(1)
                st.rerun()
            else:
                st.sidebar.error("❌ Invalid credentials")
        else:
            st.sidebar.warning("⚠️ Please enter both username and password")

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.current_step = "order_type"
    st.rerun()

# Initialize session state variables
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'current_step' not in st.session_state:
        st.session_state.current_step = "order_type"
    if 'order_type' not in st.session_state:
        st.session_state.order_type = "dine-in"
    if 'customer_name' not in st.session_state:
        st.session_state.customer_name = ""
    if 'table_number' not in st.session_state:
        st.session_state.table_number = 1
    if 'order_notes' not in st.session_state:
        st.session_state.order_notes = ""
    if 'payment_method' not in st.session_state:
        st.session_state.payment_method = "cash"
    if 'cart' not in st.session_state:
        st.session_state.cart = []
    if 'order_placed' not in st.session_state:
        st.session_state.order_placed = False
    if 'order_id' not in st.session_state:
        st.session_state.order_id = None
    if 'order_token' not in st.session_state:
        st.session_state.order_token = None
    if 'last_status_check' not in st.session_state:
        st.session_state.last_status_check = None
    if 'current_order_status' not in st.session_state:
        st.session_state.current_order_status = None
    # Tracking-specific session state
    if 'tracking_order_token' not in st.session_state:
        st.session_state.tracking_order_token = None
    if 'tracking_order_placed' not in st.session_state:
        st.session_state.tracking_order_placed = False
    if 'mobile_mode' not in st.session_state:
        st.session_state.mobile_mode = is_mobile_device()
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "home"
    # Auto-refresh for kitchen
    if 'last_order_check' not in st.session_state:
        st.session_state.last_order_check = time.time()

# Customer Ordering Interface
def customer_ordering():
    st.markdown("""
    <style>
    .order-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .menu-item-image {
        border-radius: 10px;
        object-fit: cover;
        width: 100%;
        height: 200px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="order-header"><h1>🍽️ Place Your Order</h1><p>Delicious food and drinks at great prices</p></div>', unsafe_allow_html=True)
    
    # Initialize session state
    init_session_state()
    
    # Step 1: Order Type Selection
    if st.session_state.current_step == "order_type":
        show_order_type_selection()
    
    # Step 2: Customer Information
    elif st.session_state.current_step == "customer_info":
        show_customer_info()
    
    # Step 3: Menu Selection
    elif st.session_state.current_step == "menu":
        show_menu_selection()
    
    # Step 4: Order Confirmation
    elif st.session_state.current_step == "confirmation":
        show_order_confirmation()
    
    # Step 5: Order Tracking
    elif st.session_state.current_step == "tracking":
        track_order()

def show_order_type_selection():
    st.subheader("🎯 Choose Your Experience")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        try:
            st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3", 
                    use_container_width=True, caption="Dine In Experience")
        except:
            st.markdown("""
            <div style="background: linear-gradient(45deg, #f0f0f0, #e0e0e0); border-radius: 10px; 
                        height: 150px; display: flex; align-items: center; justify-content: center;">
                <h3>🏠 Dine In</h3>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("🏠 **Dine In**", use_container_width=True, key="dine_in_btn"):
            st.session_state.order_type = "dine-in"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("Enjoy our cozy atmosphere")
    
    with col2:
        try:
            st.image("https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?ixlib=rb-4.0.3", 
                    use_container_width=True, caption="Takeaway Experience")
        except:
            st.markdown("""
            <div style="background: linear-gradient(45deg, #f0f0f0, #e0e0e0); border-radius: 10px; 
                        height: 150px; display: flex; align-items: center; justify-content: center;">
                <h3>🥡 Takeaway</h3>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("🥡 **Takeaway**", use_container_width=True, key="takeaway_btn"):
            st.session_state.order_type = "takeaway"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("Pick up and enjoy elsewhere")
    
    with col3:
        try:
            st.image("https://images.unsplash.com/photo-1504674900247-0877df9cc836?ixlib=rb-4.0.3", 
                    use_container_width=True, caption="Delivery Experience")
        except:
            st.markdown("""
            <div style="background: linear-gradient(45deg, #f0f0f0, #e0e0e0); border-radius: 10px; 
                        height: 150px; display: flex; align-items: center; justify-content: center;">
                <h3>🚚 Delivery</h3>
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("🚚 **Delivery**", use_container_width=True, key="delivery_btn"):
            st.session_state.order_type = "delivery"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("We bring it to your door")

def show_customer_info():
    st.subheader("👤 Customer Information")
    
    with st.form("customer_info_form"):
        customer_name = st.text_input(
            "**Your Name**", 
            value=st.session_state.customer_name,
            placeholder="Enter your full name",
            key="customer_name_input"
        )
        
        if st.session_state.order_type == "dine-in":
            table_number = st.number_input(
                "**Table Number**", 
                min_value=1, 
                max_value=50, 
                value=st.session_state.table_number,
                key="table_number_input"
            )
        else:
            table_number = None
        
        order_notes = st.text_area(
            "**Special Instructions**", 
            value=st.session_state.order_notes,
            placeholder="Any allergies, dietary restrictions, or special requests...",
            key="order_notes_input",
            height=100
        )
        
        # Payment method selection
        payment_method = st.radio(
            "**Payment Method**",
            ["💵 Cash", "💳 Card"],
            key="payment_method_input"
        )
        st.session_state.payment_method = "cash" if payment_method == "💵 Cash" else "card"
        
        submitted = st.form_submit_button("🚀 Continue to Menu", type="primary")
        
        if submitted:
            if not customer_name:
                st.error("👋 Please provide your name")
            else:
                # Store in session state
                st.session_state.customer_name = customer_name
                st.session_state.table_number = table_number
                st.session_state.order_notes = order_notes
                st.session_state.current_step = "menu"
                st.rerun()

def show_menu_selection():
    st.markdown("""
    <style>
    .menu-item {
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: transform 0.2s;
    }
    .menu-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .fallback-image {
        background: linear-gradient(45deg, #f0f0f0, #e0e0e0);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 200px;
        color: #666;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.subheader("📋 Explore Our Menu")
    
    # Menu categories
    categories = ['All', 'Beverage', 'Main Course', 'Dessert', 'Starter']
    selected_category = st.selectbox("**Filter by Category**", categories, key="category_filter")
    
    # Get menu items
    try:
        menu_items = db.get_menu_items(None if selected_category == 'All' else selected_category)
    except:
        # Fallback if database error - use new menu items
        menu_items = [
            (1, 'Cappuccino', 'Freshly brewed coffee with steamed milk', 25, 'Beverage', 1, 'https://images.unsplash.com/photo-1561047029-3000c68339ca?ixlib=rb-4.0.3'),
            (2, 'Beef Burger', 'Classic beef burger with cheese and veggies', 65, 'Main Course', 1, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?ixlib=rb-4.0.3'),
            (3, 'Chocolate Cake', 'Rich chocolate cake with ganache', 35, 'Dessert', 1, 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?ixlib=rb-4.0.3'),
            (4, 'French Fries', 'Crispy golden fries', 25, 'Starter', 1, 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?ixlib=rb-4.0.3')
        ]
    
    # Display menu items
    for item in menu_items:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            try:
                if item[6] and item[6].startswith('http'):
                    st.image(item[6], use_container_width=True, caption=item[1])
                else:
                    st.markdown(f"""
                    <div class="fallback-image">
                        <div>
                            <h3>🍽️</h3>
                            <p>{item[1]}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            except:
                st.markdown(f"""
                <div class="fallback-image">
                    <div>
                        <h3>🍽️</h3>
                        <p>{item[1]}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="menu-item">
                <h3>{item[1]}</h3>
                <p style="color: #666;">{item[2]}</p>
                <h4 style="color: #e74c3c;">R {item[3]:.2f}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Quantity selector
            current_qty = next((cart_item['quantity'] for cart_item in st.session_state.cart if cart_item['id'] == item[0]), 0)
            
            col_a, col_b, col_c = st.columns([1, 2, 1])
            with col_a:
                if st.button("➖", key=f"dec_{item[0]}", use_container_width=True):
                    if current_qty > 0:
                        st.session_state.cart = [cart_item for cart_item in st.session_state.cart if cart_item['id'] != item[0]]
                        if current_qty > 1:
                            st.session_state.cart.append({
                                'id': item[0], 'name': item[1], 'price': item[3], 
                                'quantity': current_qty - 1
                            })
                        st.rerun()
            with col_b:
                st.markdown(f"<center><strong>{current_qty}</strong> in cart</center>", unsafe_allow_html=True)
            with col_c:
                if st.button("➕", key=f"inc_{item[0]}", use_container_width=True):
                    existing_item = next((cart_item for cart_item in st.session_state.cart if cart_item['id'] == item[0]), None)
                    if existing_item:
                        existing_item['quantity'] += 1
                    else:
                        st.session_state.cart.append({
                            'id': item[0], 'name': item[1], 'price': item[3], 
                            'quantity': 1
                        })
                    st.rerun()
    
    # Cart summary
    if st.session_state.cart:
        st.markdown("---")
        st.subheader("🛒 Your Order")
        
        total_amount = 0
        for item in st.session_state.cart:
            item_total = item['price'] * item['quantity']
            total_amount += item_total
            st.write(f"• {item['name']} x{item['quantity']} - R {item_total:.2f}")
        
        st.markdown(f"**Total: R {total_amount:.2f}**")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.current_step = "customer_info"
                st.rerun()
        with col2:
            if st.button("🚀 Continue to Checkout", type="primary", use_container_width=True):
                if st.session_state.cart:
                    st.session_state.current_step = "confirmation"
                    st.rerun()
                else:
                    st.error("🛒 Please add items to your cart first")
    else:
        st.info("🛒 Your cart is empty. Add some delicious items!")

def show_order_confirmation():
    st.subheader("✅ Order Confirmation")
    
    # Display order summary
    st.markdown("### 📋 Order Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Customer:** {st.session_state.customer_name}")
        st.markdown(f"**Order Type:** {st.session_state.order_type.replace('-', ' ').title()}")
        if st.session_state.order_type == "dine-in":
            st.markdown(f"**Table:** {st.session_state.table_number}")
        st.markdown(f"**Payment:** {st.session_state.payment_method.title()}")
    
    with col2:
        st.markdown(f"**Special Instructions:**")
        st.markdown(f"_{st.session_state.order_notes or 'None'}_")
    
    st.markdown("### 🛒 Order Items")
    total_amount = 0
    for item in st.session_state.cart:
        item_total = item['price'] * item['quantity']
        total_amount += item_total
        st.markdown(f"- **{item['name']}** x{item['quantity']} - R {item_total:.2f}")
    
    st.markdown(f"### 💰 **Total Amount: R {total_amount:.2f}**")
    
    st.markdown("---")
    
    # Final confirmation
    st.markdown("### 🚀 Ready to Place Your Order?")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("⬅️ Back to Menu", use_container_width=True):
            st.session_state.current_step = "menu"
            st.rerun()
    
    with col2:
        if st.button("✅ Place Order Now", type="primary", use_container_width=True):
            try:
                # Prepare items for database
                order_items = []
                for cart_item in st.session_state.cart:
                    order_items.append({
                        'id': cart_item['id'],
                        'name': cart_item['name'],
                        'price': cart_item['price'],
                        'quantity': cart_item['quantity']
                    })
                
                # Add order to database
                order_id, order_token = db.add_order(
                    customer_name=st.session_state.customer_name,
                    order_type=st.session_state.order_type,
                    table_number=st.session_state.table_number,
                    items=order_items,
                    notes=st.session_state.order_notes,
                    payment_method=st.session_state.payment_method
                )
                
                if order_id and order_token:
                    st.session_state.order_id = order_id
                    st.session_state.order_token = order_token
                    st.session_state.order_placed = True
                    st.session_state.current_step = "tracking"
                    
                    # Clear cart after successful order
                    st.session_state.cart = []
                    
                    st.success(f"🎉 Order placed successfully! Your order token is: **{order_token}**")
                    st.rerun()
                else:
                    st.error("❌ Failed to place order. Please try again.")
                    
            except Exception as e:
                st.error(f"❌ Error placing order: {str(e)}")
                st.error("Please try again or contact our friendly staff for assistance.")

def track_order():
    st.subheader("📱 Track Your Order")
    
    if st.session_state.order_placed and st.session_state.order_token:
        # User just placed an order - track that order
        order_token = st.session_state.order_token
        st.success(f"🔍 Tracking your order with token: **{order_token}**")
    else:
        # User wants to track existing order
        order_token = st.text_input(
            "Enter your order token:",
            placeholder="e.g., ORD12345678",
            key="tracking_token_input"
        )
    
    if order_token:
        try:
            order = db.get_order_by_token(order_token)
            
            if order:
                # Display order information
                st.markdown("### 📋 Order Details")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Order Token:** `{order_token}`")
                    st.markdown(f"**Customer:** {order[2]}")
                    st.markdown(f"**Order Type:** {order[3].replace('-', ' ').title()}")
                    if order[4]:  # table number
                        st.markdown(f"**Table:** {order[4]}")
                
                with col2:
                    st.markdown(f"**Status:** **{order[5].title()}**")
                    st.markdown(f"**Total:** R {order[6]:.2f}")
                    st.markdown(f"**Order Date:** {order[7]}")
                    st.markdown(f"**Payment:** {order[11].title()}")
                
                # Status timeline
                st.markdown("### 📊 Order Status")
                statuses = ['pending', 'confirmed', 'preparing', 'ready', 'completed']
                current_status = order[5]
                
                # Create visual status indicator
                cols = st.columns(len(statuses))
                for i, status in enumerate(statuses):
                    with cols[i]:
                        if status == current_status:
                            st.markdown(f"🔵 **{status.title()}**")
                        elif statuses.index(status) < statuses.index(current_status):
                            st.markdown(f"✅ {status.title()}")
                        else:
                            st.markdown(f"⚪ {status.title()}")
                
                # Estimated wait time
                if current_status in ['pending', 'confirmed', 'preparing']:
                    st.info(f"⏱️ Estimated wait time: {order[8]} minutes")
                
                # Auto-refresh
                st.markdown("---")
                st.caption("🔄 Status updates automatically every 30 seconds")
                
                # Add manual refresh button
                if st.button("🔄 Refresh Status", key="refresh_status"):
                    st.rerun()
                
            else:
                st.error("❌ Order not found. Please check your order token.")
                st.info("💡 Don't have an order token? Place a new order to get one!")
                
        except Exception as e:
            st.error(f"❌ Error retrieving order: {str(e)}")
    
    # Option to place new order
    st.markdown("---")
    if st.button("🍽️ Place New Order", type="primary"):
        # Reset session state for new order
        st.session_state.current_step = "order_type"
        st.session_state.order_placed = False
        st.session_state.order_id = None
        st.session_state.order_token = None
        st.session_state.cart = []
        st.rerun()

# Kitchen Management
def kitchen_management():
    st.title("👨‍🍳 Kitchen Dashboard")
    
    # Auto-refresh every 30 seconds
    if time.time() - st.session_state.last_order_check > 30:
        st.session_state.last_order_check = time.time()
        st.rerun()
    
    # Get active orders
    try:
        orders = db.get_active_orders()
    except Exception as e:
        st.error(f"Error fetching orders: {e}")
        orders = []
    
    if not orders:
        st.success("🎉 All caught up! No active orders.")
        return
    
    # Display orders by status
    status_groups = {}
    for order in orders:
        status = order[5]
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(order)
    
    # Create columns for each status
    cols = st.columns(len(status_groups))
    
    for idx, (status, status_orders) in enumerate(status_groups.items()):
        with cols[idx]:
            st.subheader(f"{status.title()} ({len(status_orders)})")
            
            for order in status_orders:
                with st.expander(f"Order #{order[0]} - {order[2]}", expanded=True):
                    st.write(f"**Token:** {order[9]}")
                    st.write(f"**Type:** {order[3]}")
                    if order[4]:
                        st.write(f"**Table:** {order[4]}")
                    st.write(f"**Items:** {order[12]}")
                    st.write(f"**Total:** R {order[6]:.2f}")
                    st.write(f"**Time:** {order[7]}")
                    
                    if order[10]:  # notes
                        st.write(f"**Notes:** {order[10]}")
                    
                    # Status update buttons
                    if status == 'pending':
                        if st.button("✅ Confirm", key=f"confirm_{order[0]}"):
                            db.update_order_status(order[0], 'confirmed', 'Order confirmed by kitchen')
                            st.rerun()
                    elif status == 'confirmed':
                        if st.button("👨‍🍳 Start Prep", key=f"prep_{order[0]}"):
                            db.update_order_status(order[0], 'preparing', 'Food preparation started')
                            st.rerun()
                    elif status == 'preparing':
                        if st.button("✅ Ready", key=f"ready_{order[0]}"):
                            db.update_order_status(order[0], 'ready', 'Order ready for pickup/delivery')
                            st.rerun()
                    elif status == 'ready':
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Complete", key=f"complete_{order[0]}"):
                                db.update_order_status(order[0], 'completed', 'Order completed')
                                st.rerun()
                        with col2:
                            if st.button("🚚 Collected", key=f"collected_{order[0]}"):
                                db.update_order_status(order[0], 'collected', 'Order collected by customer')
                                st.rerun()

# Analytics Dashboard
def analytics_dashboard():
    st.title("📊 Analytics Dashboard")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        days = st.selectbox("Time Period", [7, 30, 90], index=1, key="analytics_days")
    
    # Get analytics data
    analytics_data = db.get_real_analytics(days)
    
    if not analytics_data:
        st.error("No analytics data available")
        return
    
    # Key metrics
    st.subheader("📈 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Orders", analytics_data['totals'][0])
    with col2:
        st.metric("Total Revenue", f"R {analytics_data['totals'][1]:.2f}")
    with col3:
        st.metric("Avg Order Value", f"R {analytics_data['totals'][2]:.2f}")
    with col4:
        st.metric("Today's Orders", db.get_todays_orders_count())
    
    # Revenue trend
    st.subheader("💰 Revenue Trend")
    if analytics_data['daily_trend']:
        df_daily = pd.DataFrame(analytics_data['daily_trend'], columns=['Date', 'Orders', 'Revenue'])
        fig = px.line(df_daily, x='Date', y='Revenue', title='Daily Revenue')
        st.plotly_chart(fig, use_container_width=True)
    
    # Popular dishes
    st.subheader("🍽️ Popular Dishes")
    if analytics_data['popular_dishes']:
        df_popular = pd.DataFrame(analytics_data['popular_dishes'], 
                                columns=['Dish', 'Quantity', 'Revenue', 'Orders'])
        fig = px.bar(df_popular.head(8), x='Dish', y='Quantity', title='Top Selling Items')
        st.plotly_chart(fig, use_container_width=True)
    
    # Category distribution
    st.subheader("📦 Category Distribution")
    if analytics_data['category_distribution']:
        df_cat = pd.DataFrame(analytics_data['category_distribution'],
                            columns=['Category', 'Quantity', 'Revenue', 'Orders'])
        fig = px.pie(df_cat, values='Quantity', names='Category', title='Sales by Category')
        st.plotly_chart(fig, use_container_width=True)

# Staff Management
def staff_management():
    st.title("👥 Staff Management")
    
    # Add new staff member
    st.subheader("➕ Add New Staff Member")
    with st.form("add_staff_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Username")
            new_role = st.selectbox("Role", ["staff", "chef", "admin"])
        with col2:
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.form_submit_button("Add Staff Member", type="primary"):
            if new_password == confirm_password:
                try:
                    cursor = db.conn.cursor()
                    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                    cursor.execute('''
                        INSERT INTO users (username, password, role) 
                        VALUES (?, ?, ?)
                    ''', (new_username, hashed_password, new_role))
                    db.conn.commit()
                    st.success(f"Staff member {new_username} added successfully!")
                except sqlite3.IntegrityError:
                    st.error("Username already exists")
                except Exception as e:
                    st.error(f"Error adding staff: {e}")
            else:
                st.error("Passwords do not match")
    
    # Current staff list
    st.subheader("📋 Current Staff")
    try:
        cursor = db.conn.cursor()
        cursor.execute('SELECT id, username, role, created_at FROM users ORDER BY created_at DESC')
        staff = cursor.fetchall()
        
        for member in staff:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{member[1]}** ({member[2]})")
            with col2:
                st.write(f"Added: {member[3][:10]}")
            with col3:
                if st.button("Remove", key=f"remove_{member[0]}"):
                    cursor.execute('DELETE FROM users WHERE id = ?', (member[0],))
                    db.conn.commit()
                    st.rerun()
    except Exception as e:
        st.error(f"Error fetching staff: {e}")

# Main Application
def main():
    # Initialize session state
    init_session_state()
    
    # Set page config
    st.set_page_config(
        page_title="Sanele Restaurant Ordering",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton button {
        border-radius: 10px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">🍽️ Sanele Restaurant Ordering System</h1>', unsafe_allow_html=True)
    
    # Sidebar for navigation and authentication
    with st.sidebar:
        st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3", 
                use_container_width=True, caption="Welcome to Sanele Restaurant")
        
        if st.session_state.logged_in:
            st.success(f"👋 Welcome, {st.session_state.user[1]}!")
            
            # Navigation for staff
            st.subheader("🧭 Navigation")
            
            pages = ["🏠 Customer Ordering"]
            if st.session_state.role in ['admin', 'chef']:
                pages.extend(["👨‍🍳 Kitchen Management", "📊 Analytics"])
            if st.session_state.role == 'admin':
                pages.append("👥 Staff Management")
            
            selected_page = st.radio("Go to", pages, key="nav_radio")
            
            # Logout button
            if st.button("🚪 Logout", use_container_width=True):
                logout()
            
            # Set current page based on selection
            if selected_page == "🏠 Customer Ordering":
                st.session_state.current_page = "home"
            elif selected_page == "👨‍🍳 Kitchen Management":
                st.session_state.current_page = "kitchen"
            elif selected_page == "📊 Analytics":
                st.session_state.current_page = "analytics"
            elif selected_page == "👥 Staff Management":
                st.session_state.current_page = "staff"
        
        else:
            # Show login form for staff
            staff_login()
            
            # QR Code for mobile ordering
            st.markdown("---")
            st.subheader("📱 Mobile Ordering")
            
            # Generate QR code for the current URL
            try:
                # Get the current URL (approximation for Streamlit Cloud)
                qr_url = "https://sanele-restaurant-ordering.streamlit.app"
                qr_img = generate_qr_code(qr_url)
                
                st.image(f"data:image/png;base64,{qr_img}", 
                        caption="Scan to order from your phone", 
                        use_container_width=True)
                
                st.markdown(get_qr_download_link(qr_img), unsafe_allow_html=True)
            except:
                st.info("📱 Mobile ordering QR code will appear here")
    
    # Main content area
    if not st.session_state.logged_in:
        # Customer interface (default)
        customer_ordering()
    else:
        # Staff interfaces
        if st.session_state.current_page == "home":
            customer_ordering()
        elif st.session_state.current_page == "kitchen":
            kitchen_management()
        elif st.session_state.current_page == "analytics":
            analytics_dashboard()
        elif st.session_state.current_page == "staff":
            staff_management()

if __name__ == "__main__":
    main()