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

# ULTIMATE RESTAURANT DATABASE
class RestaurantDB:
    def __init__(self, db_name="restaurant_final.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Drop and recreate all tables
        tables = [
            "order_status_history",
            "order_items", 
            "orders", 
            "menu_items", 
            "users",
            "analytics_cache"
        ]
        
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        # Users table
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'staff',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Menu items table
        cursor.execute('''
            CREATE TABLE menu_items (
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
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_number INTEGER,
                customer_name TEXT NOT NULL,
                order_type TEXT DEFAULT 'dine-in',
                status TEXT DEFAULT 'pending',
                total_amount REAL DEFAULT 0,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                order_token TEXT UNIQUE,
                payment_method TEXT DEFAULT 'cash'
            )
        ''')
        
        # Order items table
        cursor.execute('''
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                menu_item_id INTEGER,
                menu_item_name TEXT,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                special_instructions TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
        ''')
        
        # Order status history table
        cursor.execute('''
            CREATE TABLE order_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
        ''')
        
        # Analytics cache table
        cursor.execute('''
            CREATE TABLE analytics_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE,
                cache_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        self.insert_default_data()
    
    def insert_default_data(self):
        cursor = self.conn.cursor()
        
        # Insert default users
        default_users = [
            ('admin', hashlib.sha256('admin123'.encode()).hexdigest(), 'admin'),
            ('chef', hashlib.sha256('chef123'.encode()).hexdigest(), 'chef'),
            ('staff', hashlib.sha256('staff123'.encode()).hexdigest(), 'staff')
        ]
        
        for username, password, role in default_users:
            try:
                cursor.execute('INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)', 
                             (username, password, role))
            except:
                pass
        
        # Insert menu items with LOCAL images
        menu_items = [
            # BEVERAGES
            ('Cappuccino', 'Freshly brewed coffee with steamed milk', 25, 'Beverage', 'https://images.unsplash.com/photo-1561047029-3000c68339ca?w=400'),
            ('Coca-Cola', 'Ice cold Coca-Cola', 18, 'Beverage', 'https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=400'),
            ('Orange Juice', 'Freshly squeezed orange juice', 22, 'Beverage', 'https://images.unsplash.com/photo-1613478223719-2ab802602423?w=400'),
            ('Bottled Water', '500ml still water', 15, 'Beverage', 'bottled_water.jpg'),
            
            # BURGERS
            ('Beef Burger', 'Classic beef burger with cheese and veggies', 65, 'Main Course', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400'),
            ('Chicken Burger', 'Grilled chicken breast with mayo and lettuce', 55, 'Main Course', 'chicken_burger.jpg'),
            ('Cheese Burger', 'Double beef patty with extra cheese', 75, 'Main Course', 'https://images.unsplash.com/photo-1607013251379-e6eecfffe234?w=400'),
            
            # GRILLED ITEMS
            ('Grilled Chicken', 'Tender grilled chicken breast with herbs', 85, 'Main Course', 'https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=400'),
            ('Beef Steak', 'Juicy beef steak with pepper sauce', 120, 'Main Course', 'beef_steak.jpg'),
            ('Grilled Fish', 'Fresh fish with lemon butter sauce', 95, 'Main Course', 'grilled_fish.jpg'),
            
            # DESSERTS
            ('Chocolate Cake', 'Rich chocolate cake with ganache', 35, 'Dessert', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=400'),
            ('Ice Cream', 'Vanilla ice cream with chocolate sauce', 25, 'Dessert', 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=400'),
            ('Apple Pie', 'Warm apple pie with cinnamon', 30, 'Dessert', 'apple_pie.jpg'),
            
            # SIDES
            ('French Fries', 'Crispy golden fries', 25, 'Starter', 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400'),
            ('Onion Rings', 'Beer-battered onion rings', 28, 'Starter', 'onion_rings.jpg'),
            ('Garlic Bread', 'Toasted bread with garlic butter', 20, 'Starter', 'garlic_bread.jpg'),
        ]
        
        for item in menu_items:
            cursor.execute('''
                INSERT INTO menu_items (name, description, price, category, image_url)
                VALUES (?, ?, ?, ?, ?)
            ''', item)
        
        self.conn.commit()

    def add_order(self, customer_name, order_type, items, table_number=None, notes="", payment_method="cash"):
        """BULLETPROOF ORDER CREATION"""
        cursor = self.conn.cursor()
        
        try:
            # Calculate total
            total_amount = sum(item['price'] * item['quantity'] for item in items)
            
            # Generate unique token
            order_token = f"ORD{random.randint(1000, 9999)}{int(time.time())}"
            
            # Insert order
            cursor.execute('''
                INSERT INTO orders (customer_name, order_type, table_number, total_amount, notes, order_token, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (customer_name, order_type, table_number, total_amount, notes, order_token, payment_method))
            
            order_id = cursor.lastrowid
            
            # Insert order items
            for item in items:
                cursor.execute('''
                    INSERT INTO order_items (order_id, menu_item_id, menu_item_name, quantity, price, special_instructions)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (order_id, item['id'], item['name'], item['quantity'], item['price'], item.get('instructions', '')))
            
            # Add to status history
            cursor.execute('''
                INSERT INTO order_status_history (order_id, status, notes)
                VALUES (?, ?, ?)
            ''', (order_id, 'pending', 'Order placed'))
            
            self.conn.commit()
            
            # VERIFY the order was created
            cursor.execute('SELECT id, order_token FROM orders WHERE id = ?', (order_id,))
            result = cursor.fetchone()
            
            if result and result[1] == order_token:
                return order_id, order_token
            else:
                raise Exception("Order verification failed")
                
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Order creation failed: {str(e)}")

    def get_order_by_token(self, order_token):
        """RELIABLE ORDER RETRIEVAL"""
        cursor = self.conn.cursor()
        
        try:
            # Get basic order info
            cursor.execute('SELECT * FROM orders WHERE order_token = ?', (order_token,))
            order = cursor.fetchone()
            
            if not order:
                return None
            
            # Get order items
            cursor.execute('''
                SELECT menu_item_name, quantity, price 
                FROM order_items 
                WHERE order_id = ?
            ''', (order[0],))
            items = cursor.fetchall()
            
            # Format items string
            items_str = ", ".join([f"{item[0]} (x{item[1]})" for item in items])
            item_count = len(items)
            
            # Convert to list and add items info
            order_list = list(order)
            order_list.append(items_str)  # items at index 12
            order_list.append(item_count) # item_count at index 13
            
            return tuple(order_list)
            
        except Exception as e:
            st.error(f"Error retrieving order: {str(e)}")
            return None

    def get_order_status(self, order_token):
        """Quick status check"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT status FROM orders WHERE order_token = ?', (order_token,))
            result = cursor.fetchone()
            return result[0] if result else None
        except:
            return None

    def update_order_status(self, order_id, new_status, notes=""):
        """Update order status"""
        cursor = self.conn.cursor()
        try:
            # Update order
            cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
            # Add to history
            cursor.execute('INSERT INTO order_status_history (order_id, status, notes) VALUES (?, ?, ?)', 
                         (order_id, new_status, notes))
            self.conn.commit()
            return True
        except:
            self.conn.rollback()
            return False

    def get_active_orders(self):
        """Get active orders for kitchen"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT o.*, 
                   GROUP_CONCAT(oi.menu_item_name || ' (x' || oi.quantity || ')', ', ') as items
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.status NOT IN ('completed', 'collected')
            GROUP BY o.id 
            ORDER BY o.order_date DESC
        ''')
        return cursor.fetchall()

    def get_menu_items(self, category=None):
        """Get menu items"""
        cursor = self.conn.cursor()
        if category and category != 'All':
            cursor.execute('SELECT * FROM menu_items WHERE available = 1 AND category = ? ORDER BY name', (category,))
        else:
            cursor.execute('SELECT * FROM menu_items WHERE available = 1 ORDER BY category, name')
        return cursor.fetchall()

    def get_todays_orders_count(self):
        """Get today's orders count"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM orders WHERE date(order_date) = date("now")')
        result = cursor.fetchone()
        return result[0] if result else 0

    def get_real_analytics(self, days=30):
        """REAL ANALYTICS DATA"""
        cursor = self.conn.cursor()
        
        try:
            # Total revenue and orders
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
                ORDER BY total_revenue DESC
            ''', (days,))
            category_distribution = cursor.fetchall()
            
            return {
                'totals': totals or (0, 0, 0),
                'daily_trend': daily_data or [],
                'popular_dishes': popular_dishes or [],
                'category_distribution': category_distribution or []
            }
            
        except Exception as e:
            return {
                'totals': (0, 0, 0),
                'daily_trend': [],
                'popular_dishes': [],
                'category_distribution': []
            }

# Initialize database
try:
    if os.path.exists("restaurant_final.db"):
        os.remove("restaurant_final.db")
    db = RestaurantDB()
except Exception as e:
    st.error(f"Database error: {e}")

# QR CODE GENERATOR
def generate_qr_code(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# AUTHENTICATION
def staff_login():
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔐 Staff Login")
    
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    
    if st.sidebar.button("Login", use_container_width=True):
        if username and password:
            cursor = db.conn.cursor()
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_password))
            user = cursor.fetchone()
            
            if user:
                st.session_state.user = user
                st.session_state.logged_in = True
                st.session_state.role = user[3]
                st.sidebar.success(f"Welcome, {user[1]}!")
                time.sleep(1)
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials")

def logout():
    for key in list(st.session_state.keys()):
        if key not in ['logged_in', 'user', 'role']:
            del st.session_state[key]
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()

# INITIALIZE SESSION STATE
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
if 'last_order_check' not in st.session_state:
    st.session_state.last_order_check = time.time()

# CUSTOMER ORDERING INTERFACE
def customer_ordering():
    st.markdown("""
    <style>
    .header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .menu-image {
        border-radius: 10px;
        width: 100%;
        height: 200px;
        object-fit: cover;
        margin-bottom: 1rem;
    }
    .menu-item-card {
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    .menu-item-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="header"><h1>🍽️ TASTE RESTAURANT</h1><p>Premium Dining Experience</p></div>', unsafe_allow_html=True)
    
    # Step navigation
    if st.session_state.current_step == "order_type":
        show_order_type()
    elif st.session_state.current_step == "customer_info":
        show_customer_info()
    elif st.session_state.current_step == "menu":
        show_menu()
    elif st.session_state.current_step == "confirmation":
        show_confirmation()
    elif st.session_state.current_step == "tracking":
        track_order()

def show_order_type():
    st.subheader("🎯 Choose Your Experience")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; border: 2px solid #e0e0e0; border-radius: 15px;">
            <div style="font-size: 3rem;">🏠</div>
            <h3>Dine In</h3>
            <p>Enjoy our premium atmosphere</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Dine In", key="dine_in", use_container_width=True):
            st.session_state.order_type = "dine-in"
            st.session_state.current_step = "customer_info"
            st.rerun()
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; border: 2px solid #e0e0e0; border-radius: 15px;">
            <div style="font-size: 3rem;">🥡</div>
            <h3>Takeaway</h3>
            <p>Pick up and enjoy elsewhere</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Takeaway", key="takeaway", use_container_width=True):
            st.session_state.order_type = "takeaway"
            st.session_state.current_step = "customer_info"
            st.rerun()
    
    with col3:
        st.markdown("""
        <div style="text-align: center; padding: 2rem; border: 2px solid #e0e0e0; border-radius: 15px;">
            <div style="font-size: 3rem;">🚚</div>
            <h3>Delivery</h3>
            <p>We bring it to your door</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Choose Delivery", key="delivery", use_container_width=True):
            st.session_state.order_type = "delivery"
            st.session_state.current_step = "customer_info"
            st.rerun()

def show_customer_info():
    st.subheader("👤 Your Information")
    
    with st.form("customer_info"):
        customer_name = st.text_input("**Full Name**", value=st.session_state.customer_name, 
                                    placeholder="Enter your name")
        
        if st.session_state.order_type == "dine-in":
            table_number = st.number_input("**Table Number**", min_value=1, max_value=50, 
                                         value=st.session_state.table_number)
        else:
            table_number = None
        
        order_notes = st.text_area("**Special Instructions**", value=st.session_state.order_notes,
                                 placeholder="Any allergies, dietary requirements, or special requests...",
                                 height=100)
        
        payment_method = st.radio("**Payment Method**", ["💵 Cash", "💳 Card"])
        
        if st.form_submit_button("🚀 Continue to Menu", type="primary"):
            if customer_name.strip():
                st.session_state.customer_name = customer_name.strip()
                st.session_state.table_number = table_number
                st.session_state.order_notes = order_notes
                st.session_state.payment_method = "cash" if payment_method == "💵 Cash" else "card"
                st.session_state.current_step = "menu"
                st.rerun()
            else:
                st.error("Please enter your name")

def show_menu():
    st.subheader("📋 Explore Our Menu")
    
    # Category filter
    categories = ['All', 'Beverage', 'Main Course', 'Dessert', 'Starter']
    selected_category = st.selectbox("**Filter by Category**", categories)
    
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
        # Display image - handle both local and URL images
        image_url = item[6]
        try:
            if image_url.endswith('.jpg') or image_url.endswith('.jpeg') or image_url.endswith('.png'):
                # Local image
                st.image(image_url, use_container_width=True, caption=item[1])
            else:
                # URL image
                st.image(image_url, use_container_width=True, caption=item[1])
        except Exception as e:
            # Fallback image
            st.markdown(f"""
            <div style="background: linear-gradient(45deg, #f0f0f0, #e0e0e0); height: 200px; border-radius: 10px; 
                        display: flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
                <div style="text-align: center;">
                    <div style="font-size: 3rem;">🍽️</div>
                    <div style="font-weight: bold;">{item[1]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Menu item details
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

def show_confirmation():
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

def track_order():
    st.subheader("📱 Track Your Order")
    
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
            # Show recent orders for debugging
            try:
                cursor = db.conn.cursor()
                cursor.execute('SELECT order_token, customer_name FROM orders ORDER BY id DESC LIMIT 5')
                recent = cursor.fetchall()
                if recent:
                    st.info("🔍 Recent orders in system:")
                    for token, name in recent:
                        st.write(f"- {name}: `{token}`")
            except:
                pass
            return
        
        # Get full order details
        order = db.get_order_by_token(order_token)
        
        if order:
            display_order_progress(order, current_status)
            
            # AUTO-REFRESH every 3 seconds
            time.sleep(3)
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
        if order[1]:  # table number
            st.write(f"**Table:** {order[1]}")
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
        st.info("🔄 **Live tracking active** - Updates every 3 seconds")
        st.write(f"**Last checked:** {get_sa_time().strftime('%H:%M:%S')} SAST")
    with col2:
        if st.button("🔄 Refresh Now"):
            st.rerun()

# KITCHEN DASHBOARD
def kitchen_dashboard():
    st.title("👨‍🍳 Kitchen Dashboard")
    st.markdown("### Real-Time Order Management")
    
    # Auto-refresh
    if time.time() - st.session_state.last_order_check > 5:
        st.session_state.last_order_check = time.time()
        st.rerun()
    
    # Get active orders
    orders = db.get_active_orders()
    
    if not orders:
        st.success("🎉 All caught up! No active orders.")
        return
    
    # Display orders by status
    for status in ['pending', 'confirmed', 'preparing', 'ready']:
        status_orders = [o for o in orders if o[5] == status]
        
        if status_orders:
            st.subheader(f"{status.title()} Orders ({len(status_orders)})")
            
            for order in status_orders:
                with st.expander(f"Order #{order[0]} - {order[2]}", expanded=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Token:** `{order[9]}`")
                        st.write(f"**Type:** {order[3]}")
                        if order[1]:
                            st.write(f"**Table:** {order[1]}")
                        st.write(f"**Items:** {order[12]}" if len(order) > 12 else "Loading...")
                        st.write(f"**Total:** R {order[6]:.2f}")
                        st.write(f"**Time:** {order[7]}")
                        if order[9]:
                            st.write(f"**Notes:** {order[9]}")
                    
                    with col2:
                        # Status update buttons
                        if status == 'pending':
                            if st.button("✅ Confirm", key=f"confirm_{order[0]}", use_container_width=True):
                                db.update_order_status(order[0], 'confirmed', 'Order confirmed by kitchen')
                                st.rerun()
                        elif status == 'confirmed':
                            if st.button("👨‍🍳 Start Prep", key=f"prep_{order[0]}", use_container_width=True):
                                db.update_order_status(order[0], 'preparing', 'Food preparation started')
                                st.rerun()
                        elif status == 'preparing':
                            if st.button("🎯 Mark Ready", key=f"ready_{order[0]}", use_container_width=True):
                                db.update_order_status(order[0], 'ready', 'Order ready for service')
                                st.rerun()
                        elif status == 'ready':
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Complete", key=f"complete_{order[0]}"):
                                    db.update_order_status(order[0], 'completed', 'Order completed')
                                    st.rerun()
                            with col2:
                                if st.button("📦 Collected", key=f"collected_{order[0]}"):
                                    db.update_order_status(order[0], 'collected', 'Order collected by customer')
                                    st.rerun()

# ANALYTICS DASHBOARD
def analytics_dashboard():
    st.title("📊 Analytics Dashboard")
    
    # Time period selector
    days = st.selectbox("Time Period", [7, 30, 90], index=1)
    
    # Get analytics data
    analytics_data = db.get_real_analytics(days)
    
    # Key Metrics
    st.subheader("🎯 Key Performance Indicators")
    
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.metric("📦 Total Orders", f"{analytics_data['totals'][0]:,}")
    with kpi_cols[1]:
        st.metric("💰 Total Revenue", f"R {analytics_data['totals'][1]:,.0f}")
    with kpi_cols[2]:
        st.metric("📊 Average Order", f"R {analytics_data['totals'][2]:.0f}")
    with kpi_cols[3]:
        today_orders = db.get_todays_orders_count()
        st.metric("📅 Today's Orders", today_orders)
    
    # Revenue Trend Chart
    if analytics_data['daily_trend']:
        st.subheader("📈 Daily Revenue Trend")
        daily_df = pd.DataFrame(analytics_data['daily_trend'], columns=['Date', 'Orders', 'Revenue'])
        daily_df['Date'] = pd.to_datetime(daily_df['Date'])
        
        fig = px.line(daily_df, x='Date', y='Revenue', title='Daily Revenue Trend',
                     labels={'Revenue': 'Revenue (R)', 'Date': 'Date'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Popular Dishes Bar Chart
    if analytics_data['popular_dishes']:
        st.subheader("🍽️ Top Selling Dishes")
        dishes_df = pd.DataFrame(analytics_data['popular_dishes'], columns=['Dish', 'Quantity', 'Revenue', 'Orders'])
        
        fig = px.bar(dishes_df.head(8), x='Dish', y='Quantity', title='Most Popular Items by Quantity',
                    color='Quantity', color_continuous_scale='Viridis')
        st.plotly_chart(fig, use_container_width=True)
    
    # Category Distribution Pie Chart
    if analytics_data['category_distribution']:
        st.subheader("🥧 Revenue by Category")
        category_df = pd.DataFrame(analytics_data['category_distribution'], columns=['Category', 'Quantity', 'Revenue', 'Orders'])
        
        fig = px.pie(category_df, values='Revenue', names='Category', title='Revenue Distribution by Category')
        st.plotly_chart(fig, use_container_width=True)

# MAIN APPLICATION
def main():
    st.set_page_config(
        page_title="Taste Restaurant",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sidebar
    st.sidebar.title("🍽️ Taste Restaurant")
    
    if st.session_state.logged_in:
        # Staff interface
        st.sidebar.success(f"Welcome, {st.session_state.user[1]}!")
        
        # Staff navigation
        pages = ["👨‍🍳 Kitchen Dashboard", "📊 Analytics"]
        selected_page = st.sidebar.radio("Navigation", pages)
        
        if st.sidebar.button("Logout"):
            logout()
        
        # Page routing
        if selected_page == "👨‍🍳 Kitchen Dashboard":
            kitchen_dashboard()
        else:
            analytics_dashboard()
            
    else:
        # Customer interface
        st.sidebar.markdown("---")
        nav = st.sidebar.radio("Customer", ["🏠 Home", "🍕 Place Order", "📱 Track Order"])
        
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
        if nav == "🏠 Home":
            show_landing_page()
        elif nav == "🍕 Place Order":
            customer_ordering()
        else:
            track_order()

def show_landing_page():
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
        st.session_state.current_step = "order_type"
        st.rerun()

if __name__ == "__main__":
    main()