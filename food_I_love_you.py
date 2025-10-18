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
import threading
from concurrent.futures import ThreadPoolExecutor

# Set South African timezone
SA_TIMEZONE = pytz.timezone('Africa/Johannesburg')

def get_sa_time():
    """Get current South African time"""
    return datetime.now(SA_TIMEZONE)

# REAL-TIME DATABASE WITH PERFORMANCE OPTIMIZATION
class RestaurantDB:
    def __init__(self, db_name="restaurant_premium.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent reads
        self.conn.execute("PRAGMA synchronous=NORMAL")  # Better performance
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Drop and recreate all tables to ensure fresh start
        cursor.execute("DROP TABLE IF EXISTS order_status_history")
        cursor.execute("DROP TABLE IF EXISTS order_items") 
        cursor.execute("DROP TABLE IF EXISTS orders")
        cursor.execute("DROP TABLE IF EXISTS menu_items")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS analytics_cache")
        
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
        
        # Orders table with indexing for performance
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
                payment_method TEXT DEFAULT 'cash',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        
        # Analytics cache for performance
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE,
                cache_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_token ON orders(order_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)')
        
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
        
        # Clear existing menu items and insert new menu
        cursor.execute('DELETE FROM menu_items')
        
        # PREMIUM MENU WITH HIGH-QUALITY IMAGES
        menu_items = [
            # BEVERAGES
            ('Cappuccino', 'Freshly brewed coffee with steamed milk', 25, 'Beverage', 'https://images.unsplash.com/photo-1561047029-3000c68339ca?w=400'),
            ('Coca-Cola', 'Ice cold Coca-Cola', 18, 'Beverage', 'https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=400'),
            ('Orange Juice', 'Freshly squeezed orange juice', 22, 'Beverage', 'https://images.unsplash.com/photo-1613478223719-2ab802602423?w=400'),
            ('Sparkling Water', 'Premium sparkling water', 20, 'Beverage', 'https://images.unsplash.com/photo-1548839149-851a64d0c1e9?w=400'),
            
            # BURGERS
            ('Beef Burger', 'Classic beef burger with cheese and veggies', 65, 'Main Course', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400'),
            ('Chicken Burger', 'Grilled chicken breast with mayo and lettuce', 55, 'Main Course', 'https://images.unsplash.com/photo-1606755962773-d324e74534a2?w=400'),
            ('Cheese Burger', 'Double beef patty with extra cheese', 75, 'Main Course', 'https://images.unsplash.com/photo-1607013251379-e6eecfffe234?w=400'),
            ('Veggie Burger', 'Plant-based patty with fresh vegetables', 60, 'Main Course', 'https://images.unsplash.com/photo-1596662951482-0c4ba74a6df6?w=400'),
            
            # GRILLED ITEMS
            ('Grilled Chicken', 'Tender grilled chicken breast with herbs', 85, 'Main Course', 'https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=400'),
            ('Beef Steak', 'Juicy beef steak with pepper sauce', 120, 'Main Course', 'https://images.unsplash.com/photo-1607116667981-ff4b72a5d5c2?w=400'),
            ('Grilled Fish', 'Fresh fish with lemon butter sauce', 95, 'Main Course', 'https://images.unsplash.com/photo-1598514982193-71c63af352c3?w=400'),
            ('BBQ Ribs', 'Slow-cooked BBQ ribs with secret sauce', 110, 'Main Course', 'https://images.unsplash.com/photo-1546833996-9c7a2fce76b3?w=400'),
            
            # DESSERTS
            ('Chocolate Cake', 'Rich chocolate cake with ganache', 35, 'Dessert', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=400'),
            ('Ice Cream', 'Vanilla ice cream with chocolate sauce', 25, 'Dessert', 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=400'),
            ('Apple Pie', 'Warm apple pie with cinnamon', 30, 'Dessert', 'https://images.unsplash.com/photo-1535920527002-b35e96722206?w=400'),
            ('Cheesecake', 'Creamy New York style cheesecake', 40, 'Dessert', 'https://images.unsplash.com/photo-1524351199678-941a58a3df50?w=400'),
            
            # SIDES
            ('French Fries', 'Crispy golden fries', 25, 'Starter', 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400'),
            ('Onion Rings', 'Beer-battered onion rings', 28, 'Starter', 'https://images.unsplash.com/photo-1634510401050-8d0a2743c471?w=400'),
            ('Garlic Bread', 'Toasted bread with garlic butter', 20, 'Starter', 'https://images.unsplash.com/photo-1573140247635-6a84b4f2e4a8?w=400'),
            ('Mozzarella Sticks', 'Crispy mozzarella sticks with marinara', 32, 'Starter', 'https://images.unsplash.com/photo-1599490659213-e2b9527bd087?w=400')
        ]
        
        for item in menu_items:
            cursor.execute('''
                INSERT INTO menu_items (name, description, price, category, image_url)
                VALUES (?, ?, ?, ?, ?)
            ''', item)
        
        self.conn.commit()

    def add_order(self, customer_name, order_type, items, table_number=None, notes="", payment_method="cash"):
        """ULTRA-RELIABLE ORDER CREATION"""
        cursor = self.conn.cursor()
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        # Generate SUPER reliable order token
        timestamp = int(time.time())
        random_part = random.randint(1000, 9999)
        order_token = f"ORD{random_part}{timestamp}"
        
        # Use current South African timestamp
        current_time = get_sa_time().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # Insert order with explicit status and timestamp
            cursor.execute('''
                INSERT INTO orders (customer_name, order_type, table_number, total_amount, notes, 
                                  order_token, order_date, payment_method, status, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            ''', (customer_name, order_type, table_number, total_amount, notes, 
                  order_token, current_time, payment_method, current_time))
            
            order_id = cursor.lastrowid
            
            # Insert order items
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
            
            # VERIFY the order was created
            cursor.execute('SELECT order_token, status FROM orders WHERE id = ?', (order_id,))
            verify_order = cursor.fetchone()
            
            if verify_order and verify_order[0] == order_token:
                return order_id, order_token
            else:
                raise Exception("Order verification failed")
            
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Database error: {str(e)}")

    def get_order_by_token(self, order_token):
        """ULTRA-RELIABLE ORDER RETRIEVAL"""
        cursor = self.conn.cursor()
        
        try:
            # SIMPLE but RELIABLE query
            cursor.execute('''
                SELECT o.*, 
                       GROUP_CONCAT(oi.menu_item_name || ' (x' || oi.quantity || ')', ', ') as items,
                       COUNT(oi.id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.order_token = ?
                GROUP BY o.id
            ''', (order_token,))
            
            result = cursor.fetchone()
            return result
            
        except Exception as e:
            # Fallback - try simple order query
            try:
                cursor.execute('SELECT * FROM orders WHERE order_token = ?', (order_token,))
                return cursor.fetchone()
            except:
                return None

    def get_order_status(self, order_token):
        """Lightning-fast status check"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT status FROM orders WHERE order_token = ?', (order_token,))
            result = cursor.fetchone()
            return result[0] if result else None
        except:
            return None

    def update_order_status(self, order_id, new_status, notes=""):
        """REAL-TIME status update"""
        cursor = self.conn.cursor()
        current_time = get_sa_time().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # Update order status
            cursor.execute('''
                UPDATE orders SET status = ?, last_updated = ? WHERE id = ?
            ''', (new_status, current_time, order_id))
            
            # Add to history
            cursor.execute('''
                INSERT INTO order_status_history (order_id, status, notes)
                VALUES (?, ?, ?)
            ''', (order_id, new_status, notes))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            return False

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

    def get_real_analytics(self, days=30):
        """REAL DATA ANALYTICS - No fake data!"""
        cursor = self.conn.cursor()
        
        try:
            # Check cache first
            cache_key = f"analytics_{days}_{datetime.now().strftime('%Y%m%d')}"
            cursor.execute('SELECT cache_data FROM analytics_cache WHERE cache_key = ?', (cache_key,))
            cached = cursor.fetchone()
            
            if cached:
                import json
                return json.loads(cached[0])
            
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
            
            # Daily revenue trend (REAL DATA)
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
            
            # Revenue by hour (REAL DATA)
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
            
            # Popular dishes (REAL DATA)
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
            
            # Category distribution (REAL DATA)
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
                ORDER BY total_revenue DESC
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
            
            result = {
                'totals': totals or (0, 0, 0),
                'daily_trend': daily_data or [],
                'hourly_data': hourly_data or [],
                'popular_dishes': popular_dishes or [],
                'category_distribution': category_distribution or [],
                'payment_distribution': payment_distribution or [],
                'order_type_distribution': order_type_distribution or []
            }
            
            # Cache the results
            import json
            cursor.execute('''
                INSERT OR REPLACE INTO analytics_cache (cache_key, cache_data)
                VALUES (?, ?)
            ''', (cache_key, json.dumps(result)))
            self.conn.commit()
            
            return result
            
        except Exception as e:
            # Return empty but valid structure if error
            return {
                'totals': (0, 0, 0),
                'daily_trend': [],
                'hourly_data': [],
                'popular_dishes': [],
                'category_distribution': [],
                'payment_distribution': [],
                'order_type_distribution': []
            }

    def get_todays_orders_count(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM orders WHERE date(order_date) = date("now")')
        result = cursor.fetchone()
        return result[0] if result else 0

    def get_menu_items(self, category=None):
        cursor = self.conn.cursor()
        if category and category != 'All':
            cursor.execute('SELECT * FROM menu_items WHERE available = 1 AND category = ? ORDER BY name', (category,))
        else:
            cursor.execute('SELECT * FROM menu_items WHERE available = 1 ORDER BY category, name')
        return cursor.fetchall()

# Initialize database
try:
    if os.path.exists("restaurant_premium.db"):
        os.remove("restaurant_premium.db")
    db = RestaurantDB()
except Exception as e:
    st.error(f"Database initialization error: {e}")

# REAL-TIME ORDER TRACKING SYSTEM
class RealTimeTracker:
    def __init__(self):
        self.last_updates = {}
    
    def check_status_change(self, order_token, current_status):
        """Check if status changed and return new status"""
        if order_token not in self.last_updates:
            self.last_updates[order_token] = current_status
            return current_status
        
        if self.last_updates[order_token] != current_status:
            self.last_updates[order_token] = current_status
            return current_status
        
        return None

tracker = RealTimeTracker()

# QR Code Generator
def generate_qr_code(url, size=300):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def get_qr_download_link(img_str, filename="premium_ordering_qr.png"):
    href = f'<a href="data:image/png;base64,{img_str}" download="{filename}" style="display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">📱 Download QR Code</a>'
    return href

# AUTHENTICATION SYSTEM
def staff_login():
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔐 Staff Login")
    
    username = st.sidebar.text_input("👤 Username", key="login_user")
    password = st.sidebar.text_input("🔒 Password", type="password", key="login_pass")
    
    if st.sidebar.button("🚀 Login", use_container_width=True, type="primary"):
        if username and password:
            cursor = db.conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_password))
            user = cursor.fetchone()
            
            if user:
                st.session_state.user = user
                st.session_state.logged_in = True
                st.session_state.role = user[3]
                st.sidebar.success(f"🎉 Welcome, {user[1]}!")
                time.sleep(1)
                st.rerun()
            else:
                st.sidebar.error("❌ Invalid credentials")

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# SESSION STATE MANAGEMENT
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
        'tracking_order_token': None,
        'last_order_check': time.time(),
        'current_page': "home",
        'auto_refresh': True
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# PREMIUM CUSTOMER ORDERING EXPERIENCE
def customer_ordering():
    st.markdown("""
    <style>
    .premium-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .step-indicator {
        display: flex;
        justify-content: center;
        margin-bottom: 2rem;
    }
    .step {
        padding: 10px 20px;
        margin: 0 10px;
        border-radius: 25px;
        background: #f0f0f0;
        color: #666;
        font-weight: bold;
    }
    .step.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="premium-header"><h1>🍽️ TASTE RESTAURANT</h1><p>Premium Dining Experience • Real-Time Order Tracking</p></div>', unsafe_allow_html=True)
    
    # Step indicator
    steps = ["Order Type", "Your Info", "Menu", "Confirm", "Track"]
    current_step_index = ["order_type", "customer_info", "menu", "confirmation", "tracking"].index(st.session_state.current_step)
    
    step_html = '<div class="step-indicator">'
    for i, step in enumerate(steps):
        step_html += f'<div class="step {"active" if i == current_step_index else ""}">{step}</div>'
    step_html += '</div>'
    st.markdown(step_html, unsafe_allow_html=True)
    
    # Route to current step
    if st.session_state.current_step == "order_type":
        show_order_type_selection()
    elif st.session_state.current_step == "customer_info":
        show_customer_info()
    elif st.session_state.current_step == "menu":
        show_menu_selection()
    elif st.session_state.current_step == "confirmation":
        show_order_confirmation()
    elif st.session_state.current_step == "tracking":
        track_order_live()

def show_order_type_selection():
    st.subheader("🎯 How Would You Like to Dine?")
    
    col1, col2, col3 = st.columns(3)
    
    options = [
        {"icon": "🏠", "title": "Dine In", "desc": "Enjoy our premium atmosphere", "type": "dine-in"},
        {"icon": "🥡", "title": "Takeaway", "desc": "Pick up and enjoy elsewhere", "type": "takeaway"},
        {"icon": "🚚", "title": "Delivery", "desc": "We bring it to your door", "type": "delivery"}
    ]
    
    for i, option in enumerate(options):
        with [col1, col2, col3][i]:
            st.markdown(f"""
            <div style="text-align: center; padding: 2rem 1rem; border: 2px solid #e0e0e0; border-radius: 15px; cursor: pointer; transition: all 0.3s;">
                <div style="font-size: 3rem;">{option['icon']}</div>
                <h3>{option['title']}</h3>
                <p style="color: #666;">{option['desc']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Choose {option['title']}", key=option['type'], use_container_width=True):
                st.session_state.order_type = option['type']
                st.session_state.current_step = "customer_info"
                st.rerun()

def show_customer_info():
    st.subheader("👤 Tell Us About Yourself")
    
    with st.form("customer_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("**Full Name**", value=st.session_state.customer_name, 
                                        placeholder="Enter your name", key="cust_name")
            
            if st.session_state.order_type == "dine-in":
                table_number = st.number_input("**Table Number**", min_value=1, max_value=50, 
                                            value=st.session_state.table_number, key="table_num")
            else:
                table_number = None
                
        with col2:
            payment_method = st.radio("**Payment Method**", ["💵 Cash", "💳 Card"], key="pay_method")
            st.session_state.payment_method = "cash" if payment_method == "💵 Cash" else "card"
        
        order_notes = st.text_area("**Special Instructions**", value=st.session_state.order_notes,
                                 placeholder="Allergies, dietary requirements, or special requests...",
                                 height=100, key="notes_area")
        
        submitted = st.form_submit_button("🚀 Continue to Menu", type="primary")
        
        if submitted:
            if not customer_name.strip():
                st.error("👋 Please provide your name")
            else:
                st.session_state.customer_name = customer_name.strip()
                st.session_state.table_number = table_number
                st.session_state.order_notes = order_notes
                st.session_state.current_step = "menu"
                st.rerun()

def show_menu_selection():
    st.subheader("📋 Explore Our Premium Menu")
    
    # Category filter
    categories = ['All', 'Beverage', 'Main Course', 'Dessert', 'Starter']
    selected_category = st.selectbox("**Filter by Category**", categories, key="cat_filter")
    
    # Get menu items
    menu_items = db.get_menu_items(selected_category if selected_category != 'All' else None)
    
    if not menu_items:
        st.info("No menu items available in this category.")
        return
    
    # Display menu in a grid
    cols = st.columns(2)
    for idx, item in enumerate(menu_items):
        with cols[idx % 2]:
            display_menu_item(item)
    
    # Cart summary
    show_cart_summary()

def display_menu_item(item):
    """Display a menu item with image and add to cart functionality"""
    with st.container():
        st.markdown("""
        <style>
        .menu-item-card {
            border: 1px solid #e0e0e0;
            border-radius: 15px;
            padding: 1rem;
            margin: 0.5rem 0;
            transition: all 0.3s ease;
        }
        .menu-item-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Try to load image
        try:
            st.image(item[6], use_container_width=True, caption=item[1])
        except:
            st.markdown(f"""
            <div style="background: linear-gradient(45deg, #f0f0f0, #e0e0e0); height: 150px; border-radius: 10px; 
                        display: flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
                <div style="text-align: center;">
                    <div style="font-size: 2rem;">🍽️</div>
                    <div>{item[1]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="menu-item-card">
            <h3>{item[1]}</h3>
            <p style="color: #666; font-size: 0.9rem;">{item[2]}</p>
            <h4 style="color: #e74c3c; margin: 1rem 0;">R {item[3]:.2f}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Add to cart controls
        current_qty = next((cart_item['quantity'] for cart_item in st.session_state.cart 
                          if cart_item['id'] == item[0]), 0)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("➖", key=f"dec_{item[0]}", use_container_width=True):
                if current_qty > 0:
                    # Remove or decrease quantity
                    st.session_state.cart = [ci for ci in st.session_state.cart if ci['id'] != item[0]]
                    if current_qty > 1:
                        st.session_state.cart.append({
                            'id': item[0], 'name': item[1], 'price': item[3], 
                            'quantity': current_qty - 1
                        })
                    st.rerun()
        
        with col2:
            st.markdown(f"<center><strong>{current_qty}</strong> in cart</center>", unsafe_allow_html=True)
        
        with col3:
            if st.button("➕", key=f"inc_{item[0]}", use_container_width=True):
                existing_item = next((ci for ci in st.session_state.cart if ci['id'] == item[0]), None)
                if existing_item:
                    existing_item['quantity'] += 1
                else:
                    st.session_state.cart.append({
                        'id': item[0], 'name': item[1], 'price': item[3], 'quantity': 1
                    })
                st.rerun()

def show_cart_summary():
    if st.session_state.cart:
        st.markdown("---")
        st.subheader("🛒 Your Order Summary")
        
        total = 0
        for item in st.session_state.cart:
            item_total = item['price'] * item['quantity']
            total += item_total
            st.write(f"• **{item['name']}** x{item['quantity']} - R {item_total:.2f}")
        
        st.markdown(f"### 💰 Total: R {total:.2f}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back", use_container_width=True):
                st.session_state.current_step = "customer_info"
                st.rerun()
        with col2:
            if st.button("📦 Proceed to Checkout", type="primary", use_container_width=True):
                st.session_state.current_step = "confirmation"
                st.rerun()
    else:
        st.info("🛒 Your cart is empty. Add some delicious items!")

def show_order_confirmation():
    st.subheader("✅ Confirm Your Order")
    
    # Order summary
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Order Details")
        st.write(f"**Customer:** {st.session_state.customer_name}")
        st.write(f"**Order Type:** {st.session_state.order_type.replace('-', ' ').title()}")
        if st.session_state.order_type == "dine-in":
            st.write(f"**Table:** {st.session_state.table_number}")
        st.write(f"**Payment:** {st.session_state.payment_method.title()}")
        if st.session_state.order_notes:
            st.write(f"**Notes:** {st.session_state.order_notes}")
    
    with col2:
        st.markdown("### 🍽️ Order Items")
        total = 0
        for item in st.session_state.cart:
            item_total = item['price'] * item['quantity']
            total += item_total
            st.write(f"• {item['name']} x{item['quantity']} - R {item_total:.2f}")
        
        st.markdown(f"**Total: R {total:.2f}**")
    
    st.markdown("---")
    
    # Final confirmation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Back to Menu", use_container_width=True):
            st.session_state.current_step = "menu"
            st.rerun()
    
    with col2:
        if st.button("✅ Place Order Now", type="primary", use_container_width=True):
            try:
                # Prepare order items
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
                    # Update session state
                    st.session_state.order_id = order_id
                    st.session_state.order_token = order_token
                    st.session_state.order_placed = True
                    st.session_state.current_step = "tracking"
                    
                    # Clear cart
                    st.session_state.cart = []
                    
                    st.success(f"🎉 Order placed successfully!")
                    st.info(f"**Your Order Token:** `{order_token}`")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ Failed to place order. Please try again.")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

def track_order_live():
    """REAL-TIME ORDER TRACKING WITH INSTANT UPDATES"""
    st.subheader("📱 Live Order Tracking")
    
    # Determine which order token to track
    if st.session_state.order_placed and st.session_state.order_token:
        order_token = st.session_state.order_token
        st.success(f"🔍 Tracking your active order: `{order_token}`")
    else:
        order_token = st.text_input("Enter your order token:", 
                                  placeholder="e.g., ORD12345678",
                                  key="track_input")
        if not order_token:
            st.info("💡 Don't have an order token? Place a new order to get one!")
            if st.button("🍽️ Place New Order"):
                st.session_state.current_step = "order_type"
                st.session_state.order_placed = False
                st.rerun()
            return
    
    # REAL-TIME TRACKING
    if order_token:
        # Get current order status
        current_status = db.get_order_status(order_token)
        
        if not current_status:
            st.error("❌ Order not found. Please check your order token.")
            return
        
        # Check for status changes
        status_change = tracker.check_status_change(order_token, current_status)
        if status_change:
            st.success(f"🔄 Status updated: {status_change.title()}!")
        
        # Get full order details
        order = db.get_order_by_token(order_token)
        
        if order:
            display_order_progress(order, current_status)
            
            # AUTO-REFRESH every 2 seconds
            if st.session_state.auto_refresh:
                time.sleep(2)
                st.rerun()
        else:
            st.error("❌ Could not load order details.")

def display_order_progress(order, current_status):
    """Display beautiful order progress with real-time updates"""
    
    # Status configuration
    status_flow = {
        'pending': {'emoji': '📝', 'name': 'Order Received', 'color': '#FF6B35', 'description': 'We have received your order'},
        'confirmed': {'emoji': '✅', 'name': 'Order Confirmed', 'color': '#1E90FF', 'description': 'Kitchen has confirmed your order'},
        'preparing': {'emoji': '👨‍🍳', 'name': 'Preparing', 'color': '#FFA500', 'description': 'Our chefs are cooking your meal'},
        'ready': {'emoji': '🎯', 'name': 'Ready', 'color': '#32CD32', 'description': 'Your order is ready for pickup/delivery'},
        'completed': {'emoji': '🎉', 'name': 'Completed', 'color': '#008000', 'description': 'Order completed successfully'},
        'collected': {'emoji': '📦', 'name': 'Collected', 'color': '#4B0082', 'description': 'Order has been collected'}
    }
    
    current_status_info = status_flow.get(current_status, status_flow['pending'])
    
    # Status header
    st.markdown(f"""
    <div style="background: {current_status_info['color']}; color: white; padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem;">
        <div style="font-size: 4rem;">{current_status_info['emoji']}</div>
        <h2 style="color: white; margin: 1rem 0;">{current_status_info['name']}</h2>
        <p style="font-size: 1.2rem; opacity: 0.9;">{current_status_info['description']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Order details
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📋 Order Details")
        st.write(f"**Order #:** {order[0]}")
        st.write(f"**Customer:** {order[2]}")
        st.write(f"**Type:** {order[3].replace('-', ' ').title()}")
        if order[4]:  # table number
            st.write(f"**Table:** {order[4]}")
        st.write(f"**Payment:** {order[11].title()}")
    
    with col2:
        st.markdown("### 💰 Order Summary")
        st.write(f"**Total:** R {order[6]:.2f}")
        st.write(f"**Order Time:** {order[7]}")
        st.write(f"**Items:** {order[12]}" if len(order) > 12 else "**Items:** Loading...")
        if order[9]:  # notes
            st.write(f"**Notes:** {order[9]}")
    
    # Progress tracker
    st.markdown("### 🚀 Order Progress")
    statuses = ['pending', 'confirmed', 'preparing', 'ready', 'completed']
    if order[3] == 'takeaway':
        statuses = ['pending', 'confirmed', 'preparing', 'ready', 'collected']
    
    current_index = statuses.index(current_status) if current_status in statuses else 0
    
    # Progress bar
    progress = current_index / (len(statuses) - 1)
    st.progress(progress)
    st.write(f"**Progress:** {int(progress * 100)}% complete")
    
    # Status timeline
    cols = st.columns(len(statuses))
    for i, status in enumerate(statuses):
        status_info = status_flow[status]
        with cols[i]:
            if i < current_index:
                # Completed
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem; background: #4CAF50; color: white; border-radius: 10px;">
                    <div style="font-size: 1.5rem;">✅</div>
                    <div><strong>{status_info['name']}</strong></div>
                </div>
                """, unsafe_allow_html=True)
            elif i == current_index:
                # Current
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem; background: {status_info['color']}; color: white; border-radius: 10px; border: 3px solid #FFD700;">
                    <div style="font-size: 1.5rem;">{status_info['emoji']}</div>
                    <div><strong>{status_info['name']}</strong></div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Upcoming
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem; background: #f0f0f0; color: #666; border-radius: 10px;">
                    <div style="font-size: 1.5rem;">⏳</div>
                    <div><strong>{status_info['name']}</strong></div>
                </div>
                """, unsafe_allow_html=True)
    
    # Special actions based on status
    if current_status == 'ready' and order[3] == 'takeaway':
        st.success("🎯 **Your order is ready for collection!**")
        st.info("📍 Please come to the counter to collect your order")
        
        if st.button("📦 I've Collected My Order", type="primary"):
            db.update_order_status(order[0], 'collected', 'Customer collected order')
            st.success("🎉 Thank you! Enjoy your meal!")
            time.sleep(2)
            st.rerun()
    
    # Refresh controls
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("🔄 **Live tracking active** - Updates every 2 seconds")
        st.write(f"**Last checked:** {get_sa_time().strftime('%H:%M:%S')} SAST")
    with col2:
        if st.button("🔄 Refresh Now"):
            st.rerun()

# PREMIUM KITCHEN DASHBOARD
def premium_kitchen_dashboard():
    st.title("👨‍🍳 Premium Kitchen Dashboard")
    st.markdown("### 🚀 Real-Time Order Management")
    
    # Auto-refresh controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.info("🔄 **Live Updates Active** - Real-time order synchronization")
    with col2:
        auto_refresh = st.checkbox("Auto Refresh", value=True, key="kitchen_auto_refresh")
    with col3:
        refresh_rate = st.selectbox("Rate", [2, 5, 10], index=0, key="kitchen_refresh_rate")
    
    # Auto-refresh logic
    if auto_refresh and (time.time() - st.session_state.last_order_check > refresh_rate):
        st.session_state.last_order_check = time.time()
        st.rerun()
    
    # Real-time stats
    st.subheader("📊 Live Kitchen Metrics")
    
    try:
        orders = db.get_active_orders()
        status_counts = {}
        for order in orders:
            status = order[5]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        metrics_cols = st.columns(4)
        status_display = {
            'pending': '⏳ Pending',
            'confirmed': '✅ Confirmed', 
            'preparing': '👨‍🍳 Preparing',
            'ready': '🎯 Ready'
        }
        
        for i, (status, display) in enumerate(status_display.items()):
            with metrics_cols[i]:
                count = status_counts.get(status, 0)
                st.metric(display, count)
    except:
        st.error("Error loading kitchen metrics")
    
    # Kitchen orders by status
    st.markdown("---")
    
    if not orders:
        st.success("🎉 All caught up! No active orders.")
        return
    
    # Create tabs for different statuses
    tab1, tab2, tab3, tab4 = st.tabs([
        f"⏳ Pending ({status_counts.get('pending', 0)})",
        f"✅ Confirmed ({status_counts.get('confirmed', 0)})", 
        f"👨‍🍳 Preparing ({status_counts.get('preparing', 0)})",
        f"🎯 Ready ({status_counts.get('ready', 0)})"
    ])
    
    with tab1:
        display_kitchen_orders(orders, 'pending')
    with tab2:
        display_kitchen_orders(orders, 'confirmed')
    with tab3:
        display_kitchen_orders(orders, 'preparing')
    with tab4:
        display_kitchen_orders(orders, 'ready')

def display_kitchen_orders(orders, status):
    """Display orders for kitchen staff with quick actions"""
    filtered_orders = [order for order in orders if order[5] == status]
    
    if not filtered_orders:
        st.info(f"📭 No {status} orders")
        return
    
    for order in filtered_orders:
        with st.container():
            st.markdown(f"""
            <div style="border: 2px solid #e0e0e0; border-radius: 15px; padding: 1.5rem; margin: 1rem 0;">
                <h3>Order #{order[0]} - {order[2]}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Token:** `{order[9]}`")
                st.write(f"**Type:** {order[3].replace('-', ' ').title()}")
                if order[4]:
                    st.write(f"**Table:** {order[4]}")
                st.write(f"**Items:** {order[12]}" if len(order) > 12 else "Loading items...")
                st.write(f"**Total:** R {order[6]:.2f}")
                st.write(f"**Time:** {order[7]}")
                if order[10]:
                    st.write(f"**Notes:** {order[10]}")
            
            with col2:
                st.write("### 🔄 Quick Actions")
                
                # Status progression buttons
                if status == 'pending':
                    if st.button("✅ Confirm Order", key=f"confirm_{order[0]}", use_container_width=True):
                        db.update_order_status(order[0], 'confirmed', 'Order confirmed by kitchen')
                        st.success("Order confirmed!")
                        time.sleep(1)
                        st.rerun()
                
                elif status == 'confirmed':
                    if st.button("👨‍🍳 Start Preparing", key=f"prep_{order[0]}", use_container_width=True):
                        db.update_order_status(order[0], 'preparing', 'Food preparation started')
                        st.success("Preparation started!")
                        time.sleep(1)
                        st.rerun()
                
                elif status == 'preparing':
                    if st.button("🎯 Mark Ready", key=f"ready_{order[0]}", use_container_width=True):
                        db.update_order_status(order[0], 'ready', 'Order ready for service')
                        st.success("Order marked as ready!")
                        time.sleep(1)
                        st.rerun()
                
                elif status == 'ready':
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Complete", key=f"complete_{order[0]}"):
                            db.update_order_status(order[0], 'completed', 'Order completed')
                            st.success("Order completed!")
                            time.sleep(1)
                            st.rerun()
                    with col2:
                        if st.button("📦 Collected", key=f"collected_{order[0]}"):
                            db.update_order_status(order[0], 'collected', 'Order collected by customer')
                            st.success("Order collected!")
                            time.sleep(1)
                            st.rerun()
                
                # Advanced status control
                st.write("**Advanced Control:**")
                all_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'completed', 'collected']
                current_index = all_statuses.index(status) if status in all_statuses else 0
                
                new_status = st.selectbox("Set status:", all_statuses, index=current_index, key=f"adv_{order[0]}")
                
                if st.button("🔄 Update Status", key=f"update_{order[0]}"):
                    db.update_order_status(order[0], new_status, f"Status updated to {new_status}")
                    st.success(f"Status updated to {new_status}!")
                    time.sleep(1)
                    st.rerun()
            
            st.markdown("---")

# PREMIUM ANALYTICS DASHBOARD
def premium_analytics_dashboard():
    st.title("📊 Premium Analytics Dashboard")
    st.markdown("### 🚀 Real Business Intelligence")
    
    # Time period selector
    st.sidebar.markdown("### 📈 Analytics Settings")
    days = st.sidebar.selectbox("Time Period", [7, 30, 90, 365], index=1, key="analytics_days")
    
    # Get REAL analytics data
    analytics_data = db.get_real_analytics(days)
    
    if not analytics_data:
        st.warning("📊 **No data available yet** - Analytics will populate as orders are processed")
        return
    
    # Extract data
    totals = analytics_data['totals']
    daily_trend = analytics_data['daily_trend']
    hourly_data = analytics_data['hourly_data']
    popular_dishes = analytics_data['popular_dishes']
    category_distribution = analytics_data['category_distribution']
    payment_distribution = analytics_data['payment_distribution']
    order_type_distribution = analytics_data['order_type_distribution']
    
    # Key Metrics
    st.subheader("🎯 Key Performance Indicators")
    
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.metric("📦 Total Orders", f"{totals[0]:,}")
    with kpi_cols[1]:
        st.metric("💰 Total Revenue", f"R {totals[1]:,.0f}")
    with kpi_cols[2]:
        st.metric("📊 Average Order", f"R {totals[2]:.0f}")
    with kpi_cols[3]:
        today_orders = db.get_todays_orders_count()
        st.metric("📅 Today's Orders", today_orders)
    
    # Revenue Trend Chart (REAL DATA)
    if daily_trend:
        st.subheader("📈 Daily Revenue Trend")
        daily_df = pd.DataFrame(daily_trend, columns=['Date', 'Orders', 'Revenue'])
        daily_df['Date'] = pd.to_datetime(daily_df['Date'])
        
        fig = px.line(daily_df, x='Date', y='Revenue', title='Daily Revenue Trend',
                     labels={'Revenue': 'Revenue (R)', 'Date': 'Date'})
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    
    # Popular Dishes Bar Chart (REAL DATA)
    if popular_dishes:
        st.subheader("🍽️ Top Selling Dishes")
        dishes_df = pd.DataFrame(popular_dishes, columns=['Dish', 'Quantity', 'Revenue', 'Orders'])
        
        fig = px.bar(dishes_df.head(8), x='Dish', y='Quantity', title='Most Popular Items by Quantity',
                    color='Quantity', color_continuous_scale='Viridis')
        fig.update_layout(xaxis_tickangle=-45, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    
    # Category Distribution Pie Chart (REAL DATA)
    if category_distribution:
        st.subheader("🥧 Revenue by Category")
        category_df = pd.DataFrame(category_distribution, columns=['Category', 'Quantity', 'Revenue', 'Orders'])
        
        fig = px.pie(category_df, values='Revenue', names='Category', title='Revenue Distribution by Category',
                    color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    
    # Business Insights
    st.markdown("---")
    st.subheader("💡 Business Insights")
    
    if hourly_data and popular_dishes:
        # Peak hours insight
        hourly_df = pd.DataFrame(hourly_data, columns=['Hour', 'Orders', 'Revenue'])
        peak_hour = hourly_df.loc[hourly_df['Revenue'].idxmax()]
        
        # Best selling item
        best_seller = popular_dishes[0][0] if popular_dishes else "No data"
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"""
            **📊 Peak Performance**
            - Busiest Hour: {peak_hour['Hour']}:00
            - Peak Revenue: R {peak_hour['Revenue']:,.0f}
            - Orders: {peak_hour['Orders']}
            """)
        
        with col2:
            st.success(f"""
            **🏆 Customer Favorites**
            - Best Seller: {best_seller}
            - Total Items Sold: {sum([dish[1] for dish in popular_dishes])}
            - Unique Dishes Ordered: {len(popular_dishes)}
            """)

# PREMIUM STAFF NAVIGATION
def premium_staff_navigation():
    st.sidebar.title("👨‍💼 Premium Staff Portal")
    
    # User info
    if st.session_state.user:
        user_role = st.session_state.user[3]
        st.sidebar.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
            <h4 style="margin: 0; color: white;">Welcome, {st.session_state.user[1]}!</h4>
            <p style="margin: 0; opacity: 0.9;">Role: {user_role.title()}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Navigation
    st.sidebar.markdown("---")
    pages = ["👨‍🍳 Kitchen Dashboard", "📊 Analytics"]
    if st.session_state.role == 'admin':
        pages.append("👥 Staff Management")
    
    selected_page = st.sidebar.radio("**Navigation**", pages)
    
    # Quick actions
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Quick Actions")
    if st.sidebar.button("🔄 Refresh All", use_container_width=True):
        st.rerun()
    
    # Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", type="primary", use_container_width=True):
        logout()
    
    # Page routing
    if selected_page == "👨‍🍳 Kitchen Dashboard":
        premium_kitchen_dashboard()
    elif selected_page == "📊 Analytics":
        premium_analytics_dashboard()
    elif selected_page == "👥 Staff Management":
        staff_management()

def staff_management():
    st.title("👥 Staff Management")
    st.info("Admin-only feature for managing staff accounts")

# MAIN APPLICATION
def main():
    # Initialize session state
    init_session_state()
    
    # Set page config
    st.set_page_config(
        page_title="Taste Restaurant - Premium",
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
    </style>
    """, unsafe_allow_html=True)
    
    # Main navigation
    if st.session_state.logged_in:
        premium_staff_navigation()
    else:
        # Customer interface
        st.sidebar.title("🍽️ Taste Restaurant")
        st.sidebar.markdown("---")
        
        # Customer navigation
        nav_options = ["🏠 Home", "🍕 Place Order", "📱 Track Order"]
        selected_nav = st.sidebar.radio("**Customer**", nav_options)
        
        # Staff login
        staff_login()
        
        # QR Code for mobile
        st.sidebar.markdown("---")
        st.sidebar.subheader("📱 Mobile Ordering")
        try:
            qr_url = "https://taste-restaurant.streamlit.app"
            qr_img = generate_qr_code(qr_url)
            st.sidebar.image(f"data:image/png;base64,{qr_img}", 
                           caption="Scan to order from your phone",
                           use_container_width=True)
        except:
            st.sidebar.info("QR Code for mobile ordering")
        
        # Main content
        if selected_nav == "🏠 Home":
            show_premium_landing()
        elif selected_nav == "🍕 Place Order":
            customer_ordering()
        elif selected_nav == "📱 Track Order":
            track_order_live()

def show_premium_landing():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 4rem 2rem; border-radius: 20px; color: white; text-align: center;">
        <h1 style="font-size: 4rem; margin-bottom: 1rem;">🍽️ TASTE RESTAURANT</h1>
        <p style="font-size: 1.5rem; opacity: 0.9;">Premium Dining • Real-Time Tracking • Exceptional Service</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <br>
    <div style="text-align: center;">
        <h2>🚀 Experience the Future of Dining</h2>
        <p>Order seamlessly, track in real-time, and enjoy premium service</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <div style="font-size: 3rem;">📱</div>
            <h3>Mobile First</h3>
            <p>Order directly from your phone with our QR system</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <div style="font-size: 3rem;">⚡</div>
            <h3>Real-Time Tracking</h3>
            <p>Watch your meal being prepared live</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <div style="font-size: 3rem;">📊</div>
            <h3>Smart Analytics</h3>
            <p>Data-driven insights for better service</p>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("🚀 Start Your Order Now", type="primary", use_container_width=True):
        st.session_state.current_page = "order"
        st.session_state.current_step = "order_type"
        st.rerun()

if __name__ == "__main__":
    main()