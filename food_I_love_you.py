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
    
    def get_recent_orders(self, limit=20):
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
    
    def add_order(self, customer_name, order_type, items, table_number=None, notes=""):
        cursor = self.conn.cursor()
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        # Generate unique order token
        order_token = f"ORD{random.randint(1000, 9999)}{int(time.time()) % 10000}"
        
        # Use current timestamp for order date
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO orders (customer_name, order_type, table_number, total_amount, notes, order_token, order_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (customer_name, order_type, table_number, total_amount, notes, order_token, current_time))
        
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
    href = f'<a href="data:image/png;base64,{img_str}" download="{filename}" style="display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Download QR Code</a>'
    return href

# Smart Device Detection
def is_mobile_device():
    """Smart detection for mobile devices"""
    try:
        # Simple approach - you can enhance this based on your needs
        return False  # Default to desktop for now
    except:
        return False

# Authentication for staff
def staff_login():
    st.sidebar.title("Staff Portal")
    st.sidebar.markdown("---")
    
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    
    if st.sidebar.button("Login", type="primary", use_container_width=True):
        if username and password:
            cursor = db.conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_password))
            user = cursor.fetchone()
            
            if user:
                st.session_state.user = user
                st.session_state.logged_in = True
                st.session_state.role = user[3]
                st.sidebar.success(f"Welcome back, {user[1]}!")
                time.sleep(1)
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials")
        else:
            st.sidebar.warning("Please enter both username and password")

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
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="order-header"><h1>Place Your Order</h1><p>Fresh food made with love, delivered fast</p></div>', unsafe_allow_html=True)
    
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
    st.subheader("Choose Your Experience")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3&w=300", use_container_width=True)
        if st.button("Dine In", use_container_width=True, key="dine_in_btn"):
            st.session_state.order_type = "dine-in"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("Enjoy our cozy atmosphere")
    
    with col2:
        st.image("https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?ixlib=rb-4.0.3&w=300", use_container_width=True)
        if st.button("Takeaway", use_container_width=True, key="takeaway_btn"):
            st.session_state.order_type = "takeaway"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("Pick up and enjoy elsewhere")
    
    with col3:
        st.image("https://images.unsplash.com/photo-1504674900247-0877df9cc836?ixlib=rb-4.0.3&w=300", use_container_width=True)
        if st.button("Delivery", use_container_width=True, key="delivery_btn"):
            st.session_state.order_type = "delivery"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("We bring it to your door")

def show_customer_info():
    st.subheader("Customer Information")
    
    with st.form("customer_info_form"):
        customer_name = st.text_input(
            "Your Name", 
            value=st.session_state.customer_name,
            placeholder="Enter your full name",
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
            placeholder="Any allergies, dietary restrictions, or special requests...",
            key="order_notes_input",
            height=100
        )
        
        submitted = st.form_submit_button("Continue to Menu", type="primary")
        
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
    </style>
    """, unsafe_allow_html=True)
    
    st.subheader("Our Menu")
    
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
    
    # Display menu items
    for item in menu_items:
        with st.container():
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Display food image
                image_url = item[6] if len(item) > 6 and item[6] else "https://via.placeholder.com/300x200"
                try:
                    st.image(image_url, use_container_width=True)
                except:
                    st.image("https://via.placeholder.com/300x200", use_container_width=True)
            
            with col2:
                st.subheader(item[1])
                st.write(f"_{item[2]}_")
                st.write(f"**R {item[3]}**")
                
                # Quantity and add to cart
                col_a, col_b, col_c = st.columns([1, 2, 1])
                with col_a:
                    quantity = st.number_input("Qty", min_value=0, max_value=10, key=f"qty_{item[0]}")
                with col_b:
                    instructions = st.text_input("Special requests", key=f"inst_{item[0]}", placeholder="e.g., no onions, extra sauce")
                with col_c:
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
        st.subheader("Your Order")
        
        total = 0
        for i, item in enumerate(st.session_state.cart):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{item['name']}**")
                if item['instructions']:
                    st.caption(f"_{item['instructions']}_")
            with col2:
                st.write(f"R {item['price']}")
            with col3:
                st.write(f"x{item['quantity']}")
            with col4:
                if st.button("Remove", key=f"remove_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            total += item['price'] * item['quantity']
        
        st.markdown(f"### Total: R {total}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Info", use_container_width=True):
                st.session_state.current_step = "customer_info"
                st.rerun()
        
        with col2:
            if st.button("Place Order", type="primary", use_container_width=True):
                st.session_state.current_step = "confirmation"
                st.rerun()
    else:
        if st.button("Back to Customer Info"):
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
    
    st.title("Order Confirmation")
    
    with st.container():
        st.markdown('<div class="confirmation-box">', unsafe_allow_html=True)
        
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
            st.write(f"• **{item['quantity']}x {item['name']}** - R {item_total}")
            if item['instructions']:
                st.caption(f"  _{item['instructions']}_")
        
        st.markdown(f"### **Total Amount: R {total}**")
        st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Back to Menu", use_container_width=True):
            st.session_state.current_step = "menu"
            st.rerun()
    
    with col2:
        if st.button("Confirm Order", type="primary", use_container_width=True):
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
    
    st.markdown('<div class="tracking-header"><h1>Track Your Order</h1><p>Watch your meal being prepared in real-time</p></div>', unsafe_allow_html=True)
    
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
        
        if st.button("Track Order", type="primary", key="track_order_btn"):
            if order_token:
                st.session_state.tracking_order_token = order_token
                st.session_state.tracking_order_placed = True
                st.rerun()
            else:
                st.error("Please enter your order token")

def display_order_tracking(order_token):
    try:
        # Get current order status for live updates
        current_status = db.get_order_status(order_token)
        
        if not current_status:
            st.error("Order not found. Please check your Order Token.")
            st.info("Make sure you entered the correct Order Token from your order confirmation.")
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
                <h2 style="margin: 10px 0; color: white;">{current_status_info['name']}</h2>
                <p style="margin: 0; font-size: 1.2rem; opacity: 0.9;">{current_status_info['description']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Order details
            st.subheader("Order Details")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Order ID:** {order[0]}")
                st.write(f"**Customer:** {order[2]}")
                st.write(f"**Order Type:** {str(order[4]).title() if order[4] else 'N/A'}")
            with col2:
                st.write(f"**Total:** R {order[6]}")
                st.write(f"**Order Date:** {order[7]}")
                if len(order) > 9 and order[9]:
                    st.write(f"**Notes:** {order[9]}")
            
            # Enhanced Real-time Progress Tracker
            st.subheader("Order Progress")
            
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
            st.write(f"**Progress: {int(progress * 100)}%**")
            
            # Visual status steps
            cols = st.columns(len(status_flow))
            
            for i, (status, status_name) in enumerate(zip(status_flow, status_names)):
                status_info = status_config.get(status, status_config['pending'])
                
                with cols[i]:
                    if i < current_index:
                        # Completed step
                        st.markdown(f"""
                        <div style="text-align: center; padding: 15px; background: #4CAF50; color: white; border-radius: 10px; margin: 5px;">
                            <strong>{status_name}</strong>
                            <div style="font-size: 0.8rem; opacity: 0.9;">Completed</div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif i == current_index:
                        # Current step
                        st.markdown(f"""
                        <div style="text-align: center; padding: 15px; background: {status_info['color']}; color: white; border-radius: 10px; margin: 5px; border: 3px solid #FFD700;">
                            <strong>{status_name}</strong>
                            <div style="font-size: 0.8rem; opacity: 0.9;">In Progress</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Show estimated time for current step
                        if status == 'preparing':
                            st.info("Estimated time: 10-15 minutes")
                        elif status == 'ready':
                            st.success("Your order is ready!")
                    else:
                        # Future step
                        st.markdown(f"""
                        <div style="text-align: center; padding: 15px; background: #f0f0f0; color: #666; border-radius: 10px; margin: 5px;">
                            <strong>{status_name}</strong>
                            <div style="font-size: 0.8rem; opacity: 0.9;">Upcoming</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Order items
            st.subheader("Your Order Items")
            if order[8] and isinstance(order[8], str):
                items = order[8].split(',')
                for item in items:
                    st.write(f"• {item.strip()}")
            else:
                st.write("No items found in this order")
            
            # Special collection button for takeaway
            order_type = str(order[4]) if order[4] else 'dine-in'
            if order_type == 'takeaway' and current_status == 'ready':
                st.success("Your order is ready for collection!")
                st.info("Please come to the counter to collect your order")
                
                if st.button("I've Collected My Order", type="primary", key="collect_btn"):
                    try:
                        db.update_order_status(order[0], 'collected', 'Customer collected order')
                        st.success("Thank you! Order marked as collected. Enjoy your meal!")
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
                    st.info("Live Tracking Active - Status updates automatically")
                    st.write(f"Last checked: {datetime.now().strftime('%H:%M:%S')}")
                with col2:
                    if st.button("Refresh Now", key="refresh_btn"):
                        st.rerun()
            
            # Auto-refresh every 3 seconds for better real-time updates
            time.sleep(3)
            st.rerun()
                
        else:
            st.error("Order not found. Please check your Order Token.")
            st.info("Make sure you entered the correct Order Token from your order confirmation.")
            
    except Exception as e:
        st.error(f"Error tracking order: {e}")
        st.info("If this problem persists, please contact our staff for assistance.")

# Enhanced Landing Page
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
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 1rem;
        border-left: 5px solid #667eea;
        transition: transform 0.3s ease;
    }
    .feature-card:hover {
        transform: translateY(-5px);
    }
    .step-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <h1 style="font-size: 3.5rem; margin-bottom: 1rem;">Sanele Restaurant</h1>
        <p style="font-size: 1.5rem; margin-bottom: 2rem; opacity: 0.9;">Experience culinary excellence with every bite</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Call to Action
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        ## Why Choose Sanele?
        
        We're not just another restaurant - we're an experience. Our commitment to quality, 
        speed, and customer satisfaction sets us apart from the rest.
        """)
        
        if st.button("Start Your Order Now", type="primary", use_container_width=True):
            st.session_state.current_step = "order_type"
            st.session_state.current_page = "order"
            st.rerun()
    
    with col2:
        st.image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-4.0.3&w=400", 
                use_container_width=True, caption="Our Restaurant")
    
    # Features Grid
    st.markdown("---")
    st.subheader("What Makes Us Special")
    
    features = st.columns(3)
    
    with features[0]:
        st.markdown("""
        <div class="feature-card">
            <h3>Fresh & Local</h3>
            <p>We source ingredients locally to ensure the freshest flavors in every dish</p>
        </div>
        """, unsafe_allow_html=True)
    
    with features[1]:
        st.markdown("""
        <div class="feature-card">
            <h3>Fast Service</h3>
            <p>Average preparation time of just 15 minutes. Your hunger won't wait!</p>
        </div>
        """, unsafe_allow_html=True)
    
    with features[2]:
        st.markdown("""
        <div class="feature-card">
            <h3>Live Tracking</h3>
            <p>Watch your order being prepared in real-time. No more guessing!</p>
        </div>
        """, unsafe_allow_html=True)
    
    # How It Works
    st.markdown("---")
    st.subheader("How It Works")
    
    steps = st.columns(4)
    
    step_data = [
        {"title": "Browse Menu", "desc": "Use your phone to browse our menu"},
        {"title": "Add Items", "desc": "Select your favorite dishes"},
        {"title": "We Prepare", "desc": "Our chefs cook with passion"},
        {"title": "Enjoy", "desc": "Collect and savor every bite"}
    ]
    
    for idx, step in enumerate(steps):
        with step:
            data = step_data[idx]
            st.markdown(f"""
            <div class="step-card">
                <h4>{data['title']}</h4>
                <p style="font-size: 0.9rem; color: #666;">{data['desc']}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Restaurant Gallery
    st.markdown("---")
    st.subheader("Our Restaurant")
    
    gallery = st.columns(3)
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
    st.title("Kitchen Dashboard")
    
    # Auto-refresh every 5 seconds
    if time.time() - st.session_state.last_order_check > 5:
        st.session_state.last_order_check = time.time()
        st.rerun()
    
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
        st.metric("Pending Orders", pending_orders)
    with col2:
        st.metric("Preparing", preparing_orders)
    with col3:
        st.metric("Ready", ready_orders)
    with col4:
        st.metric("Today's Orders", today_orders)
    
    # Recent orders with enhanced display
    st.subheader("Recent Orders")
    try:
        orders = db.get_recent_orders(20)
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
        order_time = order[7] if order[7] else "Unknown"
        items = order[8] if len(order) > 8 and order[8] else "No items"
        notes = order[7] if len(order) > 7 and order[7] else ""
        
        # Status colors
        status_colors = {
            'pending': '#FFA500',
            'preparing': '#1E90FF', 
            'ready': '#32CD32',
            'completed': '#008000',
            'collected': '#4B0082'
        }
        
        status_color = status_colors.get(current_status, '#666666')
        
        # Create expander for each order
        with st.expander(f"Order #{order_id} - {customer_name} - R{total_amount} - {current_status.title()}", expanded=current_status in ['pending', 'preparing']):
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.write(f"**Customer:** {customer_name}")
                st.write(f"**Type:** {order_type.title()}")
                if order_type == 'dine-in' and table_num:
                    st.write(f"**Table:** {table_num}")
                st.write(f"**Time:** {order_time}")
                st.write(f"**Items:** {items}")
                if notes:
                    st.write(f"**Notes:** {notes}")
                st.write(f"**Current Status:** **{current_status.title()}**")
            
            with col2:
                # Status update section
                st.write("Update Status")
                
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
                if st.button("Update Status", key=f"update_btn_{order_id}", type="primary" if new_status != current_status else "secondary"):
                    try:
                        success = db.update_order_status(order_id, new_status, f"Status updated by staff")
                        if success:
                            st.success(f"Order #{order_id} status updated to {new_status}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to update status")
                    except Exception as e:
                        st.error(f"Error updating status: {str(e)}")

# QR Code Management for Staff Only
def qr_management():
    st.title("QR Code Management")
    
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
        
        st.info("Place QR codes on tables, at the entrance, and near the counter for maximum visibility.")

# Analytics Dashboard
def analytics_dashboard():
    st.title("Analytics Dashboard")
    
    # Time period selector
    days = st.sidebar.selectbox("Select Time Period", [7, 30, 90], index=1)
    
    # Get real analytics data
    analytics_data = db.get_real_analytics(days)
    
    if not analytics_data:
        st.warning("No real data available yet. Analytics will show real data as orders are placed.")
        return
    
    totals = analytics_data['totals']
    daily_trend = analytics_data['daily_trend']
    
    # Key Metrics
    st.subheader("Key Performance Indicators")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_orders = totals[0] if totals else 0
        st.metric("Total Orders", total_orders)
    
    with col2:
        total_revenue = totals[1] if totals else 0
        st.metric("Total Revenue", f"R {total_revenue:,.0f}")
    
    with col3:
        avg_order_value = totals[2] if totals else 0
        st.metric("Average Order", f"R {avg_order_value:.0f}")

# Main navigation for staff
def staff_navigation():
    st.sidebar.title("Staff Portal")
    st.sidebar.write(f"Welcome, {st.session_state.user[1]}!")
    
    if st.sidebar.button("Logout", type="primary"):
        logout()
    
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio("Navigation", ["Kitchen Dashboard", "Analytics", "QR Codes"])
    
    if page == "Kitchen Dashboard":
        staff_dashboard()
    elif page == "Analytics":
        analytics_dashboard()
    elif page == "QR Codes":
        qr_management()

# Main app with smart navigation
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
            st.title("Sanele Restaurant")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Home", use_container_width=True, type="primary" if st.session_state.current_page == "home" else "secondary"):
                    st.session_state.current_page = "home"
                    st.rerun()
            with col2:
                if st.button("Order", use_container_width=True, type="primary" if st.session_state.current_page == "order" else "secondary"):
                    st.session_state.current_page = "order"
                    st.session_state.current_step = "order_type"
                    st.rerun()
            with col3:
                if st.button("Track", use_container_width=True, type="primary" if st.session_state.current_page == "track" else "secondary"):
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
            st.sidebar.title("Sanele Restaurant")
            st.sidebar.markdown("---")
            
            # Customer navigation
            st.sidebar.subheader("Customer")
            app_mode = st.sidebar.radio("Choose your action:", 
                                      ["Home", "Place Order", "Track Order"])
            
            # Staff login section
            st.sidebar.markdown("---")
            st.sidebar.subheader("Staff Portal")
            staff_login()
            
            # Main content area
            if app_mode == "Home":
                show_landing_page()
            elif app_mode == "Place Order":
                customer_ordering()
            elif app_mode == "Track Order":
                track_order()

if __name__ == "__main__":
    main()