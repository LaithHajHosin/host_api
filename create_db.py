import csv
import sqlite3
import random
from faker import Faker

# Initialize Faker for generating fake data
fake = Faker()

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
    
    # Create users table with name, email, password
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
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
    """Insert users from CSV with fake names, emails, passwords"""
    try:
        # open the csv file for users
        f = open('user.csv', 'r', encoding='utf-8-sig')
        reader = csv.reader(f)
        
        # skip the header row because it has column names not data
        header = next(reader)
        
        # helper function to make random ages for users 
        def get_age_group(age):
            if age <= 29: return '18-29'
            elif age <= 39: return '30-39'
            elif age <= 49: return '40-49'
            elif age <= 59: return '50-59'
            else: return '60+'
        
        # helper function to make random regions for users 
        def get_region(country):
            gulf = ['Qatar', 'UAE', 'Saudi Arabia', 'Kuwait', 'Bahrain', 'Oman']
            if country.strip() in gulf:
                return 'Gulf Region'
            else:
                return 'North Africa'
        
        # helper function to make the proper definition for users based on ages
        def get_life_stage(age):
            if age <= 29:
                return 'Young Adult' 
            if age <= 49:
                return 'Working Professional'
            if age <= 59:
                return 'Established Adult'
            else:
                return 'Senior'
        
        count = 0
        for row in reader:
            if len(row) >= 3:
                # get id , age ,country from csv files 
                user_id = int(row[0].strip())
                age = int(row[1].strip())
                country = row[2].strip()
                
                # Generate fake name, email, password
                name = fake.name()
                email = f"user{user_id}@{fake.domain_name()}"
                password = "pass123"  # Simple password for demo
                
                # add extra informations to users
                age_group = get_age_group(age)
                region = get_region(country)
                customer_segment = get_life_stage(age)
                
                # insert into database with new fields
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, name, email, password, age, country, age_group, region, customer_segment) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, name, email, password, age, country, age_group, region, customer_segment))
                count += 1
        
        conn.commit()
        print(f"✅ Inserted {count} users with fake names, emails, and passwords")
        f.close()
        
    except Exception as e:
        print(f"Something went wrong with users: {e}")
        # If CSV doesn't exist, generate fake users
        print("Generating fake users instead...")
        generate_fake_users()


def generate_fake_users(count=100):
    """Generate fake users if CSV doesn't exist"""
    countries = ['Qatar', 'UAE', 'Saudi Arabia', 'Kuwait', 'Bahrain', 'Oman', 'Egypt', 'Morocco', 'Jordan', 'Lebanon']
    
    for user_id in range(1, count + 1):
        # Generate fake data
        name = fake.name()
        email = f"user{user_id}@{fake.domain_name()}"
        password = "pass123"
        age = random.randint(18, 70)
        country = random.choice(countries)
        
        # Calculate derived fields
        if age <= 29:
            age_group = '18-29'
            customer_segment = 'Young Adult'
        elif age <= 39:
            age_group = '30-39'
            customer_segment = 'Working Professional'
        elif age <= 49:
            age_group = '40-49'
            customer_segment = 'Working Professional'
        elif age <= 59:
            age_group = '50-59'
            customer_segment = 'Established Adult'
        else:
            age_group = '60+'
            customer_segment = 'Senior'
        
        # Calculate region
        gulf = ['Qatar', 'UAE', 'Saudi Arabia', 'Kuwait', 'Bahrain', 'Oman']
        region = 'Gulf Region' if country in gulf else 'North Africa'
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, name, email, password, age, country, age_group, region, customer_segment) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, email, password, age, country, age_group, region, customer_segment))
    
    conn.commit()
    print(f"✅ Generated {count} fake users with names, emails, and passwords")


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
        # Generate fake products if CSV doesn't exist
        generate_fake_products()


def generate_fake_products(count=200):
    """Generate fake products if CSV doesn't exist"""
    categories = ['Electronics', 'Clothes', 'Books', 'Sports', 'Home Appliances', 'Perfumes', 'Toys']
    price_tiers = ['Budget', 'Economy', 'Standard', 'Premium', 'Luxury']
    seasonality = ['Seasonal', 'Year-round']
    
    for product_id in range(1, count + 1):
        category = random.choice(categories)
        price = round(random.uniform(10, 2000), 2)
        
        # Generate product name based on category
        if category == 'Electronics':
            product_name = random.choice(['Smartphone', 'Laptop', 'Headphones', 'Charger', 'Power Bank', 'Speaker'])
        elif category == 'Clothes':
            product_name = random.choice(['T-Shirt', 'Jeans', 'Jacket', 'Dress', 'Shirt', 'Sweater'])
        elif category == 'Books':
            product_name = random.choice(['Novel', 'Textbook', 'Cookbook', 'Biography', 'Self-Help'])
        elif category == 'Sports':
            product_name = random.choice(['Soccer Ball', 'Basketball', 'Tennis Racket', 'Yoga Mat', 'Dumbbell'])
        elif category == 'Home Appliances':
            product_name = random.choice(['Blender', 'Microwave', 'Toaster', 'Coffee Maker', 'Vacuum Cleaner'])
        elif category == 'Perfumes':
            product_name = random.choice(['Cologne', 'Perfume', 'Body Spray', 'Aftershave', 'Fragrance Mist'])
        else:
            product_name = random.choice(['Action Figure', 'Board Game', 'Doll', 'Puzzle', 'Stuffed Animal'])
        
        subcategory = random.choice(['Standard', 'Premium', 'Basic', 'Deluxe'])
        cost = round(price * 0.6, 2)
        margin = round(((price - cost) / price) * 100, 2) if price > 0 else 0
        price_tier = price_tiers[min(int(price / 400), 4)]
        seasonality = random.choice(seasonality)
        
        cursor.execute('''
            INSERT OR REPLACE INTO products 
            (product_id, category, price, product_name, subcategory, cost, margin, price_tier, seasonality) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product_id, category, price, product_name, subcategory, cost, margin, price_tier, seasonality))
    
    conn.commit()
    print(f"✅ Generated {count} fake products")


def insert_ratings():
    """Insert ratings from CSV or generate fake ones"""
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
        generate_fake_ratings()


def generate_fake_ratings():
    """Generate fake ratings if CSV doesn't exist"""
    # Get user and product counts
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    
    if user_count == 0 or product_count == 0:
        print("No users or products found, skipping ratings")
        return
    
    count = 0
    for user_id in range(1, min(user_count, 500) + 1):
        # Each user rates 10-50 products
        num_ratings = random.randint(10, 50)
        rated_products = random.sample(range(1, min(product_count, 500) + 1), min(num_ratings, product_count))
        
        for product_id in rated_products:
            rating = random.randint(1, 5)
            cursor.execute('''
                INSERT INTO ratings (user_id, product_id, rating) 
                VALUES (?, ?, ?)
            ''', (user_id, product_id, rating))
            count += 1
    
    conn.commit()
    print(f"✅ Generated {count} fake ratings")


def insert_behavior():
    """Insert user behavior from CSV or generate fake ones"""
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
        generate_fake_behavior()


def generate_fake_behavior():
    """Generate fake user behavior if CSV doesn't exist"""
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    
    if user_count == 0 or product_count == 0:
        print("No users or products found, skipping behavior")
        return
    
    count = 0
    for user_id in range(1, min(user_count, 200) + 1):
        # Each user interacts with 20-80 products
        num_interactions = random.randint(20, 80)
        interacted_products = random.sample(range(1, min(product_count, 500) + 1), min(num_interactions, product_count))
        
        for product_id in interacted_products:
            viewed = 1
            clicked = random.choice([0, 1])
            purchased = random.choice([0, 1]) if clicked == 1 else 0
            
            cursor.execute('''
                INSERT INTO user_behavior (user_id, product_id, viewed, clicked, purchased) 
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, product_id, viewed, clicked, purchased))
            count += 1
    
    conn.commit()
    print(f"✅ Generated {count} fake behavior records")


# Run all the functions
if __name__ == "__main__":
    print("=" * 50)
    print("Creating Database from CSV Files (with fake user data)")
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
    
    # Show a sample user
    cursor.execute("SELECT user_id, name, email, password, age, country FROM users LIMIT 5")
    sample_users = cursor.fetchall()
    
    print("\n" + "=" * 50)
    print(f"✅ Database created successfully!")
    print(f"   Total users: {user_count}")
    print(f"   Total products: {product_count}")
    print("\n📝 Sample users created:")
    for user in sample_users:
        print(f"   ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Password: {user[3]}, Age: {user[4]}, Country: {user[5]}")
    print("=" * 50)
    
    conn.close()
    print("\n✅ Done!")