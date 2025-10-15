import streamlit as st

def check_staff_login():
    """Simple staff authentication"""
    if 'staff_logged_in' not in st.session_state:
        st.session_state.staff_logged_in = False
    
    return st.session_state.staff_logged_in

def staff_login():
    """Staff login form"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔐 Staff Login")
    
    password = st.sidebar.text_input("Staff Password", type="password")
    if st.sidebar.button("Login", key="staff_login"):
        # In production, use proper hashing - this is for demo
        if password == "staff123":  # Change this in production
            st.session_state.staff_logged_in = True
            st.rerun()
        else:
            st.sidebar.error("Incorrect password")
    
    return st.session_state.staff_logged_in