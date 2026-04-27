# api.py
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import sqlite3
import json
import os
import random
import time
from datetime import datetime
import traceback
import subprocess
import sys
from recommender_ga import ProductRecommenderGA


def ensure_database():
    """Create database from CSV files if it doesn't exist"""
    db_path = 'projject_database.db'
    if not os.path.exists(db_path):
        print("📦 Database not found. Creating from CSV files...")
        try:
            # Run create_db.py
            result = subprocess.run([sys.executable, 'create_db.py'], 
                                  capture_output=True, text=True, check=True)
            print(result.stdout)
            print("✅ Database created successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error creating database: {e.stderr}")
            # Try alternative: create tables directly
            create_tables_directly()
    else:
        print(f"✅ Database already exists ({db_path})")

def create_tables_directly():
    """Fallback: Create tables directly if create_db.py fails"""
    import sqlite3
    conn = sqlite3.connect('projject_database.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        age INTEGER,
        country TEXT,
        age_group TEXT,
        region TEXT,
        customer_segment TEXT
    )''')
    
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
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ratings (
        rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        rating INTEGER
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_behavior (
        behavior_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        viewed INTEGER,
        clicked INTEGER,
        purchased INTEGER
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Tables created directly (no data)")

# Call this when app starts
ensure_database()

if not os.path.exists('projject_database.db'):
    print("📦 Creating database on startup...")
    try:
        subprocess.run([sys.executable, 'create_db.py'], check=True)
        print("✅ Database created successfully!")
    except Exception as e:
        print(f"⚠️ Error creating database: {e}")

# =====================================================
# PRODUCT RECOMMENDER GA CLASS
# ====================================================
# =====================================================
# FLASK API CONFIGURATION
# =====================================================

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
DATABASE_PATH = 'projject_database.db'
OUTPUT_JSON_PATH = 'src/recommendations.json'

# Ensure the output directory exists
os.makedirs(os.path.dirname(OUTPUT_JSON_PATH), exist_ok=True)

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def execute_recommender(user_id, num_recommendations=10, force_refresh=True):
    """
    Execute the genetic algorithm recommender - ALWAYS FRESH
    
    Args:
        user_id: User ID to generate recommendations for
        num_recommendations: Number of recommendations to generate
        force_refresh: If True, always run GA fresh (ignore cache)
    """
    try:
        # Create FRESH instance each time with new random seed
        current_seed = int(time.time() * 1000) % 1000000
        recommender = ProductRecommenderGA(DATABASE_PATH, random_seed=current_seed)
        
        print(f"\n{'='*50}")
        print(f"🔄 Generating FRESH recommendations for user {user_id}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
        print(f"🎲 Random seed: {current_seed}")
        print(f"{'='*50}\n")
        
        # Run GA
        recommendations, algorithm_metrics, user_profile = recommender.recommend_products(
            user_id, 
            num_recommendations
        )
        
        if not recommendations:
            return None, "No recommendations found for this user"
        
        # Save with timestamp to avoid confusion
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        # Save to default location
        recommender.save_recommendations_to_json(
            user_id=user_id,
            recommendations=recommendations,
            algorithm_metrics=algorithm_metrics,
            user_profile=user_profile,
            output_file=OUTPUT_JSON_PATH
        )
        
        # Also save a timestamped copy
        timestamped_file = f'src/recommendations_user_{user_id}_{timestamp}.json'
        recommender.save_recommendations_to_json(
            user_id=user_id,
            recommendations=recommendations,
            algorithm_metrics=algorithm_metrics,
            user_profile=user_profile,
            output_file=timestamped_file
        )
        
        # Format recommendations for API response
        formatted_recs = []
        for product_id, score, product in recommendations:
            formatted_recs.append({
                "product_id": product_id,
                "product_name": product['product_name'],
                "category": product['category'],
                "subcategory": product['subcategory'],
                "price": product['price'],
                "price_tier": product['price_tier'],
                "seasonality": product['seasonality'],
                "recommendation_score": round(score, 2),
                "avg_rating": product.get('avg_rating', 0),
                "rating_count": product.get('rating_count', 0)
            })
        
        result = {
            "user_id": user_id,
            "user_profile": user_profile,
            "algorithm_metrics": algorithm_metrics,
            "recommendations": formatted_recs,
            "total_recommendations": len(formatted_recs),
            "timestamp": datetime.now().isoformat(),
            "run_id": timestamp,
            "random_seed": current_seed,
            "force_refresh": force_refresh
        }
        
        return result, None
        
    except Exception as e:
        print(f"❌ Error in execute_recommender: {str(e)}")
        traceback.print_exc()
        return None, str(e)

# =====================================================
# API ENDPOINTS
# =====================================================

@app.route('/')
def home():
    """Home page with API documentation"""
    return jsonify({
        "api_name": "Genetic Algorithm Product Recommender System",
        "version": "3.0",
        "status": "running",
        "note": "Each request generates FRESH recommendations using the Genetic Algorithm",
        "endpoints": {
            "/": "GET - API documentation",
            "/health": "GET - Check API health status",
            "/recommendations/<int:user_id>": "GET - Get fresh recommendations for user",
            "/recommendations/generate/<int:user_id>": "GET/POST - Force generate new recommendations",
            "/recommendations/refresh/<int:user_id>": "GET/POST - Complete refresh (clears cache)",
            "/products": "GET - Get all products",
            "/products/<int:product_id>": "GET - Get specific product",
            "/products/category/<category>": "GET - Get products by category",
            "/users": "GET - Get all users",
            "/users/<int:user_id>": "GET - Get user details",
            "/stats": "GET - Get database statistics",
            "/dashboard": "GET - Web dashboard"
        },
        "examples": {
            "get_recommendations": "/recommendations/3",
            "force_refresh": "/recommendations/refresh/3",
            "products_by_category": "/products/category/Electronics"
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    db_exists = os.path.exists(DATABASE_PATH)
    return jsonify({
        "status": "healthy" if db_exists else "degraded",
        "database_exists": db_exists,
        "database_path": DATABASE_PATH,
        "timestamp": datetime.now().isoformat()
    })

# =====================================================
# RECOMMENDATIONS ENDPOINTS
# =====================================================

@app.route('/recommendations/<int:user_id>', methods=['GET'])
def get_user_recommendations(user_id):
    """Get fresh recommendations for a specific user - ALWAYS GENERATES NEW"""
    try:
        num_recs = request.args.get('num_recommendations', 10, type=int)
        
        # Always generate fresh - no caching
        result, error = execute_recommender(user_id, num_recs, force_refresh=True)
        
        if error:
            return jsonify({"error": error}), 404
        
        return jsonify({
            "success": True,
            "message": f"Fresh recommendations generated for user {user_id}",
            "data": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

@app.route('/recommendations/generate/<int:user_id>', methods=['GET', 'POST'])
def generate_recommendations(user_id):
    """Force generation of NEW recommendations using the genetic algorithm"""
    try:
        num_recs = request.args.get('num_recommendations', 10, type=int)
        
        result, error = execute_recommender(user_id, num_recs, force_refresh=True)
        
        if error:
            return jsonify({
                "success": False,
                "error": error,
                "user_id": user_id
            }), 404
        
        return jsonify({
            "success": True,
            "message": f"✅ Fresh recommendations generated for user {user_id}",
            "note": "Each call runs the Genetic Algorithm from scratch with a new random seed",
            "generated_at": datetime.now().isoformat(),
            "data": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/recommendations/refresh/<int:user_id>', methods=['GET', 'POST'])
def refresh_recommendations(user_id):
    """
    Force complete refresh of recommendations
    - Deletes old cache
    - Runs GA with fresh random seed
    - Returns completely new recommendations
    """
    try:
        # Backup old recommendations file
        if os.path.exists(OUTPUT_JSON_PATH):
            backup_name = f'src/recommendations_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            try:
                os.rename(OUTPUT_JSON_PATH, backup_name)
                print(f"📦 Backed up old recommendations to {backup_name}")
            except:
                pass
        
        num_recs = request.args.get('num_recommendations', 10, type=int)
        result, error = execute_recommender(user_id, num_recs, force_refresh=True)
        
        if error:
            return jsonify({"error": error}), 404
        
        return jsonify({
            "success": True,
            "message": f"🔄 Recommendations completely refreshed for user {user_id}",
            "note": "This is a fresh run of the genetic algorithm with a new random seed",
            "data": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =====================================================
# PRODUCTS ENDPOINTS
# =====================================================

@app.route('/products', methods=['GET'])
def get_all_products():
    """Get all products with optional filtering"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        category = request.args.get('category')
        price_tier = request.args.get('price_tier')
        seasonality = request.args.get('seasonality')
        limit = request.args.get('limit', 100, type=int)
        
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        if price_tier:
            query += " AND price_tier = ?"
            params.append(price_tier)
        if seasonality:
            query += " AND seasonality = ?"
            params.append(seasonality)
        
        query += " LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        products = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "total": len(products),
            "products": products,
            "filters": {
                "category": category,
                "price_tier": price_tier,
                "seasonality": seasonality
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get specific product by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
        product = cursor.fetchone()
        
        conn.close()
        
        if product:
            return jsonify(dict(product))
        else:
            return jsonify({"error": f"Product {product_id} not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/products/category/<category>', methods=['GET'])
def get_products_by_category(category):
    """Get all products in a specific category"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM products WHERE category = ? ORDER BY price", 
            (category,)
        )
        products = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        if products:
            prices = [p['price'] for p in products]
            stats = {
                "count": len(products),
                "avg_price": round(sum(prices) / len(prices), 2),
                "min_price": min(prices),
                "max_price": max(prices)
            }
        else:
            stats = {"count": 0}
        
        return jsonify({
            "category": category,
            "statistics": stats,
            "products": products
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/products/categories', methods=['GET'])
def get_categories():
    """Get all unique product categories"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT category, COUNT(*) as count FROM products GROUP BY category")
        categories = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({"categories": categories})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =====================================================
# USERS ENDPOINTS
# =====================================================

@app.route('/users', methods=['GET'])
def get_all_users():
    """Get all users"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id, age, country, age_group, region, customer_segment FROM users LIMIT 100")
        users = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "total": len(users),
            "users": users
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get specific user details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({"error": f"User {user_id} not found"}), 404
        
        cursor.execute("""
            SELECT COUNT(*) as total_purchases, SUM(purchased) as items_purchased
            FROM user_behavior 
            WHERE user_id = ? AND purchased = 1
        """, (user_id,))
        behavior_stats = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*) as total_ratings, AVG(rating) as avg_rating
            FROM ratings 
            WHERE user_id = ?
        """, (user_id,))
        rating_stats = cursor.fetchone()
        
        conn.close()
        
        user_data = dict(user)
        user_data['statistics'] = {
            "purchases": dict(behavior_stats),
            "ratings": dict(rating_stats)
        }
        
        return jsonify(user_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/users/<int:user_id>/behavior', methods=['GET'])
def get_user_behavior(user_id):
    """Get user behavior history"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT b.*, p.product_name, p.category, p.price
            FROM user_behavior b
            JOIN products p ON b.product_id = p.product_id
            WHERE b.user_id = ?
            ORDER BY b.behavior_id DESC
            LIMIT 50
        """, (user_id,))
        
        behavior = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT 
                SUM(viewed) as total_views,
                SUM(clicked) as total_clicks,
                SUM(purchased) as total_purchases,
                ROUND(CAST(SUM(purchased) AS FLOAT) / NULLIF(SUM(clicked), 0) * 100, 2) as conversion_rate
            FROM user_behavior 
            WHERE user_id = ?
        """, (user_id,))
        
        summary = dict(cursor.fetchone())
        conn.close()
        
        return jsonify({
            "user_id": user_id,
            "summary": summary,
            "recent_behavior": behavior
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =====================================================
# STATISTICS ENDPOINTS
# =====================================================

@app.route('/stats', methods=['GET'])
def get_statistics():
    """Get database statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        users_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM products")
        products_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM ratings")
        ratings_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM user_behavior")
        behavior_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM products 
            GROUP BY category 
            ORDER BY count DESC
        """)
        categories = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT price_tier, COUNT(*) as count, AVG(price) as avg_price
            FROM products 
            GROUP BY price_tier
        """)
        price_tiers = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            "database": {
                "database_path": DATABASE_PATH,
                "tables": {
                    "users": users_count,
                    "products": products_count,
                    "ratings": ratings_count,
                    "user_behavior": behavior_count
                }
            },
            "product_analytics": {
                "total_products": products_count,
                "categories": categories,
                "price_tiers": price_tiers
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =====================================================
# WEB DASHBOARD
# =====================================================

@app.route('/dashboard')
def dashboard():
    """Simple HTML dashboard for testing"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GA Recommender Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
            h1 { color: #333; }
            .endpoint { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }
            .method { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; margin-right: 10px; }
            .get { background: #61affe; color: white; }
            .post { background: #49cc90; color: white; }
            input, button { padding: 8px; margin: 5px; }
            .result { background: #f8f8f8; padding: 15px; border-radius: 5px; margin-top: 20px; white-space: pre-wrap; font-family: monospace; max-height: 500px; overflow: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Genetic Algorithm Recommender System</h1>
            <p>Status: <strong style="color: green;">✓ Running</strong> | <strong>Fresh recommendations every time!</strong></p>
            
            <h2>Quick Test</h2>
            <div>
                <label>User ID:</label>
                <input type="number" id="userId" value="3">
                <button onclick="generateRecommendations()">Generate Fresh Recommendations</button>
                <button onclick="refreshRecommendations()">Complete Refresh</button>
            </div>
            <div id="result" class="result">Click a button to generate recommendations...</div>
            
            <h2>API Endpoints (All return fresh GA results)</h2>
            <div class="endpoint">
                <span class="method get">GET</span>
                <a href="#" onclick="testEndpoint('/recommendations/3')">/recommendations/&lt;user_id&gt;</a> - Get fresh recommendations
            </div>
            <div class="endpoint">
                <span class="method post">POST</span>
                <a href="#" onclick="testEndpoint('/recommendations/generate/3')">/recommendations/generate/&lt;user_id&gt;</a> - Force GA run
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <a href="#" onclick="testEndpoint('/products')">/products</a> - All products
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <a href="#" onclick="testEndpoint('/users')">/users</a> - All users
            </div>
            <div class="endpoint">
                <span class="method get">GET</span>
                <a href="#" onclick="testEndpoint('/stats')">/stats</a> - Statistics
            </div>
        </div>
        
        <script>
            async function testEndpoint(url) {
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = 'Loading...';
                try {
                    const response = await fetch(url);
                    const data = await response.json();
                    resultDiv.innerHTML = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultDiv.innerHTML = 'Error: ' + error.message;
                }
            }
            
            async function generateRecommendations() {
                const userId = document.getElementById('userId').value;
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = '🔄 Running Genetic Algorithm (this takes a few seconds)...';
                try {
                    const response = await fetch(`/recommendations/generate/${userId}`, {
                        method: 'POST'
                    });
                    const data = await response.json();
                    resultDiv.innerHTML = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultDiv.innerHTML = 'Error: ' + error.message;
                }
            }
            
            async function refreshRecommendations() {
                const userId = document.getElementById('userId').value;
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = '🔄 Complete refresh - clearing cache and running GA...';
                try {
                    const response = await fetch(`/recommendations/refresh/${userId}`, {
                        method: 'POST'
                    });
                    const data = await response.json();
                    resultDiv.innerHTML = JSON.stringify(data, null, 2);
                } catch (error) {
                    resultDiv.innerHTML = 'Error: ' + error.message;
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

# =====================================================
# ERROR HANDLERS
# =====================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# =====================================================
# MAIN
# =====================================================

if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists(DATABASE_PATH):
        print("⚠️  Warning: Database not found!")
        print(f"   Expected at: {DATABASE_PATH}")
        print("   Run 'python create_db.py' to create the database")
    else:
        # Get database size
        db_size = os.path.getsize(DATABASE_PATH) / (1024 * 1024)
        print(f"✅ Database found: {DATABASE_PATH} ({db_size:.2f} MB)")
    
    port = int(os.environ.get('PORT', 5001))
    
    print("\n" + "=" * 60)
    print("🎯 Genetic Algorithm Recommender API - FRESH RECOMMENDATIONS EVERY TIME")
    print("=" * 60)
    print(f"📁 Database: {DATABASE_PATH}")
    print(f"📄 Output JSON: {OUTPUT_JSON_PATH}")
    print(f"🌐 Server: http://localhost:{port}")
    print(f"📊 Dashboard: http://localhost:{port}/dashboard")
    print("=" * 60)
    print("\n✨ IMPORTANT: Each API call runs the Genetic Algorithm from scratch")
    print("   with a new random seed, ensuring fresh results every time!")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print(f"  GET  http://localhost:{port}/ - API Documentation")
    print(f"  GET  http://localhost:{port}/recommendations/3 - Get fresh recommendations")
    print(f"  POST http://localhost:{port}/recommendations/generate/3 - Force GA run")
    print(f"  GET  http://localhost:{port}/dashboard - Web Dashboard")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=port)