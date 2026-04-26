# create_db.py
import csv
import sqlite3

# Connect to database
conn = sqlite3.connect('projject_database.db')
cursor = conn.cursor()

def create_all_tables():
    # Drop existing tables (optional - removes old data)
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("DROP TABLE IF EXISTS ratings")
    cursor.execute("DROP TABLE IF EXISTS user_behavior")
    conn.commit()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        age INTEGER,
        country TEXT,
        age_group TEXT,
        region TEXT,
        customer_segment TEXT
    )
    ''')
    
    # Create products table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY,
        category TEXT,
        price REAL,
        product_name TEXT,
        subcategory TEXT,
        cost REAL,
        margin REAL,
        price_tier TEXT,
        seasonality TEXT
    )
    ''')
    
    # Create ratings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ratings (
        rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        rating INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )
    ''')
    
    # Create user_behavior table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_behavior (
        behavior_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        viewed INTEGER,
        clicked INTEGER,
        purchased INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )
    ''')
    
    print("✅ All tables created successfully!")

def insert_users():
    """Insert users from CSV"""
    try:
        f = open('user.csv', 'r', encoding='utf-8-sig')
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        
        def get_age_group(age):
            if age <= 29: return '18-29'
            elif age <= 39: return '30-39'
            elif age <= 49: return '40-49'
            elif age <= 59: return '50-59'
            else: return '60+'
        
        def get_region(country):
            gulf = ['Qatar', 'UAE', 'Saudi Arabia', 'Kuwait', 'Bahrain', 'Oman']
            if country.strip() in gulf:
                return 'Gulf Region'
            else:
                return 'North Africa'
        
        def get_life_stage(age):
            if age <= 29: return 'Young Adult'
            elif age <= 49: return 'Working Professional'
            elif age <= 59: return 'Established Adult'
            else: return 'Senior'
        
        count = 0
        for row in reader:
            if len(row) >= 3:
                user_id = int(row[0].strip())
                age = int(row[1].strip())
                country = row[2].strip()
                age_group = get_age_group(age)
                region = get_region(country)
                customer_segment = get_life_stage(age)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, age, country, age_group, region, customer_segment) 
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, age, country, age_group, region, customer_segment))
                count += 1
        
        conn.commit()
        print(f"✅ Inserted {count} users")
        f.close()
    except Exception as e:
        print(f"Error inserting users: {e}")

def insert_products():
    """Insert products from CSV"""
    try:
        f = open('product.csv', 'r', encoding='utf-8-sig')
        reader = csv.reader(f)
        header = next(reader)
        
        def get_price_tier(price):
            if price < 50: return 'Budget'
            if price < 100: return 'Economy'
            if price < 200: return 'Standard'
            if price < 500: return 'Premium'
            else: return 'Luxury'
        
        def get_seasonality(category):
            if category in ['Toys', 'Sports', 'Books']:
                return 'Seasonal'
            return 'Year-round'
        
        def get_product_name(category, product_id):
            names = {
                'Toys': ['Action Figure', 'Board Game', 'Doll', 'Lego Set', 'Puzzle', 'Stuffed Animal', 'Remote Control Car'],
                'Clothes': ['T-Shirt', 'Jeans', 'Jacket', 'Dress', 'Shirt', 'Sweater', 'Pants'],
                'Perfumes': ['Eau de Parfum', 'Cologne', 'Body Spray', 'Perfume Oil', 'Aftershave', 'Fragrance Mist'],
                'Sports': ['Soccer Ball', 'Basketball', 'Tennis Racket', 'Yoga Mat', 'Dumbbell', 'Running Shoes', 'Sports Bag'],
                'Home Appliances': ['Blender', 'Microwave', 'Toaster', 'Coffee Maker', 'Vacuum Cleaner', 'Air Fryer', 'Iron'],
                'Electronics': ['Headphones', 'Charger', 'Power Bank', 'USB Cable', 'Mouse', 'Keyboard', 'Speaker'],
                'Books': ['Novel', 'Textbook', 'Cookbook', 'Biography', 'Self-Help', 'Children Book', 'Science Book']
            }
            if category in names:
                category_names = names[category]
            else:
                category_names = ['Standard Product', 'Basic Item', 'Premium Item', 'Deluxe Version']
            index = product_id % len(category_names)
            return category_names[index]
        
        def get_subcategory(category):
            subcategories = {
                'Toys': ['Educational', 'Action', 'Puzzles', 'Dolls'],
                'Clothes': ['Men', 'Women', 'Kids', 'Accessories'],
                'Perfumes': ['Men', 'Women', 'Unisex', 'Premium'],
                'Sports': ['Outdoor', 'Indoor', 'Fitness', 'Team Sports'],
                'Home Appliances': ['Kitchen', 'Cleaning', 'Laundry', 'Heating/Cooling'],
                'Electronics': ['Audio', 'Mobile Accessories', 'Computer Accessories', 'Cables'],
                'Books': ['Fiction', 'Non-Fiction', 'Educational', 'Children']
            }
            if category in subcategories:
                cat_sub = subcategories[category]
            else:
                cat_sub = ['General']
            
            total = 0
            for letter in category:
                total += ord(letter)
            total *= len(category)
            index = total % len(cat_sub)
            return cat_sub[index]
        
        count = 0
        for row in reader:
            if len(row) >= 3:
                product_id = int(row[0].strip())
                category = row[1].strip()
                price = float(row[2].strip())
                
                product_name = get_product_name(category, product_id)
                subcategory = get_subcategory(category)
                cost = round(price * 0.6, 2)
                margin = round(((price - cost) / price) * 100, 2) if price > 0 else 0
                price_tier = get_price_tier(price)
                seasonality = get_seasonality(category)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO products 
                    (product_id, category, price, product_name, subcategory, cost, margin, price_tier, seasonality) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (product_id, category, price, product_name, subcategory, cost, margin, price_tier, seasonality))
                count += 1
        
        conn.commit()
        print(f"✅ Inserted {count} products")
        f.close()
    except Exception as e:
        print(f"Error inserting products: {e}")

def insert_ratings():
    """Insert ratings from CSV"""
    try:
        f = open('rating.csv', 'r', encoding='utf-8-sig')
        reader = csv.reader(f)
        header = next(reader)
        
        count = 0
        for row in reader:
            if len(row) >= 3:
                user_id = int(row[0].strip())
                product_id = int(row[1].strip())
                rating = int(row[2].strip())
                
                cursor.execute('''
                    INSERT INTO ratings (user_id, product_id, rating) 
                    VALUES (?, ?, ?)
                ''', (user_id, product_id, rating))
                count += 1
        
        conn.commit()
        print(f"✅ Inserted {count} ratings")
        f.close()
    except Exception as e:
        print(f"Error inserting ratings: {e}")

def insert_behavior():
    """Insert user behavior from CSV"""
    try:
        f = open('behavior.csv', 'r', encoding='utf-8-sig')
        reader = csv.reader(f)
        header = next(reader)
        
        count = 0
        for row in reader:
            if len(row) >= 5:
                user_id = int(row[0].strip())
                product_id = int(row[1].strip())
                viewed = int(row[2].strip())
                clicked = int(row[3].strip())
                purchased = int(row[4].strip())
                
                cursor.execute('''
                    INSERT INTO user_behavior (user_id, product_id, viewed, clicked, purchased) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, product_id, viewed, clicked, purchased))
                count += 1
        
        conn.commit()
        print(f"✅ Inserted {count} behavior records")
        f.close()
    except Exception as e:
        print(f"Error inserting behavior: {e}")

# Run all the functions
if __name__ == "__main__":
    print("=" * 50)
    print("Creating Database from CSV Files")
    print("=" * 50)
    
    create_all_tables()
    insert_users()
    insert_products()
    insert_ratings()
    insert_behavior()
    
    # Verify counts
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    
    print("=" * 50)
    print(f"✅ Database created successfully!")
    print(f"   Total users: {user_count}")
    print(f"   Total products: {product_count}")
    print(f"   Database file: projject_database.db")
    print("=" * 50)
    
    conn.close()