import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import qrcode
from PIL import Image
import io
import base64
import sqlite3
import json
import uuid
import os

# Database Class with proper table creation
class RestaurantDB:
    def __init__(self):
        self.db_path = 'restaurant_orders.db'
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Check if orders table exists and has the correct schema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            # Check if order_type column exists
            cursor.execute("PRAGMA table_info(orders)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'order_type' not in columns:
                # Add the missing column
                cursor.execute('ALTER TABLE orders ADD COLUMN order_type TEXT DEFAULT "dine_in"')
        else:
            # Create orders table if it doesn't exist
            cursor.execute('''
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE,
                    table_number INTEGER,
                    customer_name TEXT,
                    order_type TEXT DEFAULT 'dine_in',
                    items TEXT,
                    total_amount REAL,
                    status TEXT DEFAULT 'received',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        # Check if analytics table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analytics'")
        analytics_exists = cursor.fetchone()
        
        if not analytics_exists:
            # Create analytics table if it doesn't exist
            cursor.execute('''
                CREATE TABLE analytics (
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
        order_id = str(uuid.uuid4())[:8].upper()
        
        # Add individual item status
        enhanced_items = []
        for item in items:
            enhanced_items.append({
                **item,
                'item_status': 'pending',
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
            try:
                order_data = {
                    'id': row[0],
                    'order_id': row[1],
                    'table_number': row[2],
                    'customer_name': row[3],
                    'order_type': row[4] if len(row) > 4 else 'dine_in',
                    'items': json.loads(row[5]),
                    'total_amount': row[6],
                    'status': row[7],
                    'created_at': row[8],
                    'status_updated_at': row[9] if len(row) > 9 else row[8]
                }
                orders.append(order_data)
            except Exception as e:
                continue
        
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
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT items FROM orders WHERE order_id = ?', (order_id,))
        result = cursor.fetchone()
        
        if result:
            items = json.loads(result[0])
            
            for item in items:
                if item.get('item_id') == item_id:
                    item['item_status'] = new_status
                    break
            
            all_items_status = [item['item_status'] for item in items]
            if all(status == 'ready' for status in all_items_status):
                new_order_status = 'ready'
            elif any(status == 'ready' for status in all_items_status):
                new_order_status = 'partially_ready'
            else:
                new_order_status = 'preparing'
            
            cursor.execute('''
                UPDATE orders 
                SET items = ?, status = ?, status_updated_at = CURRENT_TIMESTAMP 
                WHERE order_id = ?
            ''', (json.dumps(items), new_order_status, order_id))
            
            self.conn.commit()
            return True
        return False
    
    def get_customer_order(self, order_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                'id': result[0],
                'order_id': result[1],
                'table_number': result[2],
                'customer_name': result[3],
                'order_type': result[4] if len(result) > 4 else 'dine_in',
                'items': json.loads(result[5]),
                'total_amount': result[6],
                'status': result[7],
                'created_at': result[8],
                'status_updated_at': result[9] if len(result) > 9 else result[8]
            }
        return None
    
    def get_analytics(self, days=7):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT item_name, category, SUM(quantity) as total_quantity, SUM(revenue) as total_revenue
            FROM analytics 
            WHERE date >= date('now', ?) 
            GROUP BY item_name, category
            ORDER BY total_quantity DESC
        ''', (f'-{days} days',))
        
        popular_items = []
        for row in cursor.fetchall():
            popular_items.append({
                'item_name': row[0],
                'category': row[1],
                'total_quantity': row[2],
                'total_revenue': row[3]
            })
        
        cursor.execute('''
            SELECT hour, COUNT(*) as order_count, SUM(revenue) as total_revenue
            FROM analytics 
            WHERE date >= date('now', ?)
            GROUP BY hour
            ORDER BY hour
        ''', (f'-{days} days',))
        
        busy_hours = []
        for row in cursor.fetchall():
            busy_hours.append({
                'hour': row[0],
                'order_count': row[1],
                'total_revenue': row[2]
            })
        
        return {
            'popular_items': popular_items,
            'busy_hours': busy_hours
        }

# Configuration
MENU_CATEGORIES = {
    "burgers": {
        "name": "🍔 Burgers",
        "icon": "🍔",
        "color": "#FF6B35",
        "items": {
            "classic_burger": {"name": "Classic Beef Burger", "price": 89.99, "prep_time": 12},
            "cheese_burger": {"name": "Cheese Burger", "price": 99.99, "prep_time": 15},
            "chicken_burger": {"name": "Grilled Chicken Burger", "price": 94.99, "prep_time": 10},
            "veg_burger": {"name": "Vegetarian Burger", "price": 79.99, "prep_time": 8}
        }
    },
    "meals": {
        "name": "🍛 Full Meals", 
        "icon": "🍛",
        "color": "#28A745",
        "items": {
            "steak_meal": {"name": "Steak & Chips", "price": 149.99, "prep_time": 20},
            "chicken_meal": {"name": "Grilled Chicken Meal", "price": 119.99, "prep_time": 18},
            "fish_meal": {"name": "Fish & Chips", "price": 109.99, "prep_time": 15},
            "veg_meal": {"name": "Vegetarian Platter", "price": 89.99, "prep_time": 12}
        }
    },
    "beverages": {
        "name": "🥤 Beverages",
        "icon": "🥤",
        "color": "#17A2B8", 
        "items": {
            "coke": {"name": "Coca-Cola", "price": 19.99, "prep_time": 2},
            "sprite": {"name": "Sprite", "price": 19.99, "prep_time": 2},
            "juice": {"name": "Fresh Orange Juice", "price": 29.99, "prep_time": 3},
            "water": {"name": "Bottled Water", "price": 15.99, "prep_time": 1},
            "coffee": {"name": "Coffee", "price": 24.99, "prep_time": 5}
        }
    },
    "veggies": {
        "name": "🥗 Sides & Salads",
        "icon": "🥗",
        "color": "#20C997",
        "items": {
            "fries": {"name": "French Fries", "price": 29.99, "prep_time": 8},
            "salad": {"name": "Garden Salad", "price": 39.99, "prep_time": 5},
            "coleslaw": {"name": "Coleslaw", "price": 24.99, "prep_time": 3}
        }
    }
}

ITEM_STATUS = {
    "pending": {"text": "⏳ Pending", "color": "#6C757D"},
    "preparing": {"text": "👨‍🍳 Preparing", "color": "#FFC107"}, 
    "ready": {"text": "✅ Ready", "color": "#28A745"},
    "served": {"text": "🎉 Served", "color": "#17A2B8"}
}

ORDER_TYPES = {
    "dine_in": {"name": "🪑 Dine In", "icon": "🪑"},
    "takeaway": {"name": "🥡 Takeaway", "icon": "🥡"}
}

# Authentication
def check_staff_login():
    if 'staff_logged_in' not in st.session_state:
        st.session_state.staff_logged_in = False
    return st.session_state.staff_logged_in

def staff_login():
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔐 Staff Login")
    
    password = st.sidebar.text_input("Staff Password", type="password")
    if st.sidebar.button("Login", key="staff_login"):
        if password == "staff123":
            st.session_state.staff_logged_in = True
            st.rerun()
        else:
            st.sidebar.error("Incorrect password")
    
    return st.session_state.staff_logged_in

# Initialize database
db = RestaurantDB()

# Page configuration
st.set_page_config(
    page_title="Restaurant QR Ordering",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(135deg, #FF6B35, #F7931E);
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .order-card {
        padding: 1.5rem;
        border-radius: 15px;
        background-color: white;
        color: black;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 5px solid;
        transition: transform 0.2s ease;
        border: 1px solid #E0E0E0;
    }
    .order-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    .status-pending { border-left-color: #6C757D; }
    .status-preparing { border-left-color: #FFC107; }
    .status-partially_ready { border-left-color: #17A2B8; }
    .status-ready { border-left-color: #28A745; }
    .status-completed { border-left-color: #20C997; }
    .menu-category {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .menu-item-card {
        background-color: #FFFFFF;
        color: #000000;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border: 1px solid #E0E0E0;
    }
    .item-status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.25rem;
    }
    .customer-view {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
        padding: 2rem;
    }
    .staff-view {
        background: #f8f9fa;
        min-height: 100vh;
    }
    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .progress-container {
        background: #e9ecef;
        border-radius: 10px;
        height: 10px;
        margin: 1rem 0;
    }
    .progress-bar {
        height: 100%;
        border-radius: 10px;
        background: linear-gradient(135deg, #FF6B35, #F7931E);
        transition: width 0.5s ease;
    }
    .menu-item-card h4, .menu-item-card p {
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

load_css()

def main():
    query_params = st.query_params
    order_id = query_params.get('order_id', [None])[0]
    table_number = query_params.get('table', [None])[0]
    
    if order_id:
        customer_order_tracking(order_id)
    elif table_number:
        customer_ordering(table_number)
    else:
        show_main_navigation()

def show_main_navigation():
    is_staff = check_staff_login()
    
    if not is_staff:
        if staff_login():
            st.rerun()
    
    st.sidebar.title("🍔 Restaurant Dashboard")
    
    if is_staff:
        orders = db.get_orders()
        st.sidebar.info(f"Total orders in system: {len(orders)}")
    
    if is_staff:
        app_mode = st.sidebar.selectbox(
            "Staff Menu",
            ["👨‍🍳 Kitchen Display", "📊 Analytics", "🎯 QR Manager", "🚪 Logout"]
        )
        
        if app_mode == "🚪 Logout":
            st.session_state.staff_logged_in = False
            st.rerun()
        elif app_mode == "👨‍🍳 Kitchen Display":
            kitchen_display()
        elif app_mode == "📊 Analytics":
            analytics_dashboard()
        elif app_mode == "🎯 QR Manager":
            qr_generator()
    else:
        st.markdown('<div class="customer-view">', unsafe_allow_html=True)
        customer_ordering()
        st.markdown('</div>', unsafe_allow_html=True)

def customer_ordering(prefilled_table=None):
    st.markdown('<div class="main-header">🍔 Welcome to Our Restaurant!</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        order_type = st.radio(
            "Order Type",
            options=list(ORDER_TYPES.keys()),
            format_func=lambda x: ORDER_TYPES[x]['name'],
            horizontal=True
        )
    
    with col2:
        if order_type == 'dine_in':
            table_number = st.number_input(
                "Table Number", 
                min_value=1, 
                max_value=50, 
                value=int(prefilled_table) if prefilled_table else 1
            )
        else:
            table_number = None
            st.info("🥡 Takeaway order - no table needed")
    
    customer_name = st.text_input("Your Name (Optional)", placeholder="Enter your name for the order")
    
    st.markdown("---")
    
    order_items = []
    total_amount = 0
    
    for category_id, category_data in MENU_CATEGORIES.items():
        st.markdown(f'''
            <div class="menu-category">
                <h3>{category_data['icon']} {category_data['name']}</h3>
            </div>
        ''', unsafe_allow_html=True)
        
        cols = st.columns(3)
        col_idx = 0
        
        for item_id, item_data in category_data['items'].items():
            with cols[col_idx]:
                with st.container():
                    st.markdown(f'''
                        <div class="menu-item-card">
                            <h4 style="color: #000000 !important;">{item_data['name']}</h4>
                            <p style="color: #000000 !important;">💰 R{item_data['price']:.2f}</p>
                            <p style="color: #000000 !important;">⏱️ ~{item_data['prep_time']}min</p>
                        </div>
                    ''', unsafe_allow_html=True)
                    
                    quantity = st.number_input(
                        f"Quantity of {item_data['name']}",
                        min_value=0,
                        max_value=10,
                        value=0,
                        key=f"{category_id}_{item_id}",
                        label_visibility="collapsed"
                    )
                    
                    if quantity > 0:
                        order_items.append({
                            'id': item_id,
                            'name': item_data['name'],
                            'price': item_data['price'],
                            'quantity': quantity,
                            'category': category_data['name'],
                            'prep_time': item_data['prep_time']
                        })
                        total_amount += item_data['price'] * quantity
            
            col_idx = (col_idx + 1) % 3
        st.markdown("---")
    
    if order_items:
        st.subheader("📋 Order Summary")
        
        summary_df = pd.DataFrame(order_items)
        st.dataframe(summary_df[['name', 'quantity', 'price']], hide_index=True)
        
        st.markdown(f"### 💰 Total Amount: R{total_amount:.2f}")
        
        if st.button("🚀 Place Order", type="primary", use_container_width=True):
            if total_amount > 0:
                try:
                    order_id = db.create_order(
                        table_number, 
                        customer_name, 
                        order_items, 
                        total_amount, 
                        order_type
                    )
                    
                    show_order_confirmation(order_id, table_number, customer_name, order_type, order_items)
                except Exception as e:
                    st.error(f"Error creating order: {e}")
            else:
                st.error("Please add items to your order before submitting.")

def show_order_confirmation(order_id, table_number, customer_name, order_type, order_items):
    st.success("🎉 Order placed successfully!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Order ID:** `{order_id}`")
        if order_type == 'dine_in':
            st.info(f"**Table:** {table_number}")
        st.info(f"**Customer:** {customer_name if customer_name else 'Not provided'}")
        st.info(f"**Order Type:** {ORDER_TYPES[order_type]['name']}")
        
        max_prep_time = max(item['prep_time'] for item in order_items)
        st.info(f"**Estimated wait time:** ~{max_prep_time} minutes")
    
    with col2:
        tracking_url = f"http://localhost:8501/?order_id={order_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(tracking_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        st.image(buffered, width=200)
        st.caption("Scan to track your order")
    
    st.markdown("---")
    st.subheader("📱 Live Order Tracking")
    st.write("**Your order status will update here in real-time:**")
    
    status_placeholder = st.empty()
    items_placeholder = st.empty()
    
    for i in range(120):
        order = db.get_customer_order(order_id)
        
        if order:
            display_order_status(order, status_placeholder, items_placeholder)
        
        time.sleep(2)

def display_order_status(order, status_placeholder, items_placeholder):
    with status_placeholder.container():
        status_display = "⏳ Order Received"
        if order['status'] == 'preparing':
            status_display = "👨‍🍳 Preparing Your Order"
        elif order['status'] == 'partially_ready':
            status_display = "🎉 Some Items Ready!"
        elif order['status'] == 'ready':
            status_display = "✅ Order Ready for Pickup!"
        
        st.markdown(f"### {status_display}")
        
        progress = 0.25
        if order['status'] == 'preparing':
            progress = 0.5
        elif order['status'] == 'partially_ready':
            progress = 0.75
        elif order['status'] == 'ready':
            progress = 1.0
            
        st.markdown(f'''
            <div class="progress-container">
                <div class="progress-bar" style="width: {progress * 100}%"></div>
            </div>
        ''', unsafe_allow_html=True)
    
    with items_placeholder.container():
        st.write("**Item Status:**")
        for item in order['items']:
            status_info = ITEM_STATUS.get(item['item_status'], ITEM_STATUS['pending'])
            st.markdown(f'''
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.5rem 0; padding: 0.5rem; background-color: white; border-radius: 8px; border: 1px solid #E0E0E0;">
                    <span style="color: black;">{item['name']} (x{item['quantity']})</span>
                    <span class="item-status-badge" style="background-color: {status_info['color']}20; color: {status_info['color']}; border: 1px solid {status_info['color']};">
                        {status_info['text']}
                    </span>
                </div>
            ''', unsafe_allow_html=True)

def customer_order_tracking(order_id):
    st.markdown('<div class="customer-view">', unsafe_allow_html=True)
    
    order = db.get_customer_order(order_id)
    
    if not order:
        st.error("Order not found. Please check your Order ID.")
        return
    
    st.markdown(f'<div class="main-header">📱 Order Tracking</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Order ID:** `{order_id}`")
        if order['order_type'] == 'dine_in':
            st.info(f"**Table:** {order['table_number']}")
        st.info(f"**Customer:** {order['customer_name'] or 'Not provided'}")
    
    with col2:
        st.info(f"**Order Type:** {ORDER_TYPES[order['order_type']]['name']}")
        st.info(f"**Total:** R{order['total_amount']:.2f}")
        st.info(f"**Order Time:** {order['created_at']}")
    
    status_placeholder = st.empty()
    items_placeholder = st.empty()
    
    while True:
        order = db.get_customer_order(order_id)
        if order:
            display_order_status(order, status_placeholder, items_placeholder)
        time.sleep(3)

def kitchen_display():
    st.markdown('<div class="staff-view">', unsafe_allow_html=True)
    st.markdown('<div class="main-header">👨‍🍳 Kitchen Command Center</div>', unsafe_allow_html=True)
    
    orders = db.get_orders()
    st.info(f"📊 Total orders in system: {len(orders)}")
    st.info(f"👨‍🍳 Active orders: {len([o for o in orders if o['status'] != 'completed'])}")
    
    auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)
    
    if auto_refresh:
        time.sleep(3)
        st.rerun()
    
    active_orders = [order for order in orders if order['status'] != 'completed']
    
    if not active_orders:
        st.info("No active orders. Time for a break! ☕")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📥 New Orders")
        display_orders_by_status(active_orders, 'received', col1)
    
    with col2:
        st.subheader("👨‍🍳 In Progress")
        display_orders_by_status(active_orders, 'preparing', col2)
        display_orders_by_status(active_orders, 'partially_ready', col2)
    
    with col3:
        st.subheader("✅ Ready")
        display_orders_by_status(active_orders, 'ready', col3)

def display_orders_by_status(orders, status, column):
    filtered_orders = [order for order in orders if order['status'] == status]
    
    if not filtered_orders:
        column.info(f"No {status} orders")
        return
    
    for order in filtered_orders:
        with column:
            status_class = f"status-{status}"
            with st.container():
                st.markdown(f'<div class="order-card {status_class}">', unsafe_allow_html=True)
                
                st.write(f"**Order:** `{order['order_id']}`")
                st.write(f"**Type:** {ORDER_TYPES[order['order_type']]['name']}")
                if order['order_type'] == 'dine_in':
                    st.write(f"**Table:** {order['table_number']}")
                if order['customer_name']:
                    st.write(f"**Customer:** {order['customer_name']}")
                
                st.write("---")
                
                st.write("**Items:**")
                for item in order['items']:
                    col_item1, col_item2 = st.columns([3, 2])
                    
                    with col_item1:
                        st.write(f"- {item['name']} (x{item['quantity']})")
                    
                    with col_item2:
                        current_status = item.get('item_status', 'pending')
                        status_info = ITEM_STATUS.get(current_status, ITEM_STATUS['pending'])
                        
                        if current_status == 'pending':
                            if st.button("Start", key=f"start_{item['item_id']}", use_container_width=True):
                                db.update_item_status(order['order_id'], item['item_id'], 'preparing')
                                st.rerun()
                        elif current_status == 'preparing':
                            if st.button("Ready", key=f"ready_{item['item_id']}", use_container_width=True):
                                db.update_item_status(order['order_id'], item['item_id'], 'ready')
                                st.rerun()
                        elif current_status == 'ready':
                            st.success("✅ Ready")
                
                st.markdown('</div>', unsafe_allow_html=True)

def analytics_dashboard():
    st.markdown('<div class="staff-view">', unsafe_allow_html=True)
    st.markdown('<div class="main-header">📊 Restaurant Analytics</div>', unsafe_allow_html=True)
    
    days = st.slider("Analysis Period (days)", min_value=1, max_value=30, value=7)
    
    analytics_data = db.get_analytics(days)
    
    if not analytics_data['popular_items']:
        st.info("No data available for the selected period.")
        return
    
    tab1, tab2, tab3 = st.tabs(["📈 Sales Performance", "🕒 Busy Hours", "📋 Detailed Reports"])
    
    with tab1:
        popular_df = pd.DataFrame(analytics_data['popular_items'])
        
        if not popular_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_items = px.bar(
                    popular_df.head(10),
                    x='total_quantity',
                    y='item_name',
                    orientation='h',
                    title="Top 10 Most Ordered Items",
                    labels={'total_quantity': 'Quantity Sold', 'item_name': 'Item'}
                )
                st.plotly_chart(fig_items, use_container_width=True)
            
            with col2:
                fig_revenue = px.pie(
                    popular_df,
                    values='total_revenue',
                    names='category',
                    title="Revenue by Category"
                )
                st.plotly_chart(fig_revenue, use_container_width=True)
    
    with tab2:
        busy_df = pd.DataFrame(analytics_data['busy_hours'])
        
        if not busy_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig_hours = px.line(
                    busy_df,
                    x='hour',
                    y='order_count',
                    title="Order Volume by Hour",
                    labels={'hour': 'Hour of Day', 'order_count': 'Number of Orders'}
                )
                st.plotly_chart(fig_hours, use_container_width=True)
            
            with col2:
                fig_revenue_hours = px.bar(
                    busy_df,
                    x='hour',
                    y='total_revenue',
                    title="Revenue by Hour",
                    labels={'hour': 'Hour of Day', 'total_revenue': 'Revenue (R)'}
                )
                st.plotly_chart(fig_revenue_hours, use_container_width=True)
    
    with tab3:
        st.subheader("Detailed Sales Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Top Selling Items**")
            popular_df = pd.DataFrame(analytics_data['popular_items'])
            st.dataframe(
                popular_df[['item_name', 'category', 'total_quantity', 'total_revenue']],
                use_container_width=True
            )
        
        with col2:
            st.write("**Hourly Performance**")
            busy_df = pd.DataFrame(analytics_data['busy_hours'])
            st.dataframe(
                busy_df[['hour', 'order_count', 'total_revenue']],
                use_container_width=True
            )

def qr_generator():
    st.markdown('<div class="staff-view">', unsafe_allow_html=True)
    st.markdown('<div class="main-header">🎯 QR Code Generator</div>', unsafe_allow_html=True)
    
    st.info("Generate QR codes for tables that customers can scan to start ordering")
    
    col1, col2 = st.columns(2)
    
    with col1:
        base_url = st.text_input(
            "Ordering Page URL",
            value="http://localhost:8501",
            help="The URL where your Streamlit app is hosted"
        )
        
        table_numbers = st.text_area(
            "Table Numbers (one per line)",
            value="1\n2\n3\n4\n5",
            help="Enter table numbers, one per line"
        )
    
    with col2:
        qr_size = st.slider("QR Code Size", min_value=100, max_value=300, value=150)
        
    st.subheader("Generated QR Codes")
    
    table_list = [table.strip() for table in table_numbers.split('\n') if table.strip()]
    
    cols = st.columns(4)
    for idx, table_num in enumerate(table_list):
        with cols[idx % 4]:
            qr_img = generate_table_qr(base_url, table_num, qr_size)
            if qr_img:
                # FIXED: use_container_width instead of use_column_width
                st.image(qr_img, caption=f"Table {table_num}", use_container_width=True)

def generate_table_qr(base_url, table_number, size=150):
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr_data = f"{base_url}?table={table_number}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((size, size))
        
        return qr_img
    except Exception as e:
        st.error(f"Error generating QR code: {e}")
        return None

if __name__ == "__main__":
    main()