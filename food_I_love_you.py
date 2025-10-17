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
            ''', ('food2025', hashlib.sha256('food@2025'.encode()).hexdigest(), 'admin'))
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
            ('Bottled Water', '500ml still water', 15, 'Beverage', 'bottled_water.jpeg'),  # Local image
            
            # BURGERS
            ('Beef Burger', 'Classic beef burger with cheese and veggies', 65, 'Main Course', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?ixlib=rb-4.0.3'),
            ('Chicken Burger', 'Grilled chicken breast with mayo and lettuce', 55, 'Main Course', 'chicken_burger.jpg'),  # Local image
            ('Cheese Burger', 'Double beef patty with extra cheese', 75, 'Main Course', 'https://images.unsplash.com/photo-1607013251379-e6eecfffe234?ixlib=rb-4.0.3'),
            
            # GRILLED ITEMS
            ('Grilled Chicken', 'Tender grilled chicken breast with herbs', 85, 'Main Course', 'https://images.unsplash.com/photo-1532550907401-a500c9a57435?ixlib=rb-4.0.3'),
            ('Beef Steak', 'Juicy beef steak with pepper sauce', 120, 'Main Course', 'beef_steak.jpeg'),  # Local image
            ('Grilled Fish', 'Fresh fish with lemon butter sauce', 95, 'Main Course', 'grilled_fish.jpg'),  # Local image
            
            # DESSERTS
            ('Chocolate Cake', 'Rich chocolate cake with ganache', 35, 'Dessert', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?ixlib=rb-4.0.3'),
            ('Ice Cream', 'Vanilla ice cream with chocolate sauce', 25, 'Dessert', 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?ixlib=rb-4.0.3'),
            ('Apple Pie', 'Warm apple pie with cinnamon', 30, 'Dessert', 'apple_pie.jpeg'),  # Local image
            
            # SIDES
            ('French Fries', 'Crispy golden fries', 25, 'Starter', 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?ixlib=rb-4.0.3'),
            ('Onion Rings', 'Beer-battered onion rings', 28, 'Starter', 'onion_rings.jpeg'),  # Local image
            ('Garlic Bread', 'Toasted bread with garlic butter', 20, 'Starter', 'garlic_bread.jpeg')  # Local image
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
            (3, 'Chocolate Cake', 'Rich chocolate cake with ganache', 35, 'Dessert', 1, 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?ixlib=rb-4.0.3')
        ]
    
    # Display menu items
    for item in menu_items:
        with st.container():
            col1, col2 = st.columns([1, 2])
            
            with col1:
                image_url = item[6] if len(item) > 6 and item[6] else None
                
                # Check if this is a local image file
                if image_url and (image_url.endswith('.jpeg') or image_url.endswith('.jpg') or image_url.endswith('.png')):
                    # Try to load local image file
                    try:
                        if os.path.exists(image_url):
                            st.image(image_url, use_container_width=True, caption=item[1])
                        else:
                            # If local file doesn't exist, show fallback
                            st.markdown(f'''
                            <div class="fallback-image">
                                <div>
                                    <div style="font-size: 3rem;">🍽️</div>
                                    <div>{item[1]}</div>
                                    <div style="font-size: 0.8rem; margin-top: 10px;">📁 {image_url} not found</div>
                                </div>
                            </div>
                            ''', unsafe_allow_html=True)
                    except Exception as e:
                        st.markdown(f'''
                        <div class="fallback-image">
                            <div>
                                <div style="font-size: 3rem;">🍽️</div>
                                <div>{item[1]}</div>
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)
                elif image_url and image_url.startswith('http'):
                    # Use external URL for other items
                    try:
                        st.image(image_url, use_container_width=True, caption=item[1])
                    except Exception as e:
                        st.markdown(f'''
                        <div class="fallback-image">
                            <div>
                                <div style="font-size: 3rem;">🍽️</div>
                                <div>{item[1]}</div>
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)
                else:
                    # No image available
                    st.markdown(f'''
                    <div class="fallback-image">
                        <div>
                            <div style="font-size: 3rem;">🍽️</div>
                            <div>{item[1]}</div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
            
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
            st.info("💫 We hope you enjoyed your meal!")
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
    .restaurant-image {
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 3.5rem; margin-bottom: 1rem;">🍽️ Taste Restaurant</h1>
        <p style="font-size: 1.5rem; margin-bottom: 2rem; opacity: 0.9;">Delicious Food & Great Service</p>
        <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
            <div style="background: rgba(255,255,255,0.2); padding: 1rem 2rem; border-radius: 25px; backdrop-filter: blur(10px);">
                🍕 Fresh Ingredients
            </div>
            <div style="background: rgba(255,255,255,0.2); padding: 1rem 2rem; border-radius: 25px; backdrop-filter: blur(10px);">
                👨‍🍳 Expert Chefs
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
        ## 🎯 Experience Great Taste
        
        Delicious food and drinks with quick service and affordable prices.
        
        **🌟 Quality Ingredients** - Fresh and locally sourced  
        **⚡ Lightning Fast** - Average 15-minute preparation  
        **📱 Live Tracking** - Watch your order in real-time  
        **💖 Customer First** - Your satisfaction is our priority
        """)
        
        if st.button("🚀 Start Your Order Now", type="primary", use_container_width=True):
            st.session_state.current_step = "order_type"
            st.session_state.current_page = "order"
            st.rerun()
    
    with col2:
        try:
            st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3", 
                    use_container_width=True, caption="Our Beautiful Restaurant", 
                    output_format="JPEG", use_column_width=True)
        except:
            st.markdown("""
            <div style="background: linear-gradient(45deg, #f0f0f0, #e0e0e0); border-radius: 10px; 
                        height: 200px; display: flex; align-items: center; justify-content: center;">
                <h3>🏛️ Our Restaurant</h3>
            </div>
            """, unsafe_allow_html=True)
    
    # Features Grid
    st.markdown("---")
    st.subheader("🌟 What Makes Us Special")
    
    features = st.columns(3)
    
    with features[0]:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 3rem;">🍽️</div>
            <h3 style="color: var(--text-color);">Great Taste</h3>
            <p style="color: var(--text-color);">Delicious recipes with quality ingredients and authentic flavors</p>
        </div>
        """, unsafe_allow_html=True)
    
    with features[1]:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 3rem;">⚡</div>
            <h3 style="color: var(--text-color);">Lightning Fast</h3>
            <p style="color: var(--text-color);">Average preparation time of just 15 minutes. Your hunger won't wait!</p>
        </div>
        """, unsafe_allow_html=True)
    
    with features[2]:
        st.markdown("""
        <div class="feature-card">
            <div style="font-size: 3rem;">📱</div>
            <h3 style="color: var(--text-color);">Live Tracking</h3>
            <p style="color: var(--text-color);">Watch your order being prepared in real-time. No more guessing!</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Restaurant Gallery
    st.markdown("---")
    st.subheader("🏛️ Our Restaurant")
    
    gallery_cols = st.columns(3)
    restaurant_images = [
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3",  # Interior
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?ixlib=rb-4.0.3",  # Dining area
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?ixlib=rb-4.0.3"   # Kitchen
    ]
    
    for idx, col in enumerate(gallery_cols):
        with col:
            try:
                st.image(restaurant_images[idx], use_container_width=True, 
                        caption=["Cozy Interior", "Elegant Dining", "Professional Kitchen"][idx])
            except:
                st.markdown(f"""
                <div style="background: linear-gradient(45deg, #f0f0f0, #e0e0e0); border-radius: 10px; 
                            height: 150px; display: flex; align-items: center; justify-content: center;">
                    <h4>Restaurant Image {idx+1}</h4>
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
                <h4 style="color: var(--text-color);">{data['title']}</h4>
                <p style="font-size: 0.9rem; color: var(--text-color);">{data['desc']}</p>
            </div>
            """, unsafe_allow_html=True)

# Premium Kitchen Dashboard with Real-time Updates
def premium_kitchen_dashboard():
    st.title("👨‍🍳 Premium Kitchen Dashboard")
    st.markdown("### 🚀 Real-time Order Management System")
    
    # Auto-refresh control
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.info("🔄 **Live Updates Active** - Real-time order synchronization")
    with col2:
        auto_refresh = st.checkbox("Auto Refresh", value=True, key="auto_refresh")
    with col3:
        refresh_rate = st.selectbox("Refresh Rate", [2, 5, 10], index=0, key="refresh_rate")
    
    # Auto-refresh logic
    if auto_refresh and (time.time() - st.session_state.last_order_check > refresh_rate):
        st.session_state.last_order_check = time.time()
        st.rerun()
    
    # Real-time stats with enhanced metrics
    st.subheader("📊 Live Kitchen Metrics")
    
    try:
        pending_orders = len(db.get_all_orders('pending'))
        preparing_orders = len(db.get_all_orders('preparing'))
        ready_orders = len(db.get_all_orders('ready'))
        today_orders = db.get_todays_orders_count()
        
        # Calculate average preparation time (simulated)
        avg_prep_time = random.randint(12, 18)
        
    except:
        pending_orders = preparing_orders = ready_orders = today_orders = 0
        avg_prep_time = 15
    
    metrics_cols = st.columns(5)
    
    with metrics_cols[0]:
        st.metric("⏳ Pending", pending_orders, delta=None, 
                 help="Orders waiting to be prepared")
    with metrics_cols[1]:
        st.metric("👨‍🍳 Preparing", preparing_orders, delta=None,
                 help="Orders currently being prepared")
    with metrics_cols[2]:
        st.metric("✅ Ready", ready_orders, delta=None,
                 help="Orders ready for service")
    with metrics_cols[3]:
        st.metric("📊 Today Total", today_orders, delta=None,
                 help="Total orders placed today")
    with metrics_cols[4]:
        st.metric("⏱️ Avg Prep Time", f"{avg_prep_time} min", delta=None,
                 help="Average preparation time")
    
    # Kitchen Priority System
    st.markdown("---")
    st.subheader("🎯 Priority Order Management")
    
    # Get active orders with enhanced details
    try:
        orders = db.get_active_orders()
    except:
        orders = []
    
    if not orders:
        st.info("🎉 **No active orders** - Kitchen is clear! New orders will appear here automatically.")
        st.image("https://images.unsplash.com/photo-1556909114-4d0d853e5e25?ixlib=rb-4.0.3", 
                caption="Ready for the next order!", use_container_width=True)
        return
    
    # Create tabs for different order statuses
    tab1, tab2, tab3 = st.tabs([f"⏳ Pending ({pending_orders})", 
                               f"👨‍🍳 Preparing ({preparing_orders})", 
                               f"✅ Ready ({ready_orders})"])
    
    with tab1:
        display_orders_by_status(orders, 'pending', "📋 New Orders - Action Required")
    
    with tab2:
        display_orders_by_status(orders, 'preparing', "🔥 Orders in Progress")
    
    with tab3:
        display_orders_by_status(orders, 'ready', "🎯 Ready for Service")

def display_orders_by_status(orders, status, title):
    """Display orders filtered by status with enhanced UI"""
    filtered_orders = [order for order in orders if str(order[5]) == status]
    
    if not filtered_orders:
        st.info(f"📭 No orders with status '{status}'")
        return
    
    st.subheader(title)
    
    for order in filtered_orders:
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
        notes = order[9] if len(order) > 9 and order[9] else ""
        
        # Enhanced status configuration
        status_config = {
            'pending': {'emoji': '⏳', 'color': '#FF6B35', 'priority': 'High'},
            'preparing': {'emoji': '👨‍🍳', 'color': '#1E90FF', 'priority': 'Medium'}, 
            'ready': {'emoji': '✅', 'color': '#32CD32', 'priority': 'Low'},
            'completed': {'emoji': '🎉', 'color': '#008000', 'priority': 'None'},
            'collected': {'emoji': '📦', 'color': '#4B0082', 'priority': 'None'}
        }
        
        status_info = status_config.get(current_status, status_config['pending'])
        
        # Calculate time since order (for priority)
        try:
            order_datetime = datetime.strptime(order_time, '%Y-%m-%d %H:%M:%S')
            time_elapsed = get_sa_time() - order_datetime
            minutes_elapsed = int(time_elapsed.total_seconds() / 60)
        except:
            minutes_elapsed = 0
        
        # Create order card with enhanced UI
        with st.container():
            st.markdown(f"""
            <div style="border: 2px solid {status_info['color']}; border-radius: 15px; padding: 1.5rem; margin: 1rem 0; background: var(--background-color);">
                <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 1rem;">
                    <h3 style="margin: 0; color: {status_info['color']};">
                        {status_info['emoji']} Order #{order_id} - {customer_name}
                    </h3>
                    <div style="background: {status_info['color']}; color: white; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem;">
                        {status_info['priority']} Priority
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 2])
            
            with col1:
                # Order details
                st.write(f"**👤 Customer:** {customer_name}")
                st.write(f"**🎯 Type:** {order_type.title()}")
                st.write(f"**💳 Payment:** {payment_method.title()}")
                if order_type == 'dine-in' and table_num:
                    st.write(f"**🪑 Table:** {table_num}")
                st.write(f"**🕒 Order Time:** {order_time} SAST")
                st.write(f"**⏱️ Time Elapsed:** {minutes_elapsed} minutes")
                st.write(f"**📦 Items ({item_count}):** {items}")
                if notes:
                    st.write(f"**📝 Notes:** {notes}")
                st.write(f"**💰 Total:** **R {total_amount}**")
                
                # Special indicators
                if minutes_elapsed > 10:
                    st.warning("🚨 **Priority Order** - Waiting for more than 10 minutes")
                if "urgent" in notes.lower():
                    st.error("⚡ **URGENT ORDER** - Special attention required")
            
            with col2:
                # Enhanced status management
                st.write("### 🔄 Status Management")
                
                # Quick action buttons
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if current_status != 'preparing' and st.button("Start Prep", key=f"start_{order_id}"):
                        db.update_order_status(order_id, 'preparing', 'Kitchen started preparation')
                        st.success("✅ Order preparation started!")
                        time.sleep(1)
                        st.rerun()
                
                with col_b:
                    if current_status != 'ready' and st.button("Mark Ready", key=f"ready_{order_id}"):
                        db.update_order_status(order_id, 'ready', 'Order ready for service')
                        st.success("🎉 Order marked as ready!")
                        time.sleep(1)
                        st.rerun()
                
                with col_c:
                    if current_status != 'completed' and st.button("Complete", key=f"complete_{order_id}"):
                        db.update_order_status(order_id, 'completed', 'Order completed by kitchen')
                        st.success("✅ Order completed!")
                        time.sleep(1)
                        st.rerun()
                
                # Advanced status selector
                st.write("**Advanced Status Control:**")
                status_options = ['pending', 'preparing', 'ready', 'completed', 'collected']
                current_index = status_options.index(current_status) if current_status in status_options else 0
                
                new_status = st.selectbox(
                    "Select status:",
                    status_options,
                    index=current_index,
                    key=f"adv_status_{order_id}"
                )
                
                if st.button("🔄 Update Status", key=f"update_adv_{order_id}", 
                           type="primary" if new_status != current_status else "secondary"):
                    try:
                        success = db.update_order_status(order_id, new_status, f"Status updated via kitchen dashboard")
                        if success:
                            st.success(f"✅ Order #{order_id} updated to {new_status}!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            st.markdown("---")

# Premium Analytics Dashboard
def premium_analytics_dashboard():
    st.title("📊 Premium Analytics Dashboard")
    st.markdown("### 🚀 Advanced Business Intelligence & Insights")
    
    # Time period selector with enhanced options
    st.sidebar.markdown("### 📈 Analytics Settings")
    days = st.sidebar.selectbox("Time Period", [7, 30, 90, 365], index=1, key="analytics_days")
    show_forecast = st.sidebar.checkbox("Show Revenue Forecast", value=True)
    compare_period = st.sidebar.checkbox("Compare with Previous Period", value=True)
    
    # Get analytics data
    analytics_data = db.get_real_analytics(days)
    
    if not analytics_data:
        st.warning("📊 **No data available yet** - Analytics will populate as orders are processed")
        st.info("💡 Place some test orders to see analytics in action!")
        return
    
    totals = analytics_data['totals']
    daily_trend = analytics_data['daily_trend']
    hourly_data = analytics_data['hourly_data']
    popular_dishes = analytics_data['popular_dishes']
    category_distribution = analytics_data['category_distribution']
    payment_distribution = analytics_data['payment_distribution']
    
    # Enhanced KPI Metrics
    st.subheader("🎯 Key Performance Indicators")
    
    kpi_cols = st.columns(4)
    
    with kpi_cols[0]:
        total_orders = totals[0] if totals else 0
        st.metric("📦 Total Orders", f"{total_orders:,}", 
                 delta=f"+{random.randint(5, 15)}% vs last period" if compare_period else None)
    
    with kpi_cols[1]:
        total_revenue = totals[1] if totals else 0
        st.metric("💰 Total Revenue", f"R {total_revenue:,.0f}", 
                 delta=f"R +{random.randint(500, 2000):,}" if compare_period else None)
    
    with kpi_cols[2]:
        avg_order_value = totals[2] if totals else 0
        st.metric("📊 Average Order", f"R {avg_order_value:.0f}", 
                 delta=f"R +{random.randint(5, 20)}" if compare_period else None)
    
    with kpi_cols[3]:
        if popular_dishes:
            most_popular = popular_dishes[0][0] if popular_dishes else "No data"
            st.metric("🏆 Best Seller", most_popular, 
                     delta=f"{random.randint(10, 25)}% popularity")
        else:
            st.metric("🏆 Best Seller", "No data")
    
    # Advanced Charts Section
    st.markdown("---")
    
    # Revenue Trend with Forecast
    if daily_trend:
        st.subheader("📈 Revenue Trend & Forecast")
        daily_df = pd.DataFrame(daily_trend, columns=['date', 'orders', 'revenue'])
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        
        # Add forecast data (simulated)
        if show_forecast and len(daily_df) > 5:
            last_date = daily_df['date'].max()
            forecast_dates = [last_date + timedelta(days=i) for i in range(1, 8)]
            forecast_revenue = [daily_df['revenue'].mean() * (1 + random.uniform(-0.1, 0.2)) for _ in range(7)]
            
            forecast_df = pd.DataFrame({
                'date': forecast_dates,
                'revenue': forecast_revenue,
                'type': 'forecast'
            })
            daily_df['type'] = 'actual'
            
            combined_df = pd.concat([daily_df[['date', 'revenue', 'type']], forecast_df])
        else:
            combined_df = daily_df
            combined_df['type'] = 'actual'
        
        fig_trend = px.line(
            combined_df, 
            x='date', 
            y='revenue',
            color='type',
            title='Daily Revenue Trend with 7-Day Forecast',
            labels={'revenue': 'Revenue (R)', 'date': 'Date', 'type': 'Data Type'},
            color_discrete_map={'actual': '#667eea', 'forecast': '#ff6b6b'}
        )
        fig_trend.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified'
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    
    # Business Insights
    st.markdown("---")
    st.subheader("💡 Business Insights")
    
    insight_cols = st.columns(2)
    
    with insight_cols[0]:
        st.info("""
        **📊 Peak Performance Hours**
        - Lunch Rush: 12:00 - 14:00
        - Dinner Peak: 18:00 - 20:00
        - Recommend: Extra staff during peaks
        """)
    
    with insight_cols[1]:
        st.success("""
        **🎯 Customer Preferences**
        - Most popular: Beef Burger
        - High margin: Grilled Items
        - Growth category: Beverages
        """)
    
    # Enhanced Popular Dishes Analysis
    if popular_dishes:
        st.subheader("🍽️ Menu Performance Analysis")
        
        dishes_df = pd.DataFrame(popular_dishes, columns=['dish', 'quantity', 'revenue', 'orders'])
        dishes_df = dishes_df.head(10)
        
        # Calculate metrics
        dishes_df['revenue_per_item'] = dishes_df['revenue'] / dishes_df['quantity']
        dishes_df['popularity_score'] = (dishes_df['quantity'] / dishes_df['quantity'].sum()) * 100
        
        fig_dishes = px.bar(
            dishes_df,
            x='dish',
            y=['quantity', 'revenue'],
            title='Top 10 Dishes: Quantity vs Revenue',
            labels={'value': 'Amount', 'dish': 'Dish Name', 'variable': 'Metric'},
            barmode='group',
            color_discrete_sequence=['#667eea', '#ff6b6b']
        )
        fig_dishes.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_dishes, use_container_width=True)
    
    # Real-time Performance Metrics
    st.markdown("---")
    st.subheader("⚡ Real-time Performance")
    
    perf_cols = st.columns(3)
    
    with perf_cols[0]:
        st.metric("🕒 Avg Prep Time", "14.5 min", "-1.2 min")
    
    with perf_cols[1]:
        st.metric("📱 Order Accuracy", "98.7%", "+0.5%")
    
    with perf_cols[2]:
        st.metric("💖 Customer Satisfaction", "4.8/5.0", "+0.2")

# Enhanced QR Code Management
def premium_qr_management():
    st.title("📱 Premium QR Code Management")
    
    st.markdown("""
    ### 🚀 Smart QR Code System
    
    Generate and manage QR codes for seamless customer ordering experience.
    Track scan analytics and optimize placement for maximum engagement.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 QR Code Generator")
        
        # Customizable QR options
        qr_url = st.text_input("Ordering URL", "http://localhost:8501", key="qr_url")
        qr_size = st.slider("QR Code Size", 200, 500, 300, key="qr_size")
        qr_color = st.color_picker("QR Color", "#000000", key="qr_color")
        
        # Generate QR code
        if st.button("🔄 Generate QR Code", type="primary"):
            qr_img = generate_qr_code(qr_url)
            st.image(f"data:image/png;base64,{qr_img}", width=qr_size)
            st.success("✅ QR Code generated successfully!")
            
            # Download section
            st.markdown("---")
            st.subheader("📥 Download Options")
            st.markdown(get_qr_download_link(qr_img), unsafe_allow_html=True)
    
    with col2:
        st.subheader("📊 QR Code Analytics")
        
        # Simulated analytics
        st.metric("🔄 Total Scans", "1,247", "+128 this week")
        st.metric("📱 Mobile Orders", "893", "71.5% of total")
        st.metric("⏰ Peak Scan Time", "19:30", "Dinner rush")
        
        st.info("""
        **💡 Placement Tips:**
        - Tables: 85% conversion rate
        - Entrance: 62% conversion rate  
        - Counter: 45% conversion rate
        - Menus: 78% conversion rate
        """)
        
        st.warning("""
        **🎯 Optimization Suggestions:**
        - Add more table QR codes
        - Train staff to promote scanning
        - Offer scan-to-order discounts
        """)

# Premium Staff Navigation
def premium_staff_navigation():
    st.sidebar.title("👨‍💼 Premium Staff Portal")
    
    # User info with enhanced display
    if st.session_state.user:
        user_role = st.session_state.user[3]
        st.sidebar.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
            <h4 style="margin: 0; color: white;">Welcome, {st.session_state.user[1]}!</h4>
            <p style="margin: 0; opacity: 0.9;">Role: {user_role.title()}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Enhanced navigation
    st.sidebar.markdown("---")
    page = st.sidebar.radio("**Navigation Menu**", 
                          ["👨‍🍳 Kitchen Dashboard", "📊 Analytics", "📱 QR Codes", "⚙️ Settings"])
    
    # Quick actions
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Quick Actions")
    
    if st.sidebar.button("🔄 Refresh All Data", use_container_width=True):
        st.rerun()
    
    if st.sidebar.button("📊 View Today's Summary", use_container_width=True):
        st.session_state.last_order_check = 0  # Force refresh
        st.rerun()
    
    # Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", type="primary", use_container_width=True):
        logout()
    
    # Page routing
    if page == "👨‍🍳 Kitchen Dashboard":
        premium_kitchen_dashboard()
    elif page == "📊 Analytics":
        premium_analytics_dashboard()
    elif page == "📱 QR Codes":
        premium_qr_management()
    elif page == "⚙️ Settings":
        st.title("⚙️ System Settings")
        st.info("System configuration and preferences coming soon...")

# Main app with premium features
def main():
    st.set_page_config(
        page_title="Taste Restaurant - Premium",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Premium CSS for dark/light mode compatibility
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        text-align: center;
        color: var(--text-color);
        margin-bottom: 2rem;
    }
    
    /* Dark mode compatibility */
    .feature-card, .step-card {
        background: var(--background-color);
        color: var(--text-color);
    }
    
    /* Ensure text visibility in all modes */
    .st-bw, .st-d4, .st-d5, .st-d6, .st-d7, .st-d8, .st-d9, .st-da, .st-db, .st-dc {
        color: var(--text-color) !important;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--background-color);
    }
    
    ::-webkit-scrollbar-thumb {
        background: #667eea;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #764ba2;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main navigation - Customer vs Staff
    if st.session_state.logged_in:
        # Premium staff interface
        premium_staff_navigation()
    else:
        # Customer interface remains the same
        st.sidebar.title("🍽️ Taste Restaurant")
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