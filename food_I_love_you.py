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

# Database setup with migration support
class RestaurantDB:
    def __init__(self, db_name="restaurant.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Check if tables exist and create if they don't
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            self.create_fresh_tables()
        else:
            # Check for missing columns and add them
            self.update_tables()
        
        self.insert_default_data()
    
    def update_tables(self):
        cursor = self.conn.cursor()
        
        # Check orders table columns
        cursor.execute("PRAGMA table_info(orders)")
        order_columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns to orders table
        if 'order_token' not in order_columns:
            cursor.execute('ALTER TABLE orders ADD COLUMN order_token TEXT UNIQUE')
        
        # Check menu_items table columns
        cursor.execute("PRAGMA table_info(menu_items)")
        menu_columns = [column[1] for column in cursor.fetchall()]
        
        if 'image_url' not in menu_columns:
            cursor.execute('ALTER TABLE menu_items ADD COLUMN image_url TEXT')
        
        self.conn.commit()
    
    def create_fresh_tables(self):
        cursor = self.conn.cursor()
        
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
        
        # Orders table - simplified without customer_phone
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
                order_token TEXT UNIQUE
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
        
        # Check if menu items already exist
        cursor.execute('SELECT COUNT(*) FROM menu_items')
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insert sample menu items only if table is empty
            sample_items = [
                ('Truffle Pasta', 'Creamy pasta with black truffle and parmesan cheese', 245, 'Main Course', 'https://images.unsplash.com/photo-1563379926898-05f4575a45d8?ixlib=rb-4.0.3&w=400'),
                ('Grilled Salmon', 'Atlantic salmon with lemon butter sauce and vegetables', 320, 'Main Course', 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?ixlib=rb-4.0.3&w=400'),
                ('Caesar Salad', 'Fresh romaine lettuce with caesar dressing and croutons', 95, 'Appetizer', 'https://images.unsplash.com/photo-1546793665-c74683f339c1?ixlib=rb-4.0.3&w=400'),
                ('Margherita Pizza', 'Classic pizza with tomato sauce and fresh mozzarella', 185, 'Main Course', 'https://images.unsplash.com/photo-1604068549290-dea0e4a305ca?ixlib=rb-4.0.3&w=400'),
                ('Garlic Bread', 'Toasted bread with garlic butter and herbs', 45, 'Appetizer', 'https://images.unsplash.com/photo-1573140247632-f8fd74997d5c?ixlib=rb-4.0.3&w=400'),
                ('Chocolate Lava Cake', 'Warm chocolate cake with vanilla ice cream', 85, 'Dessert', 'https://images.unsplash.com/photo-1624353365286-3f8d62daad51?ixlib=rb-4.0.3&w=400'),
                ('Mojito', 'Fresh mint and lime cocktail with rum', 65, 'Beverage', 'https://images.unsplash.com/photo-1551538827-9c037cb4f32a?ixlib=rb-4.0.3&w=400'),
                ('Tiramisu', 'Italian coffee-flavored dessert with mascarpone', 75, 'Dessert', 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?ixlib=rb-4.0.3&w=400'),
                ('Cappuccino', 'Freshly brewed coffee with steamed milk foam', 35, 'Beverage', 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?ixlib=rb-4.0.3&w=400'),
                ('Beef Burger', 'Juicy beef patty with fresh vegetables and sauce', 165, 'Main Course', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?ixlib=rb-4.0.3&w=400')
            ]
            
            for item in sample_items:
                try:
                    cursor.execute('''
                        INSERT INTO menu_items (name, description, price, category, image_url)
                        VALUES (?, ?, ?, ?, ?)
                    ''', item)
                except sqlite3.IntegrityError:
                    pass
        
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
            
            # Weekly revenue by day of week
            cursor.execute('''
                SELECT 
                    strftime('%w', order_date) as weekday,
                    COUNT(*) as order_count,
                    COALESCE(SUM(total_amount), 0) as daily_revenue
                FROM orders 
                WHERE order_date >= date('now', '-' || ? || ' days')
                GROUP BY weekday
                ORDER BY weekday
            ''', (days,))
            weekly_data = cursor.fetchall()
            
            # Popular dishes
            cursor.execute('''
                SELECT 
                    oi.menu_item_name,
                    SUM(oi.quantity) as total_quantity,
                    COUNT(DISTINCT oi.order_id) as order_count
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.order_date >= date('now', '-' || ? || ' days')
                GROUP BY oi.menu_item_name
                ORDER BY total_quantity DESC
                LIMIT 10
            ''', (days,))
            popular_dishes = cursor.fetchall()
            
            # Category distribution (NEW - based on menu categories)
            cursor.execute('''
                SELECT 
                    mi.category,
                    SUM(oi.quantity) as total_quantity,
                    COUNT(DISTINCT oi.order_id) as order_count
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE o.order_date >= date('now', '-' || ? || ' days')
                GROUP BY mi.category
                ORDER BY total_quantity DESC
            ''', (days,))
            category_distribution = cursor.fetchall()
            
            return {
                'totals': totals,
                'daily_trend': daily_data,
                'weekly_revenue': weekly_data,
                'popular_dishes': popular_dishes,
                'category_distribution': category_distribution  # NEW
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
    
    def get_all_orders(self, status_filter=None):
        cursor = self.conn.cursor()
        query = '''
            SELECT o.*, 
                   GROUP_CONCAT(oi.menu_item_name || ' (x' || oi.quantity || ')', ', ') as items,
                   COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
        '''
        if status_filter:
            query += f" WHERE o.status = '{status_filter}'"
        query += " GROUP BY o.id ORDER BY o.order_date DESC"
        
        cursor.execute(query)
        return cursor.fetchall()
    
    def get_menu_items(self, category=None):
        cursor = self.conn.cursor()
        query = 'SELECT * FROM menu_items WHERE available = 1'
        if category:
            query += f" AND category = '{category}'"
        query += " ORDER BY category, name"
        
        cursor.execute(query)
        return cursor.fetchall()
    
    def add_order(self, customer_name, order_type, items, table_number=None, notes=""):
        cursor = self.conn.cursor()
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        # Generate unique order token
        order_token = f"ORD{random.randint(1000, 9999)}{int(time.time()) % 10000}"
        
        cursor.execute('''
            INSERT INTO orders (customer_name, order_type, table_number, total_amount, notes, order_token)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (customer_name, order_type, table_number, total_amount, notes, order_token))
        
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

# Initialize database
try:
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

# Device detection
def is_mobile_device():
    """Check if the user is on a mobile device"""
    try:
        # Streamlit doesn't directly provide user agent, so we'll use a simple approach
        # In production, you might want to use a more sophisticated method
        return False  # Default to non-mobile for development
    except:
        return False

# Authentication for staff
def staff_login():
    # Check if on mobile device and restrict staff login
    if is_mobile_device():
        st.sidebar.warning("📱 Staff login is not available on mobile devices. Please use a desktop or tablet.")
        return
    
    st.sidebar.title("Staff Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    
    if st.sidebar.button("Login"):
        if username and password:
            cursor = db.conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_password))
            user = cursor.fetchone()
            
            if user:
                st.session_state.user = user
                st.session_state.logged_in = True
                st.session_state.role = user[3]
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials")
        else:
            st.sidebar.warning("Please enter both username and password")

def logout():
    st.session_state.logged_in = False
    st.session_state.user = None
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

# Customer Ordering Interface
def customer_ordering():
    st.title("🍽️ Place Your Order")
    
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
    st.subheader("Choose Order Type")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏠 Dine In", use_container_width=True, key="dine_in_btn"):
            st.session_state.order_type = "dine-in"
            st.session_state.current_step = "customer_info"
            st.rerun()
    
    with col2:
        if st.button("🥡 Takeaway", use_container_width=True, key="takeaway_btn"):
            st.session_state.order_type = "takeaway"
            st.session_state.current_step = "customer_info"
            st.rerun()
    
    with col3:
        if st.button("🚚 Delivery", use_container_width=True, key="delivery_btn"):
            st.session_state.order_type = "delivery"
            st.session_state.current_step = "customer_info"
            st.rerun()
    
    st.write(f"Selected: **{st.session_state.order_type.title()}**")

def show_customer_info():
    st.subheader("Customer Information")
    
    with st.form("customer_info_form"):
        customer_name = st.text_input(
            "Your Name", 
            value=st.session_state.customer_name,
            placeholder="Enter your name",
            key="customer_name_input"
        )
        
        if st.session_state.order_type == "dine-in":
            table_number = st.number_input(
                "Table Number", 
                min_value=1, 
                max_value=50, 
                value=st.session_state.table_number,
                key="table_number_input"
            )
        else:
            table_number = None
        
        order_notes = st.text_area(
            "Special Instructions", 
            value=st.session_state.order_notes,
            placeholder="Any allergies or special requests...",
            key="order_notes_input"
        )
        
        submitted = st.form_submit_button("Continue to Menu")
        
        if submitted:
            if not customer_name:
                st.error("Please provide your name")
            else:
                # Store in session state
                st.session_state.customer_name = customer_name
                st.session_state.table_number = table_number
                st.session_state.order_notes = order_notes
                st.session_state.current_step = "menu"
                st.rerun()

def show_menu_selection():
    st.title("📋 Our Menu")
    
    # Menu categories
    categories = ['All', 'Appetizer', 'Main Course', 'Dessert', 'Beverage']
    selected_category = st.selectbox("Filter by Category", categories, key="category_filter")
    
    # Get menu items
    try:
        menu_items = db.get_menu_items(None if selected_category == 'All' else selected_category)
    except:
        # Fallback if database error
        menu_items = [
            (1, 'Truffle Pasta', 'Creamy pasta with black truffle and parmesan', 245, 'Main Course', 1, 'https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=400'),
            (2, 'Grilled Salmon', 'Atlantic salmon with lemon butter sauce', 320, 'Main Course', 1, 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400'),
            (3, 'Caesar Salad', 'Fresh romaine with caesar dressing', 95, 'Appetizer', 1, 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=400')
        ]
    
    # Display menu items in a grid
    cols = st.columns(2)
    for idx, item in enumerate(menu_items):
        with cols[idx % 2]:
            with st.container():
                st.markdown("---")
                
                # Display food image
                image_url = item[6] if len(item) > 6 and item[6] else "https://via.placeholder.com/300x200"
                try:
                    st.image(image_url, use_container_width=True)
                except:
                    st.image("https://via.placeholder.com/300x200", use_container_width=True)
                
                # Item details
                st.subheader(item[1])
                st.write(item[2])
                st.write(f"**R {item[3]}**")
                
                # Quantity and add to cart
                col1, col2 = st.columns(2)
                with col1:
                    quantity = st.number_input("Qty", min_value=0, max_value=10, key=f"qty_{item[0]}")
                with col2:
                    instructions = st.text_input("Instructions", key=f"inst_{item[0]}", placeholder="e.g., no onions")
                
                if quantity > 0:
                    if st.button("Add to Cart", key=f"add_{item[0]}"):
                        cart_item = {
                            'id': item[0],
                            'name': item[1],
                            'price': item[3],
                            'quantity': quantity,
                            'instructions': instructions
                        }
                        st.session_state.cart.append(cart_item)
                        st.success(f"Added {quantity} x {item[1]} to cart!")
                        st.rerun()
    
    # Display cart and navigation
    show_cart_and_navigation()

def show_cart_and_navigation():
    if st.session_state.cart:
        st.markdown("---")
        st.subheader("🛒 Your Order")
        
        total = 0
        for i, item in enumerate(st.session_state.cart):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{item['name']}**")
                if item['instructions']:
                    st.caption(f"Instructions: {item['instructions']}")
            with col2:
                st.write(f"R {item['price']}")
            with col3:
                st.write(f"Qty: {item['quantity']}")
            with col4:
                if st.button("❌", key=f"remove_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            total += item['price'] * item['quantity']
        
        st.write(f"### Total: R {total}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Customer Info", use_container_width=True):
                st.session_state.current_step = "customer_info"
                st.rerun()
        
        with col2:
            if st.button("📦 Place Order", type="primary", use_container_width=True):
                st.session_state.current_step = "confirmation"
                st.rerun()
    else:
        if st.button("← Back to Customer Info"):
            st.session_state.current_step = "customer_info"
            st.rerun()

def show_order_confirmation():
    st.title("📦 Order Confirmation")
    
    # Display order summary
    st.subheader("Order Summary")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Customer:** {st.session_state.customer_name}")
        st.write(f"**Order Type:** {st.session_state.order_type.title()}")
    
    with col2:
        if st.session_state.order_type == "dine-in":
            st.write(f"**Table:** {st.session_state.table_number}")
        if st.session_state.order_notes:
            st.write(f"**Notes:** {st.session_state.order_notes}")
    
    st.subheader("Order Items")
    total = 0
    for item in st.session_state.cart:
        item_total = item['price'] * item['quantity']
        total += item_total
        st.write(f"{item['quantity']} x {item['name']} - R {item_total}")
        if item['instructions']:
            st.caption(f"  Instructions: {item['instructions']}")
    
    st.write(f"**Total Amount: R {total}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("← Back to Menu", use_container_width=True):
            st.session_state.current_step = "menu"
            st.rerun()
    
    with col2:
        if st.button("✅ Confirm Order", type="primary", use_container_width=True):
            try:
                # Save order to database
                order_id, order_token = db.add_order(
                    st.session_state.customer_name,
                    st.session_state.order_type,
                    st.session_state.cart,
                    st.session_state.table_number,
                    st.session_state.order_notes
                )
                
                st.session_state.order_placed = True
                st.session_state.order_id = order_id
                st.session_state.order_token = order_token
                st.session_state.current_order_status = 'pending'
                
                # Clear cart after successful order
                st.session_state.cart = []
                
                st.session_state.current_step = "tracking"
                st.rerun()
                
            except Exception as e:
                st.error(f"Error placing order: {e}")
                st.error("Please try again or contact staff for assistance.")

def track_order():
    st.title("📱 Track Your Order")
    
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
        st.info("Enter your Order Token to track your order status")
        order_token = st.text_input("Order Token", placeholder="ORD123456789", key="track_order_input")
        
        if st.button("Track Order", key="track_order_btn"):
            if order_token:
                st.session_state.tracking_order_token = order_token
                st.session_state.tracking_order_placed = True
                st.rerun()
            else:
                st.error("Please enter an order token")

def display_order_tracking(order_token):
    try:
        # Get current order status for live updates
        current_status = db.get_order_status(order_token)
        
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
            # Status emoji mapping
            status_emoji = {
                'pending': '⏳',
                'preparing': '👨‍🍳',
                'ready': '✅',
                'completed': '🎉',
                'collected': '📦'
            }
            
            current_status = str(order[5]) if order[5] else 'pending'
            emoji = status_emoji.get(current_status, '📝')
            
            # Display real-time status header with visual feedback
            status_colors = {
                'pending': '#FFA500',  # Orange
                'preparing': '#1E90FF',  # Dodger Blue
                'ready': '#32CD32',  # Lime Green
                'completed': '#008000',  # Green
                'collected': '#4B0082'  # Indigo
            }
            
            status_color = status_colors.get(current_status, '#666666')
            
            st.markdown(f"""
            <div style="background-color: {status_color}; color: white; padding: 1rem; border-radius: 10px; text-align: center;">
                <h2 style="margin: 0; color: white;">{emoji} Order Status: {current_status.title()}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Order details
            st.subheader("📋 Order Details")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Order ID:** {order[0]}")
                st.write(f"**Customer:** {order[2]}")
                st.write(f"**Order Type:** {str(order[4]).title() if order[4] else 'N/A'}")
                st.write(f"**Order Token:** `{order_token}`")
            with col2:
                st.write(f"**Total:** R {order[6]}")
                st.write(f"**Order Date:** {order[7]}")
                if len(order) > 9 and order[9]:
                    st.write(f"**Notes:** {order[9]}")
            
            # Enhanced Real-time Progress Tracker
            st.subheader("🔄 Live Order Progress")
            
            status_flow = ['pending', 'preparing', 'ready', 'completed']
            order_type = str(order[4]) if order[4] else 'dine-in'
            if order_type == 'takeaway':
                status_flow[2] = 'ready for collection'
                status_flow[3] = 'collected'
            
            current_index = status_flow.index(current_status) if current_status in status_flow else 0
            
            # Progress bar with percentage
            progress = (current_index + 1) / len(status_flow)
            st.progress(progress)
            st.write(f"**Progress: {int(progress * 100)}%**")
            
            # Visual status steps with timestamps
            status_history = db.get_order_status_history(order[0])
            status_times = {}
            
            for status_entry in status_history:
                status_times[status_entry[2]] = status_entry[3]
            
            for i, status in enumerate(status_flow):
                status_time = status_times.get(status, '')
                time_display = f" - {status_time}" if status_time else ""
                
                if i < current_index:
                    st.success(f"✅ **{status.title()}** {time_display} - Completed")
                elif i == current_index:
                    st.info(f"🔄 **{status.title()}** {time_display} - In Progress")
                    # Show estimated time for current step
                    if status == 'preparing':
                        st.write("   *Estimated: 10-15 minutes*")
                    elif status == 'ready' or status == 'ready for collection':
                        st.write("   *Your order is ready!*")
                        st.balloons()
                else:
                    st.write(f"⏳ {status.title()} - Pending")
            
            # Order items with better formatting
            st.subheader("🍽️ Your Order Items")
            if order[8] and isinstance(order[8], str):
                items = order[8].split(',')
                for item in items:
                    st.write(f"• {item.strip()}")
            else:
                st.write("No items found in this order")
            
            # Special collection button for takeaway
            order_type = str(order[4]) if order[4] else 'dine-in'
            if order_type == 'takeaway' and current_status == 'ready for collection':
                st.success("🎯 **Your order is ready for collection!**")
                if st.button("🎯 I've Collected My Order", type="primary", key="collect_btn"):
                    try:
                        db.update_order_status(order[0], 'collected', 'Customer collected order')
                        st.success("Thank you! Order marked as collected. Enjoy your meal! 🍽️")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating order: {e}")
            
            # Auto-refresh for live updates
            st.markdown("---")
            refresh_container = st.container()
            with refresh_container:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info("🔄 **Live Tracking Active** - Status updates automatically")
                    st.write("Last checked: " + datetime.now().strftime("%H:%M:%S"))
                with col2:
                    if st.button("🔄 Refresh Now", key="refresh_btn"):
                        st.rerun()
            
            # Auto-refresh every 3 seconds for better real-time updates
            time.sleep(3)
            st.rerun()
                
        else:
            st.error("❌ Order not found. Please check your Order Token.")
            st.info("💡 Make sure you entered the correct Order Token from your order confirmation.")
            
    except Exception as e:
        st.error(f"Error tracking order: {e}")
        st.info("If this problem persists, please contact our staff for assistance.")

# Staff Dashboard Pages - FIXED ORDER MANAGEMENT
def staff_dashboard():
    st.title("👨‍💼 Staff Dashboard")
    
    # Quick stats - FIXED: Use today's orders only
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        pending_orders = len(db.get_all_orders('pending'))
        preparing_orders = len(db.get_all_orders('preparing'))
        ready_orders = len(db.get_all_orders('ready'))
        today_orders = db.get_todays_orders_count()  # Fixed: Only today's orders
    except:
        pending_orders = preparing_orders = ready_orders = today_orders = 0
    
    with col1:
        st.metric("Pending Orders", pending_orders)
    with col2:
        st.metric("Preparing", preparing_orders)
    with col3:
        st.metric("Ready", ready_orders)
    with col4:
        st.metric("Today's Orders", today_orders)
    
    # Recent orders with enhanced display - FIXED STATUS UPDATES
    st.subheader("📋 Recent Orders - Kitchen View")
    try:
        orders = db.get_all_orders()[:15]  # Show more orders
    except:
        orders = []
    
    if not orders:
        st.info("No orders found. Orders will appear here when customers place them.")
        return
    
    # Create a container for each order with proper status management
    for order in orders:
        order_id = order[0]
        table_num = order[1] if order[1] else ""
        customer_name = str(order[2]) if order[2] else "Unknown"
        order_type = str(order[4]) if order[4] else "dine-in"
        current_status = str(order[5]) if order[5] else "pending"
        total_amount = order[6] if order[6] else 0
        items = order[8] if len(order) > 8 and order[8] else "No items"
        notes = order[7] if len(order) > 7 and order[7] else ""
        
        # Status emoji
        status_emoji = {
            'pending': '⏳',
            'preparing': '👨‍🍳', 
            'ready': '✅',
            'completed': '🎉',
            'collected': '📦'
        }
        
        # Create expander for each order
        with st.expander(f"{status_emoji.get(current_status, '📝')} Order #{order_id} - {customer_name} - R{total_amount}", expanded=current_status in ['pending', 'preparing']):
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.write(f"**Customer:** {customer_name}")
                st.write(f"**Type:** {order_type.title()}")
                if order_type == 'dine-in' and table_num:
                    st.write(f"**Table:** {table_num}")
                st.write(f"**Items:** {items}")
                if notes:
                    st.write(f"**Notes:** {notes}")
                st.write(f"**Current Status:** **{current_status.title()}**")
            
            with col2:
                # Status update section
                st.write("### Update Status")
                
                # Create a unique key for this order's status selector
                status_key = f"status_select_{order_id}"
                
                # Status options
                status_options = ['pending', 'preparing', 'ready', 'completed', 'collected']
                current_index = status_options.index(current_status) if current_status in status_options else 0
                
                # Status selector
                new_status = st.selectbox(
                    "Select new status:",
                    status_options,
                    index=current_index,
                    key=status_key
                )
                
                # Update button
                update_key = f"update_btn_{order_id}"
                if st.button("Update Status", key=update_key, type="primary" if new_status != current_status else "secondary"):
                    try:
                        success = db.update_order_status(order_id, new_status, f"Status updated by staff")
                        if success:
                            st.success(f"✅ Order #{order_id} status updated to {new_status}!")
                            # Use a small delay and rerun to show the success message
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Failed to update status")
                    except Exception as e:
                        st.error(f"Error updating status: {str(e)}")

def analytics_dashboard():
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">📊 Restaurant Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Time period selector
    days = st.sidebar.selectbox("Select Time Period", [7, 30, 90], index=1)
    
    # Get real analytics data
    analytics_data = db.get_real_analytics(days)
    
    if not analytics_data:
        st.warning("No real data available yet. Analytics will show real data as orders are placed.")
        return
    
    totals = analytics_data['totals']
    daily_trend = analytics_data['daily_trend']
    weekly_revenue = analytics_data['weekly_revenue']
    popular_dishes = analytics_data['popular_dishes']
    category_distribution = analytics_data['category_distribution']  # NEW
    
    # Key Metrics
    st.subheader("📈 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_orders = totals[0] if totals else 0
        st.metric("Total Orders", total_orders)
    
    with col2:
        total_revenue = totals[1] if totals else 0
        st.metric("Total Revenue", f"R {total_revenue:,.0f}")
    
    with col3:
        avg_order_value = totals[2] if totals else 0
        st.metric("Average Order", f"R {avg_order_value:.0f}")
    
    with col4:
        if popular_dishes:
            most_popular = popular_dishes[0][0] if popular_dishes else "No data"
            st.metric("Most Popular", most_popular)
        else:
            st.metric("Most Popular", "No data")
    
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
        st.plotly_chart(fig_line, use_container_width=True)
    
    # Bar Chart - Weekly Revenue
    if weekly_revenue:
        st.subheader("📊 Weekly Revenue by Day")
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        weekly_df = pd.DataFrame(weekly_revenue, columns=['weekday', 'orders', 'revenue'])
        weekly_df['day_name'] = weekly_df['weekday'].apply(lambda x: day_names[int(x)])
        
        fig_bar = px.bar(
            weekly_df,
            x='day_name',
            y='revenue',
            title='Revenue by Day of Week',
            labels={'revenue': 'Revenue (R)', 'day_name': 'Day of Week'},
            color='revenue',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Pie Chart - Category Distribution (NEW - based on menu categories)
    if category_distribution:
        st.subheader("🥧 Menu Category Distribution")
        category_df = pd.DataFrame(category_distribution, columns=['category', 'quantity', 'orders'])
        
        # Category emojis for better visualization
        category_emojis = {
            'Main Course': '🍽️',
            'Appetizer': '🥗', 
            'Dessert': '🍰',
            'Beverage': '🥤'
        }
        
        # Add emojis to category names
        category_df['category_with_emoji'] = category_df['category'].apply(
            lambda x: f"{category_emojis.get(x, '📦')} {x}"
        )
        
        fig_pie = px.pie(
            category_df,
            values='quantity',
            names='category_with_emoji',
            title='Items Sold by Category',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
        # Also show category breakdown as bars
        st.subheader("📊 Category Performance")
        fig_category_bar = px.bar(
            category_df,
            x='category',
            y='quantity',
            color='category',
            title='Items Sold by Category',
            labels={'quantity': 'Items Sold', 'category': 'Menu Category'}
        )
        st.plotly_chart(fig_category_bar, use_container_width=True)
    
    # Popular Dishes Table
    if popular_dishes:
        st.subheader("🍽️ Popular Dishes")
        dishes_df = pd.DataFrame(popular_dishes, columns=['dish', 'quantity', 'orders'])
        dishes_df = dishes_df.head(5)  # Top 5 only
        
        # Display as a nice table
        for idx, row in dishes_df.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{row['dish']}**")
            with col2:
                st.write(f"🍽️ {row['orders']} orders")
            with col3:
                st.write(f"📦 {row['quantity']} sold")

# QR Code Management for Admin
def qr_management():
    st.title("📱 QR Code Management")
    
    st.markdown("""
    ### Generate QR Code for Customer Ordering
    
    Customers can scan this QR code to access the ordering system directly from their phones.
    Place this QR code at your restaurant entrance, tables, or counter for easy access.
    """)
    
    # Get the current URL (you might need to adjust this based on your deployment)
    # For local development
    ordering_url = "https://myfood.streamlit.app/"
    
    # For production, you would use your actual deployed URL
    # ordering_url = "https://your-restaurant-app.streamlit.app"
    
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
    
    st.markdown("---")
    st.subheader("📋 QR Code Best Practices")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**📍 Placement**")
        st.write("• Restaurant entrance")
        st.write("• Each table")
        st.write("• Counter/waiting area")
        st.write("• Takeaway packaging")
    
    with col2:
        st.write("**📱 Customer Experience**")
        st.write("• Ensure good lighting")
        st.write("• Keep QR code clean")
        st.write("• Test scanning regularly")
        st.write("• Provide instructions")
    
    with col3:
        st.write("**🖨️ Printing Tips**")
        st.write("• Use high contrast")
        st.write("• Minimum size: 2x2 inches")
        st.write("• Laminated for durability")
        st.write("• Multiple copies available")

# Main navigation for staff
def staff_navigation():
    st.sidebar.title(f"Staff Portal")
    st.sidebar.write(f"Welcome, {st.session_state.user[1]}!")
    
    if st.sidebar.button("Logout"):
        logout()
    
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Order Management", "Analytics", "QR Codes", "Menu Management"]
    )
    
    if page == "Dashboard":
        staff_dashboard()
    elif page == "Order Management":
        staff_dashboard()
    elif page == "Analytics":
        analytics_dashboard()
    elif page == "QR Codes":
        qr_management()
    elif page == "Menu Management":
        st.title("Menu Management")
        st.info("Menu management features coming soon...")

# Enhanced Landing Page with improved "How It Works"
def show_landing_page():
    st.markdown("""
    <style>
    .welcome-header {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem;
    }
    .welcome-subtitle {
        font-size: 1.5rem;
        color: #6c757d;
        text-align: center;
        margin-bottom: 3rem;
        font-weight: 300;
    }
    .step-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 0.5rem;
        border-left: 4px solid #667eea;
        height: 100%;
    }
    .step-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .step-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: #2c3e50;
    }
    .step-desc {
        font-size: 0.9rem;
        color: #6c757d;
    }
    .qr-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 2rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<h1 class="welcome-header">Welcome to Sanele Restaurant</h1>', unsafe_allow_html=True)
        st.markdown('<p class="welcome-subtitle">Experience culinary excellence with every bite</p>', unsafe_allow_html=True)
        
        st.markdown("""
        ### 🎯 Why Choose Us?
        - 🍽️ **Fresh Ingredients** - Locally sourced, always fresh
        - 👨‍🍳 **Expert Chefs** - Master chefs with years of experience
        - ⚡ **Quick Service** - Your order ready in minutes
        - 📱 **Live Tracking** - Watch your order being prepared in real-time
        """)
        
        if st.button("🍕 Start Your Order Now", type="primary", use_container_width=True):
            st.session_state.current_step = "order_type"
            st.rerun()
    
    with col2:
        st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3&w=400", 
                use_container_width=True, caption="Sanele Restaurant")
    
    # QR Code Section
    st.markdown("""
    <div class="qr-section">
        <h2>📱 Scan to Order</h2>
        <p>Use your phone camera to scan the QR code and order directly from your table!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display QR code on landing page
    ordering_url = "https://myfood.streamlit.app/"  # Adjust for production
    qr_img = generate_qr_code(ordering_url)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(f"data:image/png;base64,{qr_img}", width=250)
        st.caption("Scan with your phone camera to order")
    
    st.markdown("---")
    
    # Improved "How It Works" Section with smaller cards
    st.subheader("🚀 How It Works")
    
    steps = [
        {
            "icon": "📱", 
            "title": "Scan & Order", 
            "desc": "Scan QR code or visit our site",
            "image": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?ixlib=rb-4.0.3&w=200"
        },
        {
            "icon": "🛒", 
            "title": "Confirm", 
            "desc": "Review & confirm your order",
            "image": "https://images.unsplash.com/photo-1562428309-f97fc8e256e7?ixlib=rb-4.0.3&w=200"
        },
        {
            "icon": "👨‍🍳", 
            "title": "We Prepare", 
            "desc": "Chefs prepare with care",
            "image": "https://images.unsplash.com/photo-1555244162-803834f70033?ixlib=rb-4.0.3&w=200"
        },
        {
            "icon": "🎯", 
            "title": "Enjoy", 
            "desc": "Collect & enjoy your meal",
            "image": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?ixlib=rb-4.0.3&w=200"
        }
    ]
    
    # Create 4 columns for the steps
    cols = st.columns(4)
    
    for idx, step in enumerate(steps):
        with cols[idx]:
            # Display step image
            st.image(step['image'], use_container_width=True)
            
            # Display step card
            st.markdown(f"""
            <div class="step-card">
                <div class="step-icon">{step['icon']}</div>
                <div class="step-title">{step['title']}</div>
                <div class="step-desc">{step['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Restaurant Images Gallery
    st.markdown("---")
    st.subheader("🏛️ Sanele Restaurant")
    
    gallery_cols = st.columns(3)
    gallery_images = [
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3&w=400",
        "https://images.unsplash.com/photo-1559329007-40df8a9345d8?ixlib=rb-4.0.3&w=400",
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?ixlib=rb-4.3&w=400"
    ]
    
    for idx, col in enumerate(gallery_cols):
        with col:
            st.image(gallery_images[idx], use_container_width=True, 
                    caption=["Elegant Dining Area", "Modern Kitchen", "Cozy Atmosphere"][idx])

# Main app
def main():
    st.set_page_config(
        page_title="Sanele Restaurant",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Main navigation - Customer vs Staff
    st.sidebar.title("🍽️ Sanele Restaurant")
    
    # Mobile device detection
    is_mobile = is_mobile_device()
    
    if st.session_state.logged_in:
        # Staff interface
        staff_navigation()
    else:
        # Customer interface or staff login
        app_options = ["🏠 Home", "Place an Order 🍕", "Track My Order 📱"]
        
        # Only show staff login on non-mobile devices
        if not is_mobile:
            app_options.append("Staff Login 👨‍💼")
        else:
            st.sidebar.info("📱 Mobile-friendly ordering available")
        
        app_mode = st.sidebar.radio("I want to:", app_options)
        
        if app_mode == "🏠 Home":
            show_landing_page()
        elif app_mode == "Place an Order 🍕":
            customer_ordering()
        elif app_mode == "Track My Order 📱":
            track_order()
        elif app_mode == "Staff Login 👨‍💼" and not is_mobile:
            staff_login()
            if not st.session_state.logged_in:
                show_landing_page()

if __name__ == "__main__":
    main()