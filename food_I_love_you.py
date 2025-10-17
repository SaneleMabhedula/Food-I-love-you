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
        
        # Insert default admin user with new credentials
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
            ('Bottled Water', '500ml still water', 15, 'Beverage', 'bottled_water.jpg'),
            
            # BURGERS
            ('Beef Burger', 'Classic beef burger with cheese and veggies', 65, 'Main Course', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?ixlib=rb-4.0.3'),
            ('Chicken Burger', 'Grilled chicken breast with mayo and lettuce', 55, 'Main Course', 'chicken_burger.jpg'),
            ('Cheese Burger', 'Double beef patty with extra cheese', 75, 'Main Course', 'https://images.unsplash.com/photo-1607013251379-e6eecfffe234?ixlib=rb-4.0.3'),
            
            # GRILLED ITEMS
            ('Grilled Chicken', 'Tender grilled chicken breast with herbs', 85, 'Main Course', 'https://images.unsplash.com/photo-1532550907401-a500c9a57435?ixlib=rb-4.0.3'),
            ('Beef Steak', 'Juicy beef steak with pepper sauce', 120, 'Main Course', 'beef_steak.jpg'),
            ('Grilled Fish', 'Fresh fish with lemon butter sauce', 95, 'Main Course', 'grilled_fish.jpg'),
            
            # DESSERTS
            ('Chocolate Cake', 'Rich chocolate cake with ganache', 35, 'Dessert', 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?ixlib=rb-4.0.3'),
            ('Ice Cream', 'Vanilla ice cream with chocolate sauce', 25, 'Dessert', 'https://images.unsplash.com/photo-1563805042-7684c019e1cb?ixlib=rb-4.0.3'),
            ('Apple Pie', 'Warm apple pie with cinnamon', 30, 'Dessert', 'apple_pie.jpg'),
            
            # SIDES
            ('French Fries', 'Crispy golden fries', 25, 'Starter', 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?ixlib=rb-4.0.3'),
            ('Onion Rings', 'Beer-battered onion rings', 28, 'Starter', 'onion_rings.jpg'),
            ('Garlic Bread', 'Toasted bread with garlic butter', 20, 'Starter', 'garlic_bread.jpg')
        ]
        
        for item in menu_items:
            cursor.execute('''
                INSERT INTO menu_items (name, description, price, category, image_url)
                VALUES (?, ?, ?, ?, ?)
            ''', item)
        
        self.conn.commit()

    def add_order(self, customer_name, order_type, items, table_number=None, notes="", payment_method="cash"):
        cursor = self.conn.cursor()
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        # Generate unique order token
        order_token = f"ORD{random.randint(1000, 9999)}{int(time.time()) % 10000}"
        
        # Use current South African timestamp for order date
        current_time = get_sa_time().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            # Insert order
            cursor.execute('''
                INSERT INTO orders (customer_name, order_type, table_number, total_amount, notes, order_token, order_date, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (customer_name, order_type, table_number, total_amount, notes, order_token, current_time, payment_method))
            
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
            
            # Verify the order was created
            cursor.execute('SELECT id FROM orders WHERE order_token = ?', (order_token,))
            result = cursor.fetchone()
            if not result:
                raise Exception("Order was not created successfully")
                
            return order_id, order_token
            
        except Exception as e:
            self.conn.rollback()
            st.error(f"Error adding order: {e}")
            raise e

    def get_order_by_token(self, order_token):
        """COMPLETELY REWRITTEN: Simple and reliable order retrieval"""
        cursor = self.conn.cursor()
        try:
            # Get the order
            cursor.execute('SELECT * FROM orders WHERE order_token = ?', (order_token,))
            order = cursor.fetchone()
            
            if not order:
                st.warning(f"No order found with token: {order_token}")
                return None
            
            # Get order items
            cursor.execute('''
                SELECT menu_item_name, quantity, special_instructions 
                FROM order_items 
                WHERE order_id = ?
            ''', (order[0],))
            items = cursor.fetchall()
            
            # Format items string
            items_list = []
            for item in items:
                item_str = f"{item[0]} (x{item[1]})"
                if item[2]:  # special instructions
                    item_str += f" - {item[2]}"
                items_list.append(item_str)
            
            items_str = ", ".join(items_list)
            item_count = len(items)
            
            # Return complete order info
            return {
                'id': order[0],
                'table_number': order[1],
                'customer_name': order[2],
                'order_type': order[3],
                'status': order[4],
                'total_amount': order[5],
                'order_date': order[6],
                'notes': order[7],
                'estimated_wait_time': order[8],
                'order_token': order[9],
                'payment_method': order[10],
                'items': items_str,
                'item_count': item_count
            }
            
        except Exception as e:
            st.error(f"Database error in get_order_by_token: {e}")
            return None

    def get_order_status(self, order_token):
        """Get just the current status of an order"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT status FROM orders WHERE order_token = ?', (order_token,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            st.error(f"Error getting order status: {e}")
            return None

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

    def get_recent_orders(self, limit=25):
        """Get recent orders"""
        cursor = self.conn.cursor()
        try:
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
        except Exception as e:
            st.error(f"Error getting recent orders: {e}")
            return []

    def get_menu_items(self, category=None):
        cursor = self.conn.cursor()
        query = 'SELECT * FROM menu_items WHERE available = 1'
        if category:
            query += f" AND category = '{category}'"
        query += " ORDER BY category, name"
        
        cursor.execute(query)
        return cursor.fetchall()

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

    # ... (other methods remain the same)

# Initialize database
try:
    if os.path.exists("restaurant.db"):
        os.remove("restaurant.db")
    db = RestaurantDB()
    st.success("✅ Database initialized successfully!")
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
        if st.button("🏠 **Dine In**", use_container_width=True, key="dine_in_btn"):
            st.session_state.order_type = "dine-in"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("Enjoy our cozy atmosphere")
    
    with col2:
        if st.button("🥡 **Takeaway**", use_container_width=True, key="takeaway_btn"):
            st.session_state.order_type = "takeaway"
            st.session_state.current_step = "customer_info"
            st.rerun()
        st.caption("Pick up and enjoy elsewhere")
    
    with col3:
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
    st.subheader("📋 Explore Our Menu")
    
    # Menu categories
    categories = ['All', 'Beverage', 'Main Course', 'Dessert', 'Starter']
    selected_category = st.selectbox("**Filter by Category**", categories, key="category_filter")
    
    # Get menu items
    try:
        menu_items = db.get_menu_items(None if selected_category == 'All' else selected_category)
    except:
        # Fallback if database error
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
                # Simple image placeholder
                st.markdown(f'''
                <div style="background: linear-gradient(45deg, #f0f0f0, #e0e0e0); border-radius: 10px; 
                            height: 150px; display: flex; align-items: center; justify-content: center;">
                    <div style="text-align: center;">
                        <div style="font-size: 2rem;">🍽️</div>
                        <div style="font-weight: bold;">{item[1]}</div>
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
                    instructions = st.text_input("Special requests", key=f"inst_{item[0]}", placeholder="e.g., no onions")
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
                st.success(f"🎉 Order placed successfully! Your Order Token is: **{order_token}**")
                st.info("📱 Save this token to track your order status")
                st.balloons()
                time.sleep(2)
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
    
    # Check if we have an active order from the ordering flow
    if st.session_state.get('order_placed') and st.session_state.get('order_token'):
        order_token = st.session_state.order_token
        display_order_tracking(order_token)
    else:
        # Allow manual order token entry
        st.info("🔍 **Enter your Order Token to track your order status**")
        order_token = st.text_input("Order Token", placeholder="ORD123456789", key="track_order_input")
        
        if st.button("🔍 Track Order", type="primary", key="track_order_btn"):
            if order_token:
                if order_token.startswith("ORD") and len(order_token) > 3:
                    display_order_tracking(order_token)
                else:
                    st.error("❌ Invalid Order Token format. It should start with 'ORD' followed by numbers.")
            else:
                st.error("❌ Please enter your order token")

def display_order_tracking(order_token):
    try:
        # First check if order exists
        current_status = db.get_order_status(order_token)
        
        if current_status is None:
            st.error("❌ Order not found. Please check your Order Token.")
            
            # Show recent orders for debugging
            try:
                recent_orders = db.get_recent_orders(5)
                if recent_orders:
                    st.info("🔍 Recent orders in system:")
                    for order in recent_orders:
                        st.write(f"- Order #{order[0]}: {order[2]} (Token: {order[9]})")
                else:
                    st.write("No orders found in system.")
            except Exception as e:
                st.write(f"Error checking recent orders: {e}")
                
            return
        
        # If order is collected/completed, show completion message
        if current_status in ['completed', 'collected']:
            st.success("🎉 **Your order has been completed! Thank you for dining with us!**")
            st.balloons()
            st.info("💫 We hope you enjoyed your meal!")
            return
        
        # Get full order details
        order = db.get_order_by_token(order_token)
        
        if not order:
            st.error("❌ Could not load order details. Please try again.")
            return
        
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
            st.write(f"**📄 Order ID:** {order['id']}")
            st.write(f"**👤 Customer:** {order['customer_name']}")
            st.write(f"**🎯 Order Type:** {order['order_type'].title()}")
            st.write(f"**💳 Payment:** {order['payment_method'].title()}")
        with col2:
            st.write(f"**💰 Total:** R {order['total_amount']}")
            st.write(f"**📅 Order Date:** {order['order_date']}")
            st.write(f"**📦 Items Ordered:** {order['item_count']}")
            if order['notes']:
                st.write(f"**📝 Notes:** {order['notes']}")
        
        # Enhanced Real-time Progress Tracker
        st.subheader("🔄 Order Progress")
        
        # Define status flow based on order type
        if order['order_type'] == 'takeaway':
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
        if order['items']:
            items = order['items'].split(',')
            for item in items:
                st.write(f"• {item.strip()}")
        else:
            st.write("No items found in this order")
        
        # Special collection button for takeaway
        if order['order_type'] == 'takeaway' and current_status == 'ready':
            st.success("🎯 **Your order is ready for collection!**")
            st.info("📍 Please come to the counter to collect your order")
            
            if st.button("📦 **I've Collected My Order**", type="primary", key="collect_btn"):
                try:
                    db.update_order_status(order['id'], 'collected', 'Customer collected order')
                    st.success("🎉 Thank you! Order marked as collected. Enjoy your meal! 🍽️")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error updating order: {e}")
        
        # Auto-refresh for live updates
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("🔄 **Live Tracking Active** - Status updates automatically")
            st.write(f"**Last checked:** {get_sa_time().strftime('%H:%M:%S')} SAST")
        with col2:
            if st.button("🔄 Refresh Now", key="refresh_btn"):
                st.rerun()
        
        # Auto-refresh every 5 seconds for real-time updates
        time.sleep(5)
        st.rerun()
            
    except Exception as e:
        st.error(f"❌ Error tracking order: {e}")
        st.info("🤝 If this problem persists, please contact our staff for assistance.")

# Main app
def main():
    st.set_page_config(
        page_title="Taste Restaurant",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Main navigation - Customer vs Staff
    if st.session_state.logged_in:
        # Staff interface
        st.sidebar.title("👨‍💼 Staff Portal")
        st.sidebar.markdown(f"Welcome, {st.session_state.user[1]}!")
        
        page = st.sidebar.radio("Navigation", ["👨‍🍳 Kitchen", "📊 Analytics"])
        
        if page == "👨‍🍳 Kitchen":
            st.title("👨‍🍳 Kitchen Dashboard")
            # Simple kitchen view
            orders = db.get_active_orders()
            if orders:
                for order in orders:
                    with st.expander(f"Order #{order[0]} - {order[2]} ({order[4]})"):
                        st.write(f"Items: {order[8]}")
                        st.write(f"Table: {order[1]}")
                        if st.button(f"Mark as Preparing", key=f"prep_{order[0]}"):
                            db.update_order_status(order[0], 'preparing')
                            st.rerun()
                        if st.button(f"Mark as Ready", key=f"ready_{order[0]}"):
                            db.update_order_status(order[0], 'ready')
                            st.rerun()
            else:
                st.info("No active orders")
                
        elif page == "📊 Analytics":
            st.title("📊 Analytics")
            st.info("Analytics dashboard would go here")
            
        if st.sidebar.button("Logout"):
            logout()
            
    else:
        # Customer interface
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
            st.title("🍽️ Welcome to Taste Restaurant")
            st.write("Delicious food and great service!")
            if st.button("Start Your Order"):
                st.session_state.current_step = "order_type"
                st.rerun()
                
        elif app_mode == "🍕 Place Order":
            customer_ordering()
        elif app_mode == "📱 Track Order":
            track_order()

if __name__ == "__main__":
    main()