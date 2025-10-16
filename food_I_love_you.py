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
        
        # Clear existing menu items and insert new South African menu
        cursor.execute('DELETE FROM menu_items')
        
        # FIXED: Using only reliable Unsplash image URLs
        south_african_menu = [
            # STARTERS
            ('Biltong Platter', 'Traditional dried cured meat with droewors', 65, 'Starter', 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Chakalaka & Pap', 'Spicy vegetable relish with maize meal', 45, 'Starter', 'https://images.unsplash.com/photo-1565299507177-b0ac66763828?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Samoosas', 'Triangular pastry with spiced filling', 35, 'Starter', 'https://images.unsplash.com/photo-1603100055781-cab7adf375b1?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),

            # MAIN COURSES
            ('Braai Platter for 2', 'Mixed grill with boerewors, lamb chops, chicken', 195, 'Main Course', 'https://images.unsplash.com/photo-1555939597-9c0a8be1e74e?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Bobotie with Rice', 'Spiced minced meat baked with egg topping', 89, 'Main Course', 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Bunny Chow', 'Hollowed bread filled with curry of your choice', 75, 'Main Course', 'https://images.unsplash.com/photo-1565299588453-b8ec840b7c7e?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Pap & Wors', 'Maize meal porridge with boerewors', 65, 'Main Course', 'https://images.unsplash.com/photo-1563379926898-05f4575a45d8?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Potjiekos', 'Traditional slow-cooked stew in cast iron pot', 125, 'Main Course', 'https://images.unsplash.com/photo-1551024506-0bccd828d307?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Samp & Beans', 'Traditional maize and sugar bean dish', 55, 'Main Course', 'https://images.unsplash.com/photo-1512058564366-18510be2db19?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Boerewors Roll', 'Traditional sausage in fresh roll with chakalaka', 45, 'Main Course', 'https://images.unsplash.com/photo-1550317138-10000687a72b?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Vetkoek with Mince', 'Fried dough bread filled with savoury mince', 50, 'Main Course', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),

            # DESSERTS
            ('Melktert', 'Traditional milk tart with cinnamon', 35, 'Dessert', 'https://images.unsplash.com/photo-1563729784474-d77dbb933a9e?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Koeksisters', 'Sweet syrupy plaited doughnuts', 25, 'Dessert', 'https://images.unsplash.com/photo-1555507036-ab794f27d2e9?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Malva Pudding', 'Sweet apricot pudding with custard', 40, 'Dessert', 'https://images.unsplash.com/photo-1565958011703-44f9829ba187?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),

            # BEVERAGES
            ('Rooibos Tea', 'Traditional South African herbal tea', 20, 'Beverage', 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Amarula Cream', 'Cream liqueur with marula fruit', 35, 'Beverage', 'https://images.unsplash.com/photo-1470337458703-46ad1756a187?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Coke/Fanta/Sprite', 'Cold soft drinks', 18, 'Beverage', 'https://images.unsplash.com/photo-1622483767028-3f66f32aef97?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            ('Still Water', '500ml bottled water', 15, 'Beverage', 'https://images.unsplash.com/photo-1548839149-851a5d7d3f6a?ixlib=rb-4.0.3&w=400&h=300&fit=crop')
        ]
        
        for item in south_african_menu:
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
                WHERE order_date >= date('now', '-' || ? || ' days')
            ''', (days,))
            totals = cursor.fetchone()
            
            # Daily revenue trend
            cursor.execute('''
                SELECT 
                    date(order_date) as order_day,
                    COUNT(*) as daily_orders,
                    COALESCE(SUM(total_amount), 0) as daily_revenue
                FROM orders 
                WHERE order_date >= date('now', '-' || ? || ' days')
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
                WHERE order_date >= date('now', '-' || ? || ' days')
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
                WHERE o.order_date >= date('now', '-' || ? || ' days')
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
                WHERE o.order_date >= date('now', '-' || ? || ' days')
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
                WHERE order_date >= date('now', '-' || ? || ' days')
                GROUP BY payment_method
            ''', (days,))
            payment_distribution = cursor.fetchall()
            
            return {
                'totals': totals,
                'daily_trend': daily_data,
                'hourly_data': hourly_data,
                'popular_dishes': popular_dishes,
                'category_distribution': category_distribution,
                'payment_distribution': payment_distribution
            }
            
        except Exception as e:
            st.error(f"Error in get_real_analytics: {e}")
            return None
    
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
        
        cursor.execute('''
            INSERT INTO orders (customer_name, order_type, table_number, total_amount, notes, order_token, order_date, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_name, order_type, table_number, total_amount, notes, order_token, current_time, payment_method))
        
        order_id = cursor.lastrowid
        
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
        return order_id, order_token
    
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
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT o.*, 
                   GROUP_CONCAT(oi.menu_item_name || ' (x' || oi.quantity || ')', ', ') as items,
                   COUNT(oi.id) as item_count,
                   o.notes as order_notes
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.order_token = ?
            GROUP BY o.id
        ''', (order_token,))
        return cursor.fetchone()
    
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
        cursor.execute('''
            SELECT status FROM orders WHERE order_token = ?
        ''', (order_token,))
        result = cursor.fetchone()
        return result[0] if result else None

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
    
    st.markdown('<div class="order-header"><h1>🍽️ Place Your Order</h1><p>Authentic South African cuisine at great prices</p></div>', unsafe_allow_html=True)
    
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
        # FIXED: Using reliable Unsplash image
        st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3&w=300&h=200&fit=crop", use_container_width=True)
        if st.button("🏠 **Dine In**", use_container_width=True, key="dine_in_btn"):
            st.session_state.order_type = "dine-in"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("Enjoy our cozy atmosphere")
    
    with col2:
        # FIXED: Using reliable Unsplash image
        st.image("https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?ixlib=rb-4.0.3&w=300&h=200&fit=crop", use_container_width=True)
        if st.button("🥡 **Takeaway**", use_container_width=True, key="takeaway_btn"):
            st.session_state.order_type = "takeaway"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("Pick up and enjoy elsewhere")
    
    with col3:
        # FIXED: Using reliable Unsplash image
        st.image("https://images.unsplash.com/photo-1504674900247-0877df9cc836?ixlib=rb-4.0.3&w=300&h=200&fit=crop", use_container_width=True)
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
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.subheader("📋 Explore Our South African Menu")
    
    # Menu categories
    categories = ['All', 'Starter', 'Main Course', 'Dessert', 'Beverage']
    selected_category = st.selectbox("**Filter by Category**", categories, key="category_filter")
    
    # Get menu items
    try:
        menu_items = db.get_menu_items(None if selected_category == 'All' else selected_category)
    except:
        # Fallback if database error - use new menu items
        menu_items = [
            (1, 'Biltong Platter', 'Traditional dried cured meat with droewors', 65, 'Starter', 1, 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            (2, 'Braai Platter for 2', 'Mixed grill with boerewors, lamb chops, chicken', 195, 'Main Course', 1, 'https://images.unsplash.com/photo-1555939597-9c0a8be1e74e?ixlib=rb-4.0.3&w=400&h=300&fit=crop'),
            (3, 'Bobotie with Rice', 'Spiced minced meat baked with egg topping', 89, 'Main Course', 1, 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?ixlib=rb-4.0.3&w=400&h=300&fit=crop')
        ]
    
    # Display menu items
    for item in menu_items:
        with st.container():
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Display food image with fallback
                image_url = item[6] if len(item) > 6 and item[6] else None
                if image_url:
                    try:
                        st.image(image_url, use_container_width=True, caption="")
                    except:
                        st.markdown(f'<div class="fallback-image">🍽️ {item[1]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="fallback-image">🍽️ {item[1]}</div>', unsafe_allow_html=True)
            
            with col2:
                st.subheader(f"🍽️ {item[1]}")
                st.write(f"_{item[2]}_")
                st.write(f"**💰 R {item[3]}**")
                
                # Quantity and add to cart
                col_a, col_b, col_c = st.columns([1, 2, 1])
                with col_a:
                    quantity = st.number_input("Qty", min_value=0, max_value=10, key=f"qty_{item[0]}")
                with col_b:
                    instructions = st.text_input("Special requests", key=f"inst_{item[0]}", placeholder="e.g., no onions, extra sauce")
                with col_c:
                    if quantity > 0:
                        if st.button("**+ Add**", key=f"add_{item[0]}"):
                            cart_item = {
                                'id': item[0],
                                'name': item[1],
                                'price': item[3],
                                'quantity': quantity,
                                'instructions': instructions
                            }
                            st.session_state.cart.append(cart_item)
                            st.success(f"✅ Added {quantity} x {item[1]} to cart!")
                            st.rerun()
    
    # Display cart and navigation
    show_cart_and_navigation()

def show_cart_and_navigation():
    if st.session_state.cart:
        st.markdown("---")
        st.subheader("🛒 Your Order Summary")
        
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
                if st.button("❌", key=f"remove_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            total += item['price'] * item['quantity']
        
        st.markdown(f"### 💰 Total: R {total}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Info", use_container_width=True):
                st.session_state.current_step = "customer_info"
                st.rerun()
        
        with col2:
            if st.button("📦 **Place Order**", type="primary", use_container_width=True):
                st.session_state.current_step = "confirmation"
                st.rerun()
    else:
        if st.button("← Back to Customer Info"):
            st.session_state.current_step = "customer_info"
            st.rerun()

def show_order_confirmation():
    st.markdown("""
    <style>
    .confirmation-box {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        border-left: 5px solid #28a745;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("✅ Order Confirmation")
    
    with st.container():
        st.markdown('<div class="confirmation-box">', unsafe_allow_html=True)
        
        # Display order summary
        st.subheader("📋 Order Summary")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**👤 Customer:** {st.session_state.customer_name}")
            st.write(f"**🎯 Order Type:** {st.session_state.order_type.title()}")
            st.write(f"**💳 Payment:** {st.session_state.payment_method.title()}")
        
        with col2:
            if st.session_state.order_type == "dine-in":
                st.write(f"**🪑 Table:** {st.session_state.table_number}")
            if st.session_state.order_notes:
                st.write(f"**📝 Notes:** {st.session_state.order_notes}")
        
        st.subheader("🍽️ Order Items")
        total = 0
        item_count = 0
        for item in st.session_state.cart:
            item_total = item['price'] * item['quantity']
            total += item_total
            item_count += item['quantity']
            st.write(f"• **{item['quantity']}x {item['name']}** - R {item_total}")
            if item['instructions']:
                st.caption(f"  _📝 {item['instructions']}_")
        
        st.markdown(f"### 💰 **Total Amount: R {total}**")
        st.markdown(f"**📦 Total Items: {item_count}**")
        st.markdown(f"**🕒 Order Time: {get_sa_time().strftime('%Y-%m-%d %H:%M:%S')} SAST**")
        st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Menu", use_container_width=True):
            st.session_state.current_step = "menu"
            st.rerun()
    
    with col2:
        if st.button("🚀 **Confirm & Place Order**", type="primary", use_container_width=True):
            try:
                # Save order to database
                order_id, order_token = db.add_order(
                    st.session_state.customer_name,
                    st.session_state.order_type,
                    st.session_state.cart,
                    st.session_state.table_number,
                    st.session_state.order_notes,
                    st.session_state.payment_method
                )
                
                st.session_state.order_placed = True
                st.session_state.order_id = order_id
                st.session_state.order_token = order_token
                st.session_state.current_order_status = 'pending'
                
                # Clear cart after successful order
                st.session_state.cart = []
                
                st.session_state.current_step = "tracking"
                st.balloons()
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error placing order: {e}")
                st.error("Please try again or contact our friendly staff for assistance.")

def track_order():
    st.markdown("""
    <style>
    .tracking-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="tracking-header"><h1>📱 Track Your Order</h1><p>Watch your meal being prepared in real-time</p></div>', unsafe_allow_html=True)
    
    # Initialize session state for tracking
    if 'tracking_order_token' not in st.session_state:
        st.session_state.tracking_order_token = None
    if 'tracking_order_placed' not in st.session_state:
        st.session_state.tracking_order_placed = False
    
    # Check if we have an active order from the ordering flow
    if st.session_state.get('order_placed') and st.session_state.get('order_token'):
        order_token = st.session_state.order_token
        st.session_state.tracking_order_token = order_token
        st.session_state.tracking_order_placed = True
        display_order_tracking(order_token)
    elif st.session_state.tracking_order_placed and st.session_state.tracking_order_token:
        # Use the stored tracking token
        display_order_tracking(st.session_state.tracking_order_token)
    else:
        # Allow manual order token entry
        st.info("🔍 **Enter your Order Token to track your order status**")
        order_token = st.text_input("Order Token", placeholder="ORD123456789", key="track_order_input")
        
        if st.button("🔍 Track Order", type="primary", key="track_order_btn"):
            if order_token:
                st.session_state.tracking_order_token = order_token
                st.session_state.tracking_order_placed = True
                st.rerun()
            else:
                st.error("❌ Please enter your order token")

def display_order_tracking(order_token):
    try:
        # Get current order status for live updates
        current_status = db.get_order_status(order_token)
        
        # If order is collected/completed, show completion message and stop tracking
        if current_status in ['completed', 'collected']:
            st.success("🎉 **Your order has been completed! Thank you for dining with us!**")
            st.balloons()
            st.info("💫 We hope you enjoyed your South African culinary experience!")
            return
        
        if not current_status:
            st.error("❌ Order not found. Please check your Order Token.")
            st.info("💡 Make sure you entered the correct Order Token from your order confirmation.")
            return
        
        # Update session state with current status for comparison
        previous_status = st.session_state.get('current_order_status')
        if current_status != previous_status:
            st.session_state.current_order_status = current_status
            # Force a rerun when status changes
            st.rerun()
        
        # Get full order details
        order = db.get_order_by_token(order_token)
        
        if order:
            # Status configuration
            status_config = {
                'pending': {'emoji': '⏳', 'color': '#FFA500', 'name': 'Order Received', 'description': 'We have received your order'},
                'preparing': {'emoji': '👨‍🍳', 'color': '#1E90FF', 'name': 'Preparing', 'description': 'Our chefs are cooking your meal'},
                'ready': {'emoji': '✅', 'color': '#32CD32', 'name': 'Ready', 'description': 'Your order is ready!'},
                'completed': {'emoji': '🎉', 'color': '#008000', 'name': 'Completed', 'description': 'Order completed successfully'},
                'collected': {'emoji': '📦', 'color': '#4B0082', 'name': 'Collected', 'description': 'Order has been collected'}
            }
            
            current_status_info = status_config.get(current_status, status_config['pending'])
            
            # Display real-time status header
            st.markdown(f"""
            <div style="background-color: {current_status_info['color']}; color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem;">
                <h1 style="margin: 0; font-size: 2.5rem;">{current_status_info['emoji']}</h1>
                <h2 style="margin: 10px 0; color: white;">{current_status_info['name']}</h2>
                <p style="margin: 0; font-size: 1.2rem; opacity: 0.9;">{current_status_info['description']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Order details
            st.subheader("📋 Order Details")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**📄 Order ID:** {order[0]}")
                st.write(f"**👤 Customer:** {order[2]}")
                st.write(f"**🎯 Order Type:** {str(order[4]).title() if order[4] else 'N/A'}")
                st.write(f"**💳 Payment:** {str(order[10]).title() if len(order) > 10 and order[10] else 'Cash'}")
            with col2:
                st.write(f"**💰 Total:** R {order[6]}")
                st.write(f"**📅 Order Date:** {order[7]} SAST")
                st.write(f"**📦 Items Ordered:** {order[11] if len(order) > 11 else '0'}")
                if len(order) > 9 and order[9]:
                    st.write(f"**📝 Notes:** {order[9]}")
            
            # Enhanced Real-time Progress Tracker
            st.subheader("🔄 Order Progress")
            
            # Define status flow based on order type
            if str(order[4]) == 'takeaway':
                status_flow = ['pending', 'preparing', 'ready', 'collected']
                status_names = ['Order Received', 'Preparing', 'Ready for Collection', 'Collected']
            else:
                status_flow = ['pending', 'preparing', 'ready', 'completed']
                status_names = ['Order Received', 'Preparing', 'Ready', 'Completed']
            
            current_index = status_flow.index(current_status) if current_status in status_flow else 0
            
            # Progress bar with percentage
            progress = current_index / (len(status_flow) - 1) if len(status_flow) > 1 else 0
            st.progress(progress)
            st.write(f"**📊 Progress: {int(progress * 100)}%**")
            
            # Visual status steps
            cols = st.columns(len(status_flow))
            
            for i, (status, status_name) in enumerate(zip(status_flow, status_names)):
                status_info = status_config.get(status, status_config['pending'])
                
                with cols[i]:
                    if i < current_index:
                        # Completed step
                        st.markdown(f"""
                        <div style="text-align: center; padding: 15px; background: #4CAF50; color: white; border-radius: 10px; margin: 5px;">
                            <div style="font-size: 2rem;">✅</div>
                            <strong>{status_name}</strong>
                            <div style="font-size: 0.8rem; opacity: 0.9;">Completed</div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif i == current_index:
                        # Current step
                        st.markdown(f"""
                        <div style="text-align: center; padding: 15px; background: {status_info['color']}; color: white; border-radius: 10px; margin: 5px; border: 3px solid #FFD700;">
                            <div style="font-size: 2rem;">{status_info['emoji']}</div>
                            <strong>{status_name}</strong>
                            <div style="font-size: 0.8rem; opacity: 0.9;">In Progress</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Show estimated time for current step
                        if status == 'preparing':
                            st.info("⏱️ **Estimated time: 10-15 minutes**")
                        elif status == 'ready':
                            st.success("🎉 **Your order is ready!**")
                            st.balloons()
                    else:
                        # Future step
                        st.markdown(f"""
                        <div style="text-align: center; padding: 15px; background: #f0f0f0; color: #666; border-radius: 10px; margin: 5px;">
                            <div style="font-size: 2rem;">⏳</div>
                            <strong>{status_name}</strong>
                            <div style="font-size: 0.8rem; opacity: 0.9;">Upcoming</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Order items with detailed information
            st.subheader("🍽️ Your Order Items")
            if order[8] and isinstance(order[8], str):
                items = order[8].split(',')
                for item in items:
                    st.write(f"• {item.strip()}")
            else:
                st.write("No items found in this order")
            
            # Special collection button for takeaway
            order_type = str(order[4]) if order[4] else 'dine-in'
            if order_type == 'takeaway' and current_status == 'ready':
                st.success("🎯 **Your order is ready for collection!**")
                st.info("📍 Please come to the counter to collect your order")
                
                if st.button("📦 **I've Collected My Order**", type="primary", key="collect_btn"):
                    try:
                        db.update_order_status(order[0], 'collected', 'Customer collected order')
                        st.success("🎉 Thank you! Order marked as collected. Enjoy your meal! 🍽️")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error updating order: {e}")
            
            # Auto-refresh for live updates
            st.markdown("---")
            refresh_container = st.container()
            with refresh_container:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info("🔄 **Live Tracking Active** - Status updates automatically")
                    st.write(f"**Last checked:** {get_sa_time().strftime('%H:%M:%S')} SAST")
                with col2:
                    if st.button("🔄 Refresh Now", key="refresh_btn"):
                        st.rerun()
            
            # Auto-refresh every 3 seconds for real-time updates
            time.sleep(3)
            st.rerun()
                
        else:
            st.error("❌ Order not found. Please check your Order Token.")
            st.info("💡 Make sure you entered the correct Order Token from your order confirmation.")
            
    except Exception as e:
        st.error(f"❌ Error tracking order: {e}")
        st.info("🤝 If this problem persists, please contact our staff for assistance.")

# Enhanced Landing Page with proper dark/light mode support
def show_landing_page():
    st.markdown("""
    <style>
    .hero-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 4rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 3rem;
    }
    .feature-card {
        background: var(--background-color);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 1rem;
        border-left: 5px solid #667eea;
        transition: transform 0.3s ease;
        color: var(--text-color);
    }
    .feature-card:hover {
        transform: translateY(-5px);
    }
    .step-card {
        background: var(--background-color);
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 0.5rem;
        color: var(--text-color);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 3.5rem; margin-bottom: 1rem;">🍽️ Taste of South Africa</h1>
        <p style="font-size: 1.5rem; margin-bottom: 2rem; opacity: 0.9;">Authentic South African Cuisine Experience</p>
        <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
            <div style="background: rgba(255,255,255,0.2); padding: 1rem 2rem; border-radius: 25px; backdrop-filter: blur(10px);">
                🍕 Fresh Local Ingredients
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 1rem 2rem; border-radius: 25px; backdrop-filter: blur(10px);">
                👨‍🍳 Traditional Recipes
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 1rem 2rem; border-radius: 25px; backdrop-filter: blur(10px);">
                ⚡ Quick Service
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Call to Action
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        ## 🎯 Experience True South African Taste
        
        Authentic South African flavors with traditional recipes and affordable prices.
        
        **🌟 Traditional Recipes** - Passed down through generations  
        **⚡ Lightning Fast** - Average 15-minute preparation  
        **📱 Live Tracking** - Watch your order in real-time  
        **💖 Customer First** - Your satisfaction is our priority
        """)
        
        if st.button("🚀 Start Your Order Now", type="primary", use_container_width=True):
            st.session_state.current_step = "order_type"
            st.session_state.current_page = "order"
            st.rerun()
    
    with col2:
        # FIXED: Using reliable Unsplash image
        st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3&w=400", 
                use_container_width=True, caption="Our Beautiful Restaurant")
    
    # Features Grid
    st.markdown("---")
    st.subheader("🌟 What Makes Us Special")
    
    features = st.columns(3)
    
    with features[0]:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 3rem;">🍽️</div>
            <h3>Authentic Taste</h3>
            <p>Traditional South African recipes with authentic flavors and ingredients</p>
        </div>
        """, unsafe_allow_html=True)
    
    with features[1]:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 3rem;">⚡</div>
            <h3>Lightning Fast</h3>
            <p>Average preparation time of just 15 minutes. Your hunger won't wait!</p>
        </div>
        """, unsafe_allow_html=True)
    
    with features[2]:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 3rem;">📱</div>
            <h3>Live Tracking</h3>
            <p>Watch your order being prepared in real-time. No more guessing!</p>
        </div>
        """, unsafe_allow_html=True)
    
    # How It Works
    st.markdown("---")
    st.subheader("🚀 How It Works")
    
    steps = st.columns(4)
    
    step_data = [
        {"icon": "📱", "title": "Scan & Order", "desc": "Use your phone to browse our menu"},
        {"icon": "🛒", "title": "Add Items", "desc": "Select your favorite dishes"},
        {"icon": "👨‍🍳", "title": "We Prepare", "desc": "Our chefs cook with passion"},
        {"icon": "🎯", "title": "Enjoy", "desc": "Collect and savor every bite"}
    ]
    
    for idx, step in enumerate(steps):
        with step:
            data = step_data[idx]
            st.markdown(f"""
            <div class="step-card">
                <div style="font-size: 2.5rem; margin-bottom: 1rem;">{data['icon']}</div>
                <h4>{data['title']}</h4>
                <p style="font-size: 0.9rem; color: #666;">{data['desc']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Restaurant Gallery
    st.markdown("---")
    st.subheader("🏛️ Our Restaurant")
    
    gallery = st.columns(3)
    # FIXED: All reliable Unsplash images
    gallery_images = [
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3&w=400",
        "https://images.unsplash.com/photo-1559329007-40df8a9345d8?ixlib=rb-4.0.3&w=400", 
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?ixlib=rb-4.3&w=400"
    ]
    
    captions = ["Elegant Dining Area", "Modern Kitchen", "Cozy Atmosphere"]
    
    for idx, col in enumerate(gallery):
        with col:
            st.image(gallery_images[idx], use_container_width=True, caption=captions[idx])

# Staff Dashboard with real-time updates
def staff_dashboard():
    st.title("👨‍🍳 Kitchen Dashboard - Live Orders")
    
    # Auto-refresh every 2 seconds for real-time updates
    if time.time() - st.session_state.last_order_check > 2:
        st.session_state.last_order_check = time.time()
        st.rerun()
    
    # Show last update time
    st.write(f"🕒 **Last updated:** {get_sa_time().strftime('%H:%M:%S')} SAST")
    st.write("🔄 **Auto-refreshing every 2 seconds**")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        pending_orders = len(db.get_all_orders('pending'))
        preparing_orders = len(db.get_all_orders('preparing'))
        ready_orders = len(db.get_all_orders('ready'))
        today_orders = db.get_todays_orders_count()
    except:
        pending_orders = preparing_orders = ready_orders = today_orders = 0
    
    with col1:
        st.metric("⏳ Pending Orders", pending_orders)
    with col2:
        st.metric("👨‍🍳 Preparing", preparing_orders)
    with col3:
        st.metric("✅ Ready", ready_orders)
    with col4:
        st.metric("📊 Today's Orders", today_orders)
    
    # Active orders only (not completed/collected)
    st.subheader("📋 Active Orders - Live Updates")
    try:
        orders = db.get_active_orders()
    except:
        orders = []
    
    if not orders:
        st.info("📭 No active orders. New orders will appear here automatically.")
        # Show refresh button
        if st.button("🔄 Refresh Now"):
            st.rerun()
        return
    
    # Create a container for each order with proper status management
    for order in orders:
        order_id = order[0]
        table_num = order[1] if order[1] else ""
        customer_name = str(order[2]) if order[2] else "Unknown"
        order_type = str(order[4]) if order[4] else "dine-in"
        current_status = str(order[5]) if order[5] else "pending"
        total_amount = order[6] if order[6] else 0
        order_time = order[7] if order[7] else "Unknown"
        items = order[8] if len(order) > 8 and order[8] else "No items"
        item_count = order[11] if len(order) > 11 else 0
        payment_method = order[10] if len(order) > 10 and order[10] else "cash"
        notes = order[7] if len(order) > 7 and order[7] else ""
        
        # Status colors and emojis
        status_config = {
            'pending': {'emoji': '⏳', 'color': '#FFA500'},
            'preparing': {'emoji': '👨‍🍳', 'color': '#1E90FF'}, 
            'ready': {'emoji': '✅', 'color': '#32CD32'},
            'completed': {'emoji': '🎉', 'color': '#008000'},
            'collected': {'emoji': '📦', 'color': '#4B0082'}
        }
        
        status_info = status_config.get(current_status, status_config['pending'])
        
        # Create expander for each order
        with st.expander(f"{status_info['emoji']} Order #{order_id} - {customer_name} - R{total_amount} - {current_status.title()}", expanded=current_status in ['pending', 'preparing']):
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.write(f"**👤 Customer:** {customer_name}")
                st.write(f"**🎯 Type:** {order_type.title()}")
                st.write(f"**💳 Payment:** {payment_method.title()}")
                if order_type == 'dine-in' and table_num:
                    st.write(f"**🪑 Table:** {table_num}")
                st.write(f"**🕒 Time:** {order_time} SAST")
                st.write(f"**📦 Items ({item_count}):** {items}")
                if notes:
                    st.write(f"**📝 Notes:** {notes}")
                st.write(f"**💰 Total:** R {total_amount}")
                st.write(f"**📊 Status:** **{current_status.title()}**")
            
            with col2:
                # Status update section
                st.write("### 🔄 Update Status")
                
                # Status options
                status_options = ['pending', 'preparing', 'ready', 'completed', 'collected']
                current_index = status_options.index(current_status) if current_status in status_options else 0
                
                # Status selector
                new_status = st.selectbox(
                    "Select new status:",
                    status_options,
                    index=current_index,
                    key=f"status_select_{order_id}"
                )
                
                # Update button
                if st.button("🔄 Update Status", key=f"update_btn_{order_id}", type="primary" if new_status != current_status else "secondary"):
                    try:
                        success = db.update_order_status(order_id, new_status, f"Status updated by staff")
                        if success:
                            st.success(f"✅ Order #{order_id} status updated to {new_status}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Failed to update status")
                    except Exception as e:
                        st.error(f"❌ Error updating status: {str(e)}")

# Enhanced Analytics Dashboard
def analytics_dashboard():
    st.title("📊 Analytics Dashboard")
    
    # Time period selector
    days = st.sidebar.selectbox("📅 Select Time Period", [7, 30, 90], index=1)
    
    # Get real analytics data
    analytics_data = db.get_real_analytics(days)
    
    if not analytics_data:
        st.warning("📭 No real data available yet. Analytics will show real data as orders are placed.")
        return
    
    totals = analytics_data['totals']
    daily_trend = analytics_data['daily_trend']
    hourly_data = analytics_data['hourly_data']
    popular_dishes = analytics_data['popular_dishes']
    category_distribution = analytics_data['category_distribution']
    payment_distribution = analytics_data['payment_distribution']
    
    # Key Metrics
    st.subheader("📈 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_orders = totals[0] if totals else 0
        st.metric("📦 Total Orders", total_orders)
    
    with col2:
        total_revenue = totals[1] if totals else 0
        st.metric("💰 Total Revenue", f"R {total_revenue:,.0f}")
    
    with col3:
        avg_order_value = totals[2] if totals else 0
        st.metric("📊 Average Order", f"R {avg_order_value:.0f}")
    
    with col4:
        if popular_dishes:
            most_popular = popular_dishes[0][0] if popular_dishes else "No data"
            st.metric("🏆 Most Popular", most_popular)
        else:
            st.metric("🏆 Most Popular", "No data")
    
    # Charts Section
    st.markdown("---")
    
    # Line Chart - Daily Revenue Trend
    if daily_trend:
        st.subheader("📈 Daily Revenue Trend")
        daily_df = pd.DataFrame(daily_trend, columns=['date', 'orders', 'revenue'])
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        
        fig_line = px.line(
            daily_df, 
            x='date', 
            y='revenue',
            title='Daily Revenue Trend',
            labels={'revenue': 'Revenue (R)', 'date': 'Date'}
        )
        fig_line.update_traces(line=dict(color='#667eea', width=3))
        fig_line.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_line, use_container_width=True)
    
    # Bar Chart - Revenue by Hour
    if hourly_data:
        st.subheader("🕒 Revenue by Hour")
        hourly_df = pd.DataFrame(hourly_data, columns=['hour', 'orders', 'revenue'])
        hourly_df['hour'] = hourly_df['hour'].astype(int)
        hourly_df = hourly_df.sort_values('hour')
        
        fig_bar = px.bar(
            hourly_df,
            x='hour',
            y='revenue',
            title='Revenue by Hour of Day',
            labels={'revenue': 'Revenue (R)', 'hour': 'Hour'},
            color='revenue',
            color_continuous_scale='Viridis'
        )
        fig_bar.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Pie Chart - Category Distribution
    if category_distribution:
        st.subheader("🥧 Menu Category Distribution")
        category_df = pd.DataFrame(category_distribution, columns=['category', 'quantity', 'revenue', 'orders'])
        
        fig_pie = px.pie(
            category_df,
            values='quantity',
            names='category',
            title='Items Sold by Category',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Bar Chart - Popular Dishes
    if popular_dishes:
        st.subheader("🍽️ Top 10 Popular Dishes")
        dishes_df = pd.DataFrame(popular_dishes, columns=['dish', 'quantity', 'revenue', 'orders'])
        dishes_df = dishes_df.head(10)
        
        fig_dishes = px.bar(
            dishes_df,
            x='dish',
            y='quantity',
            title='Most Popular Dishes by Quantity Sold',
            labels={'quantity': 'Quantity Sold', 'dish': 'Dish Name'},
            color='quantity',
            color_continuous_scale='Viridis'
        )
        fig_dishes.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_dishes, use_container_width=True)
    
    # Payment Method Distribution
    if payment_distribution:
        st.subheader("💳 Payment Method Distribution")
        payment_df = pd.DataFrame(payment_distribution, columns=['method', 'orders', 'revenue'])
        
        fig_payment = px.pie(
            payment_df,
            values='orders',
            names='method',
            title='Orders by Payment Method',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_payment.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig_payment, use_container_width=True)

# QR Code Management for Staff Only
def qr_management():
    st.title("📱 QR Code Management")
    
    st.markdown("""
    ### Generate QR Code for Customer Ordering
    
    Customers can scan this QR code to access the ordering system directly from their phones.
    Place this QR code at your restaurant entrance, tables, or counter for easy access.
    """)
    
    # Get the current URL
    ordering_url = "http://localhost:8501"
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("QR Code Preview")
        # Generate QR code
        qr_img = generate_qr_code(ordering_url)
        st.image(f"data:image/png;base64,{qr_img}", width=300)
        st.caption("Scan this QR code to start ordering")
    
    with col2:
        st.subheader("Download QR Code")
        st.markdown("""
        **Instructions:**
        1. Click the download button below
        2. Save the QR code image
        3. Print and display it in your restaurant
        4. Customers can scan it with their phone camera
        """)
        
        # Download link
        st.markdown(get_qr_download_link(qr_img), unsafe_allow_html=True)
        
        st.info("💡 **Tip:** Place QR codes on tables, at the entrance, and near the counter for maximum visibility.")

# Main navigation for staff
def staff_navigation():
    st.sidebar.title("👨‍💼 Staff Portal")
    st.sidebar.write(f"Welcome, {st.session_state.user[1]}!")
    
    if st.sidebar.button("🚪 Logout", type="primary"):
        logout()
    
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio("Navigation", ["👨‍🍳 Kitchen Dashboard", "📊 Analytics", "📱 QR Codes"])
    
    if page == "👨‍🍳 Kitchen Dashboard":
        staff_dashboard()
    elif page == "📊 Analytics":
        analytics_dashboard()
    elif page == "📱 QR Codes":
        qr_management()

# Main app with smart navigation
def main():
    st.set_page_config(
        page_title="Taste of South Africa",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Custom CSS for dark/light mode compatibility
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        text-align: center;
        color: var(--text-color);
        margin-bottom: 2rem;
    }
    .feature-card, .step-card {
        color: var(--text-color) !important;
        background: var(--background-color) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main navigation - Customer vs Staff
    if st.session_state.logged_in:
        # Staff interface
        staff_navigation()
    else:
        # Check if mobile mode
        is_mobile = st.session_state.mobile_mode
        
        if is_mobile:
            # MOBILE INTERFACE - Clean and focused
            st.sidebar.empty()
            
            # Simple mobile navigation
            st.markdown('<h2 class="main-header">🍽️ Taste of South Africa</h2>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🏠 Home", use_container_width=True, type="primary" if st.session_state.current_page == "home" else "secondary"):
                    st.session_state.current_page = "home"
                    st.rerun()
            with col2:
                if st.button("🍕 Order", use_container_width=True, type="primary" if st.session_state.current_page == "order" else "secondary"):
                    st.session_state.current_page = "order"
                    st.session_state.current_step = "order_type"
                    st.rerun()
            with col3:
                if st.button("📱 Track", use_container_width=True, type="primary" if st.session_state.current_page == "track" else "secondary"):
                    st.session_state.current_page = "track"
                    st.rerun()
            
            st.markdown("---")
            
            # Mobile content
            if st.session_state.current_page == "home":
                show_landing_page()
            elif st.session_state.current_page == "order":
                customer_ordering()
            elif st.session_state.current_page == "track":
                track_order()
                
        else:
            # DESKTOP INTERFACE - Full features
            st.sidebar.title("🍽️ Taste of South Africa")
            st.sidebar.markdown("---")
            
            # Customer navigation
            st.sidebar.subheader("🎯 Customer")
            app_mode = st.sidebar.radio("Choose your action:", 
                                      ["🏠 Home", "🍕 Place Order", "📱 Track Order"])
            
            # Staff login section
            st.sidebar.markdown("---")
            st.sidebar.subheader("👨‍💼 Staff Portal")
            staff_login()
            
            # Main content area
            if app_mode == "🏠 Home":
                show_landing_page()
            elif app_mode == "🍕 Place Order":
                customer_ordering()
            elif app_mode == "📱 Track Order":
                track_order()

if __name__ == "__main__":
    main()