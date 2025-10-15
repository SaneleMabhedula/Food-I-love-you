import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import calendar

# Page configuration
st.set_page_config(
    page_title="Finance Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #10b981;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .progress-bar {
        height: 0.5rem;
        border-radius: 0.25rem;
        background: #e5e7eb;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# Sample data (replace with your actual data source)
def load_sample_data():
    expenses = pd.DataFrame({
        'Date': [f'2024-04-{i:02d}' for i in range(1, 16)],
        'Amount': [45, 28, 15, 89, 125, 67, 34, 56, 72, 43, 98, 23, 65, 87, 32],
        'Category': ['Transport', 'Entertainment', 'Wants', 'Food', 'Food', 
                    'Needs', 'Transport', 'Entertainment', 'Wants', 'Food',
                    'Needs', 'Entertainment', 'Transport', 'Food', 'Wants'],
        'Description': ['Gas Station', 'Movie Tickets', 'Coffee', 'Grocery Shopping',
                       'Grocery Shopping', 'Utilities', 'Public Transport', 'Streaming',
                       'Dining Out', 'Groceries', 'Rent', 'Concert', 'Taxi', 
                       'Supermarket', 'Shopping']
    })
    
    income = pd.DataFrame({
        'Date': ['2024-04-01', '2024-04-15'],
        'Amount': [4500, 950],
        'Source': ['ABC Company', 'Freelance Project'],
        'Category': ['Salary', 'Freelance']
    })
    
    return expenses, income

expenses_df, income_df = load_sample_data()

# Sidebar navigation
st.sidebar.markdown("# 💰 Finance Tracker")
st.sidebar.markdown("Manage your money")

# Navigation options
nav_options = {
    "🏠 Dashboard": "dashboard",
    "➕ Add Income": "income",
    "➖ Add Expense": "expense",
    "🎯 Savings Goals": "savings",
    "📊 Reports": "reports"
}

selected_nav = st.sidebar.radio("Navigation", list(nav_options.keys()))

# Display current page based on selection
if nav_options[selected_nav] == "dashboard":
    # Dashboard View
    st.markdown('<div class="main-header">Financial Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">April 2024 Overview</div>', unsafe_allow_html=True)
    
    # KPI Metrics
    total_income = income_df['Amount'].sum()
    total_expenses = expenses_df['Amount'].sum()
    remaining_budget = total_income - total_expenses
    savings_goal = 2000
    current_savings = 1650
    savings_progress = (current_savings / savings_goal) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Income", f"${total_income:,.0f}", "+12% from last month")
    with col2:
        st.metric("Total Expenses", f"${total_expenses:,.0f}", "+8% from last month", delta_color="inverse")
    with col3:
        st.metric("Remaining Budget", f"${remaining_budget:,.0f}", "Available to spend")
    with col4:
        st.metric("Savings Goal", f"${current_savings:,.0f}", f"{savings_progress:.0f}% complete")
    
    st.divider()
    
    # Expense Breakdown Chart
    st.subheader("Expense Breakdown")
    st.write("How you spent your money this month")
    
    expense_by_category = expenses_df.groupby('Category')['Amount'].sum().reset_index()
    fig = px.pie(expense_by_category, values='Amount', names='Category', 
                 color_discrete_sequence=['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444'])
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent Transactions
    st.subheader("Recent Transactions")
    recent_transactions = pd.concat([
        income_df.assign(Type='Income'),
        expenses_df.assign(Type='Expense')
    ]).sort_values('Date', ascending=False).head(5)
    
    for _, transaction in recent_transactions.iterrows():
        amount_color = "green" if transaction['Type'] == 'Income' else "red"
        amount_prefix = "+" if transaction['Type'] == 'Income' else "-"
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{transaction.get('Description', transaction.get('Source', 'Transaction'))}**")
            st.caption(f"{transaction['Date']} • {transaction.get('Category', '')}")
        with col2:
            st.markdown(f"<span style='color: {amount_color}; font-weight: bold;'>{amount_prefix}${transaction['Amount']}</span>", 
                       unsafe_allow_html=True)
        
        st.divider()

elif nav_options[selected_nav] == "income":
    # Add Income Form
    st.markdown('<div class="main-header">Add Income</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Record your income to track your financial progress</div>', unsafe_allow_html=True)
    
    with st.form("income_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            amount = st.number_input("Amount *", min_value=0.0, step=0.01, format="%.2f")
            source = st.text_input("Income Source *", placeholder="e.g., ABC Company, Freelance Project")
        
        with col2:
            date_input = st.date_input("Date *", value=date.today())
            category = st.selectbox("Category *", ["Salary", "Freelance", "Business", "Investment", "Rental", "Gift", "Other"])
        
        description = st.text_area("Description (Optional)", placeholder="Add any additional notes about this income...")
        recurring = st.checkbox("This is a recurring income")
        
        submitted = st.form_submit_button("Add Income")
        if submitted:
            if amount and source and category:
                st.success(f"Income of ${amount:,.2f} added successfully!")
            else:
                st.error("Please fill in all required fields")
    
    # Recent Income
    st.subheader("Recent Income")
    for _, income in income_df.head(3).iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{income['Source']}**")
            st.caption(f"{income['Date']} • {income['Category']}")
        with col2:
            st.markdown(f"<span style='color: green; font-weight: bold;'>+${income['Amount']}</span>", 
                       unsafe_allow_html=True)
        st.divider()

elif nav_options[selected_nav] == "expense":
    # Add Expense Form
    st.markdown('<div class="main-header">Add Expense</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Track your spending and stay within budget</div>', unsafe_allow_html=True)
    
    with st.form("expense_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            amount = st.number_input("Amount *", min_value=0.0, step=0.01, format="%.2f")
            date_input = st.date_input("Date *", value=date.today())
        
        with col2:
            category = st.selectbox("Category *", ["Needs", "Wants", "Food", "Transport", "Entertainment", "Savings"])
            description = st.text_input("Description *", placeholder="e.g., Grocery shopping, Gas, Movie tickets")
        
        notes = st.text_area("Additional Notes (Optional)")
        recurring = st.checkbox("This is a recurring expense")
        
        submitted = st.form_submit_button("Add Expense")
        if submitted:
            if amount and description and category:
                st.success(f"Expense of ${amount:,.2f} added successfully!")
            else:
                st.error("Please fill in all required fields")
    
    # Recent Expenses
    st.subheader("Recent Expenses")
    for _, expense in expenses_df.head(4).iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{expense['Description']}**")
            st.caption(f"{expense['Date']} • {expense['Category']}")
        with col2:
            st.markdown(f"<span style='color: red; font-weight: bold;'>-${expense['Amount']}</span>", 
                       unsafe_allow_html=True)
        st.divider()

elif nav_options[selected_nav] == "savings":
    # Savings Goals
    st.markdown('<div class="main-header">Savings Goals</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Track your progress towards financial goals</div>', unsafe_allow_html=True)
    
    # Savings Overview
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Goals", "3")
    with col2:
        st.metric("Total Target", "$17,000")
    with col3:
        st.metric("Total Saved", "$10,500")
    
    st.divider()
    
    # Individual Goals
    goals = [
        {"name": "Emergency Fund", "target": 10000, "current": 6500, "category": "Security", "priority": "high"},
        {"name": "Vacation to Europe", "target": 5000, "current": 2800, "category": "Travel", "priority": "medium"},
        {"name": "New Laptop", "target": 2000, "current": 1200, "category": "Technology", "priority": "low"}
    ]
    
    for goal in goals:
        progress = (goal["current"] / goal["target"]) * 100
        remaining = goal["target"] - goal["current"]
        
        st.subheader(goal["name"])
        st.caption(f"{goal['category']} • {goal['priority'].title()} Priority")
        
        # Progress bar
        st.progress(progress / 100)
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**${goal['current']:,.0f} / ${goal['target']:,.0f}** ({progress:.0f}%)")
        with col2:
            st.write(f"**${remaining:,.0f} remaining**")
        
        # Quick add buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(f"+$50", key=f"add50_{goal['name']}"):
                st.success("Added $50 to your goal!")
        with col2:
            if st.button(f"+$100", key=f"add100_{goal['name']}"):
                st.success("Added $100 to your goal!")
        with col3:
            if st.button(f"+$250", key=f"add250_{goal['name']}"):
                st.success("Added $250 to your goal!")
        
        st.divider()

elif nav_options[selected_nav] == "reports":
    # Reports
    st.markdown('<div class="main-header">Financial Reports</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Analyze your financial patterns and trends</div>', unsafe_allow_html=True)
    
    # Income vs Expenses Chart
    st.subheader("Income vs Expenses Trend")
    
    # Create sample monthly data
    monthly_data = pd.DataFrame({
        'Month': ['Jan', 'Feb', 'Mar', 'Apr'],
        'Income': [4800, 5200, 4900, 5450],
        'Expenses': [3200, 3600, 3800, 3890]
    })
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Income', x=monthly_data['Month'], y=monthly_data['Income'], marker_color='#10b981'))
    fig.add_trace(go.Bar(name='Expenses', x=monthly_data['Month'], y=monthly_data['Expenses'], marker_color='#ef4444'))
    fig.update_layout(barmode='group')
    st.plotly_chart(fig, use_container_width=True)
    
    # Financial Insights
    st.subheader("Financial Insights")
    
    insights_col1, insights_col2 = st.columns(2)
    
    with insights_col1:
        st.success("""
        **Positive Trends**
        - Your savings rate improved by 5% this month
        - Food expenses decreased by $120 compared to last month
        - You're on track to meet your emergency fund goal
        """)
    
    with insights_col2:
        st.warning("""
        **Areas for Improvement**
        - Entertainment spending increased by 15% this month
        - Consider setting a stricter budget for "Wants" category
        - Transportation costs are above average
        """)
    
    # Category Breakdown
    st.subheader("Category Breakdown")
    category_stats = expenses_df.groupby('Category').agg({'Amount': ['sum', 'count']}).round(2)
    category_stats.columns = ['Total Amount', 'Number of Transactions']
    st.dataframe(category_stats, use_container_width=True)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### Total Savings")
st.sidebar.markdown("**$2,450**")
st.sidebar.caption("Across all savings goals")