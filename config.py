# Enhanced Menu Configuration
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

# Item status flow
ITEM_STATUS = {
    "pending": {"text": "⏳ Pending", "color": "#6C757D"},
    "preparing": {"text": "👨‍🍳 Preparing", "color": "#FFC107"}, 
    "ready": {"text": "✅ Ready", "color": "#28A745"},
    "served": {"text": "🎉 Served", "color": "#17A2B8"}
}

# Order types
ORDER_TYPES = {
    "dine_in": {"name": "🪑 Dine In", "icon": "🪑"},
    "takeaway": {"name": "🥡 Takeaway", "icon": "🥡"}
}