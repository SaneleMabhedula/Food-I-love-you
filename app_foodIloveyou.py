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

from database import RestaurantDB
from config import MENU_CATEGORIES, ITEM_STATUS, ORDER_TYPES
from auth import staff_login, check_staff_login

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
    with open('styles/custom.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

def main():
    # Check URL parameters for customer view
    query_params = st.experimental_get_query_params()
    order_id = query_params.get('order_id', [None])[0]
    table_number = query_params.get('table', [None])[0]
    
    if order_id:
        # Customer order tracking view
        customer_order_tracking(order_id)
    elif table_number:
        # Customer ordering view for specific table
        customer_ordering(table_number)
    else:
        # Main navigation
        show_main_navigation()

def show_main_navigation():
    """Show role-based navigation"""
    
    # Check if staff is logged in
    is_staff = check_staff_login()
    
    if not is_staff:
        # Show staff login in sidebar
        if staff_login():
            st.rerun()
    
    st.sidebar.title("🍔 Restaurant Dashboard")
    
    if is_staff:
        # Staff navigation
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
        # Customer navigation (simple)
        st.markdown('<div class="customer-view">', unsafe_allow_html=True)
        customer_ordering()
        st.markdown('</div>', unsafe_allow_html=True)

def customer_ordering(prefilled_table=None):
    """Customer ordering interface - clean and simple"""
    
    st.markdown('<div class="main-header">🍔 Welcome to Our Restaurant!</div>', unsafe_allow_html=True)
    
    # Order type selection
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
                value=int(prefilled_table) if prefilled_table else 1,
                help="Enter your table number"
            )
        else:
            table_number = None
            st.info("🥡 Takeaway order - no table needed")
    
    customer_name = st.text_input("Your Name (Optional)", placeholder="Enter your name for the order")
    
    st.markdown("---")
    
    # Ordering interface
    order_items = []
    total_amount = 0
    
    # Display menu by categories with enhanced styling
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
                            <h4>{item_data['name']}</h4>
                            <p>💰 R{item_data['price']:.2f}</p>
                            <p>⏱️ ~{item_data['prep_time']}min</p>
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
    
    # Order summary and submission
    if order_items:
        st.subheader("📋 Order Summary")
        
        summary_df = pd.DataFrame(order_items)
        st.dataframe(summary_df[['name', 'quantity', 'price']], hide_index=True)
        
        st.markdown(f"### 💰 Total Amount: R{total_amount:.2f}")
        
        if st.button("🚀 Place Order", type="primary", use_container_width=True):
            if total_amount > 0:
                order_id = db.create_order(
                    table_number, 
                    customer_name, 
                    order_items, 
                    total_amount, 
                    order_type
                )
                
                show_order_confirmation(order_id, table_number, customer_name, order_type, order_items)
            else:
                st.error("Please add items to your order before submitting.")

def show_order_confirmation(order_id, table_number, customer_name, order_type, order_items):
    """Show order confirmation and tracking info"""
    
    st.success("🎉 Order placed successfully!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Order ID:** `{order_id}`")
        if order_type == 'dine_in':
            st.info(f"**Table:** {table_number}")
        st.info(f"**Customer:** {customer_name if customer_name else 'Not provided'}")
        st.info(f"**Order Type:** {ORDER_TYPES[order_type]['name']}")
        
        # Estimated wait time
        max_prep_time = max(item['prep_time'] for item in order_items)
        st.info(f"**Estimated wait time:** ~{max_prep_time} minutes")
    
    with col2:
        # Generate tracking QR code
        tracking_url = f"http://localhost:8501/?order_id={order_id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(tracking_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        st.image(buffered, width=200)
        st.caption("Scan to track your order")
    
    # Live order tracking
    st.markdown("---")
    st.subheader("📱 Live Order Tracking")
    st.write("**Your order status will update here in real-time:**")
    
    # Create placeholder for live updates
    status_placeholder = st.empty()
    items_placeholder = st.empty()
    
    # Simulate live updates
    for i in range(120):  # 2 minutes of updates
        order = db.get_customer_order(order_id)
        
        if order:
            display_order_status(order, status_placeholder, items_placeholder)
        
        time.sleep(2)  # Update every 2 seconds

def display_order_status(order, status_placeholder, items_placeholder):
    """Display current order status for customer"""
    
    with status_placeholder.container():
        # Overall order status
        status_display = "⏳ Order Received"
        if order['status'] == 'preparing':
            status_display = "👨‍🍳 Preparing Your Order"
        elif order['status'] == 'partially_ready':
            status_display = "🎉 Some Items Ready!"
        elif order['status'] == 'ready':
            status_display = "✅ Order Ready for Pickup!"
        
        st.markdown(f"### {status_display}")
        
        # Progress visualization
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
        # Individual item status
        st.write("**Item Status:**")
        for item in order['items']:
            status_info = ITEM_STATUS.get(item['item_status'], ITEM_STATUS['pending'])
            st.markdown(f'''
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.5rem 0;">
                    <span>{item['name']} (x{item['quantity']})</span>
                    <span class="item-status-badge" style="background-color: {status_info['color']}20; color: {status_info['color']}; border: 1px solid {status_info['color']};">
                        {status_info['text']}
                    </span>
                </div>
            ''', unsafe_allow_html=True)

def customer_order_tracking(order_id):
    """Dedicated page for customers to track their order"""
    
    st.markdown('<div class="customer-view">', unsafe_allow_html=True)
    
    order = db.get_customer_order(order_id)
    
    if not order:
        st.error("Order not found. Please check your Order ID.")
        return
    
    st.markdown(f'<div class="main-header">📱 Order Tracking</div>', unsafe_allow_html=True)
    
    # Order info
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
    
    # Live status updates
    status_placeholder = st.empty()
    items_placeholder = st.empty()
    
    while True:
        order = db.get_customer_order(order_id)
        if order:
            display_order_status(order, status_placeholder, items_placeholder)
        time.sleep(3)  # Update every 3 seconds

def kitchen_display():
    """Staff kitchen display with item-level status control"""
    
    st.markdown('<div class="staff-view">', unsafe_allow_html=True)
    st.markdown('<div class="main-header">👨‍🍳 Kitchen Command Center</div>', unsafe_allow_html=True)
    
    # Auto-refresh
    auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)
    
    if auto_refresh:
        time.sleep(3)
        st.rerun()
    
    # Get all active orders
    orders = db.get_orders()
    active_orders = [order for order in orders if order['status'] != 'completed']
    
    if not active_orders:
        st.info("No active orders. Time for a break! ☕")
        return
    
    # Display orders in columns by status
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
    """Display orders filtered by status"""
    
    filtered_orders = [order for order in orders if order['status'] == status]
    
    for order in filtered_orders:
        with column:
            status_class = f"status-{status}"
            with st.container():
                st.markdown(f'<div class="order-card {status_class}">', unsafe_allow_html=True)
                
                # Order header
                st.write(f"**Order:** `{order['order_id']}`")
                st.write(f"**Type:** {ORDER_TYPES[order['order_type']]['name']}")
                if order['order_type'] == 'dine_in':
                    st.write(f"**Table:** {order['table_number']}")
                if order['customer_name']:
                    st.write(f"**Customer:** {order['customer_name']}")
                
                st.write("---")
                
                # Individual item controls
                st.write("**Items:**")
                for item in order['items']:
                    col_item1, col_item2 = st.columns([3, 2])
                    
                    with col_item1:
                        st.write(f"- {item['name']} (x{item['quantity']})")
                    
                    with col_item2:
                        current_status = item.get('item_status', 'pending')
                        status_info = ITEM_STATUS.get(current_status, ITEM_STATUS['pending'])
                        
                        # Status update buttons
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

# [Rest of the functions (analytics_dashboard, qr_generator) remain similar but with enhanced styling]

if __name__ == "__main__":
    main()