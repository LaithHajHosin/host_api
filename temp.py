import sqlite3  # For database operations to fetch user and product data
import random   # For random selection in genetic algorithm (selection, mutation, initialization)
import math     # For mathematical operations (though not heavily used here)
import json     # For saving recommendations to JSON file
from datetime import datetime  # For timestamping the output
from collections import OrderedDict

# Simple cache for product features
class _ProductCache:
    def __init__(self, maxsize=500):
        self.cache = OrderedDict()
        self.maxsize = maxsize
    
    def get(self, product_id):
        if product_id in self.cache:
            self.cache.move_to_end(product_id)
            return self.cache[product_id]
        return None
    
    def set(self, product_id, features):
        if product_id in self.cache:
            self.cache.move_to_end(product_id)
        self.cache[product_id] = features
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)
    
    def clear(self):
        self.cache.clear()

class ProductRecommenderGA:
    """Genetic Algorithm based Product Recommender System"""
    
    def __init__(self, db_path):
        """Initialize the recommender with database connection and GA parameters"""
        # Connect to SQLite database
        self.conn = sqlite3.connect(db_path)
        # Set row_factory to return rows as dictionaries (access by column name)
        self.conn.row_factory = sqlite3.Row
        
        # Genetic Algorithm hyperparameters
        self.population_size = 50    # Number of chromosomes (recommendation sets) in population
        self.generations = 30        # Number of evolution cycles to run
        self.mutation_rate = 0.1     # Probability of mutating each gene (10%)
        self.crossover_rate = 0.7    # Probability of crossover between parents (70%)
        
        # Initialize product cache
        self._product_cache = _ProductCache(maxsize=500)
        
    def get_user_embedding(self, user_id):
        """
        Create a user preference vector (embedding) from their ratings and behavior
        This represents the user's taste profile similar to a query vector in information retrieval
        """
        cursor = self.conn.cursor()
        
        # Get the user information (age, region, customer segment)
        cursor.execute("""
            SELECT age_group, region, customer_segment, age, country
            FROM users WHERE user_id = ?
        """, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return None  # User doesn't exist in database
            
        # Get user's average rating per product category (what they rate highly)
        cursor.execute("""
            SELECT p.category, AVG(r.rating) as avg_rating
            FROM ratings r
            JOIN products p ON r.product_id = p.product_id
            WHERE r.user_id = ?
            GROUP BY p.category
        """, (user_id,))
        
        category_ratings = cursor.fetchall()
        
        # Get user's purchase behavior per category (what they actually buy)
        cursor.execute("""
            SELECT p.category, COUNT(*) as purchase_count
            FROM user_behavior b
            JOIN products p ON b.product_id = p.product_id
            WHERE b.user_id = ? AND b.purchased = 1
            GROUP BY p.category
        """, (user_id,))
        
        purchase_history = cursor.fetchall()
        
        # Get total purchase count
        cursor.execute("""
            SELECT COUNT(*) as total_purchased
            FROM user_behavior 
            WHERE user_id = ? AND purchased = 1
        """, (user_id,))
        
        purchase_count = cursor.fetchone()
        
        # Create embedding as a dictionary (feature vector)
        embedding = {
            'id': user_id,
            'age_group': user['age_group'],          #  age 
            'region': user['region'],                 # region
            'customer_segment': user['customer_segment'],  # Marketing segment
            'age': user['age'],                       # Actual age
            'country': user['country'],               # Country
            'purchased_count': purchase_count['total_purchased'] if purchase_count else 0,
            'category_preferences': {},               # Ratings preferences
            'purchase_strength': {}                   # Purchase preferences
        }
        
        # Normalize rating preferences (0 to 1)
        for row in category_ratings:
            embedding['category_preferences'][row['category']] = row['avg_rating'] / 5.0
        
        # Normalize purchase strength (10+ purchases = max strength)
        for row in purchase_history:
            embedding['purchase_strength'][row['category']] = min(row['purchase_count'] / 10.0, 1.0)
        
        return embedding
    
    def get_product_features(self, product_id):
        """
        Extract all relevant features from a product
        These features will be used to calculate compatibility with user preferences
        """
        # Check cache first
        cached_features = self._product_cache.get(product_id)
        if cached_features is not None:
            return cached_features
        
        cursor = self.conn.cursor()
        
        # Get basic product information
        cursor.execute("""
            SELECT product_id, category, price, price_tier, 
                   seasonality, margin, subcategory, product_name
            FROM products 
            WHERE product_id = ?
        """, (product_id,))
        
        product = cursor.fetchone()
        if not product:
            return None
        
        # Get product's average rating from all users (social proof)
        cursor.execute("""
            SELECT AVG(rating) as avg_rating, COUNT(rating) as rating_count
            FROM ratings WHERE product_id = ?
        """, (product_id,))
        
        rating_data = cursor.fetchone()
        
        # Get total purchase count (popularity metric)
        cursor.execute("""
            SELECT COUNT(*) as purchase_count
            FROM user_behavior 
            WHERE product_id = ? AND purchased = 1
        """, (product_id,))
        
        purchase_data = cursor.fetchone()
        
        # Compile all features into a dictionary
        features = {
            'product_id': product['product_id'],
            'product_name': product['product_name'],
            'category': product['category'],
            'subcategory': product['subcategory'],
            'price': product['price'],
            'price_tier': product['price_tier'],      # Budget, Economy, Standard, Premium, Luxury
            'seasonality': product['seasonality'],    # Seasonal or Year-round
            'margin': product['margin'],              # Profit margin for business
            'avg_rating': rating_data['avg_rating'] if rating_data['avg_rating'] else 0,
            'rating_count': rating_data['rating_count'] if rating_data['rating_count'] else 0,
            'purchase_count': purchase_data['purchase_count'] if purchase_data['purchase_count'] else 0
        }
        
        # Store in cache
        self._product_cache.set(product_id, features)
        
        return features
    
    def calculate_product_score(self, user_embedding, product_features):
        """
        Calculate fitness score for a single product
        This is like a similarity/distance function between user and product
        Higher score = better match
        """
        if not user_embedding or not product_features:
            return 0.0
        
        score = 0.0
        
        # Weighted scoring: different features contribute differently to final score
        weights = {
            'category_match': 0.30,       # Category relevance is most important (30%)
            'price_match': 0.20,          # Price appropriateness (20%)
            'rating_quality': 0.20,       # Product quality/satisfaction (20%)
            'popularity': 0.15,           # Social proof (15%)
            'seasonality_match': 0.10,    # Seasonal relevance (10%)
            'margin_preference': 0.05     # Business objective (5%)
        }
        
        # 1. Category Match Score - does user like this category?
        category_score = 0.0
        
        # Check if user has rated products in this category
        if product_features['category'] in user_embedding['category_preferences']:
            category_score = user_embedding['category_preferences'][product_features['category']]
        # If not rated, check purchase history
        elif product_features['category'] in user_embedding['purchase_strength']:
            category_score = user_embedding['purchase_strength'][product_features['category']] * 0.8
        # If no history, use region-based defaults (cold start handling)
        else:
            # we will assume he has some intrest in it
            category_score = 0.6
        
        score += weights['category_match'] * category_score
        
        # user (affordability)
        price_tier_preferences = {
            'Young Adult': {'Budget': 0.8, 'Economy': 0.7, 'Standard': 0.5, 'Premium': 0.3, 'Luxury': 0.1},
            'Working Professional': {'Budget': 0.3, 'Economy': 0.5, 'Standard': 0.8, 'Premium': 0.7, 'Luxury': 0.4},
            'Established Adult': {'Budget': 0.2, 'Economy': 0.3, 'Standard': 0.6, 'Premium': 0.8, 'Luxury': 0.6},
            'Senior': {'Budget': 0.6, 'Economy': 0.7, 'Standard': 0.6, 'Premium': 0.4, 'Luxury': 0.2}
        }
        
        segment = user_embedding.get('customer_segment', 'Working Professional')
        price_score = price_tier_preferences.get(segment, {}).get(product_features['price_tier'], 0.5)
        score += weights['price_match'] * price_score
        
        # user average rating 
        if product_features['avg_rating'] > 0:
            rating_score = product_features['avg_rating'] / 5.0
            # Boost score if many people rated it (statistical confidence)
            rating_count_boost = min(product_features['rating_count'] / 100.0, 0.2)
            rating_score = min(rating_score + rating_count_boost, 1.0)
        else:
            rating_score = 0.5  # Default for unrated products
        score += weights['rating_quality'] * rating_score
        
        # people ratings
        popularity_score = min(product_features['purchase_count'] / 50.0, 1.0)
        score += weights['popularity'] * popularity_score
        
        # product seasonal
        seasonality_score = 1.0 if product_features['seasonality'] == 'Year-round' else 0.7
        score += weights['seasonality_match'] * seasonality_score
        
        # popular products
        margin_score = min(product_features['margin'] / 50.0, 1.0)
        score += weights['margin_preference'] * margin_score
        
        return score
    
    def get_candidate_products(self, user_id, limit=500):
        """
        Get initial pool of candidate products for recommendation
        Excludes products user has already purchased OR rated highly (≥4 stars)
        This prevents recommending items the user already knows about
        """
        cursor = self.conn.cursor()
        
        # Using NOT EXISTS for efficiency - filter out purchased and highly rated products
        cursor.execute("""
            SELECT DISTINCT p.product_id
            FROM products p
            WHERE NOT EXISTS (
                SELECT 1 FROM user_behavior 
                WHERE user_id = ? 
                AND product_id = p.product_id 
                AND purchased = 1
            )
            AND NOT EXISTS (
                SELECT 1 FROM ratings 
                WHERE user_id = ? 
                AND product_id = p.product_id 
                AND rating >= 4
            )
            LIMIT ?
        """, (user_id, user_id, limit))
        
        products = [row['product_id'] for row in cursor.fetchall()]
        return products
    
    def create_chromosome(self, product_pool, size=10):
        """
        Create a chromosome (individual in GA population)
        A chromosome is a set of product recommendations (list of product IDs)
        """
        if len(product_pool) <= size:
            return product_pool[:]  # Return all if pool is small
        return random.sample(product_pool, size)  # Randomly select 'size' products
    
    def calculate_chromosome_fitness(self, chromosome, user_embedding):
        """
        Calculate total fitness for a chromosome (recommendation set)
        Fitness = average of individual product scores
        This represents how good this entire recommendation list is
        
        NOTE: This now queries the database for each product every time it's called
        """
        if not chromosome:
            return 0.0
        
        total_score = 0.0
        for product_id in chromosome:
            # fetch product
            product_features = self.get_product_features(product_id)
            if product_features:
                score = self.calculate_product_score(user_embedding, product_features)
                total_score += score
        
        # Return average score 0 - 10
        return total_score / len(chromosome)
    
    def selection_tournament(self, population, fitness_scores, tournament_size=3):
        """
        Tournament selection for parent selection in GA
        Randomly pick 'tournament_size' individuals, the one with highest fitness wins
        This maintains selection pressure while preserving diversity
        """
        new_population = []
        
        for _ in range(len(population)):
            # Randomly select tournament participants
            tournament_indices = random.sample(range(len(population)), tournament_size)
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            
            # Find winner (highest fitness)
            winner_idx = tournament_indices[tournament_fitness.index(max(tournament_fitness))]
            new_population.append(population[winner_idx][:])  # Deep copy to avoid reference issues
        
        return new_population
    
    def crossover(self, parent1, parent2):
        """
        Single-point crossover between two parent chromosomes
        Creates two children by swapping segments at a random point
        """
        # Apply crossover only with probability = crossover_rate
        if random.random() > self.crossover_rate:
            return parent1[:], parent2[:]  # No crossover
        
        # Choose random crossover point 
        crossover_point = random.randint(1, min(len(parent1), len(parent2)) - 1)
        
        # Create children by swapping segments
        child1 = parent1[:crossover_point] + parent2[crossover_point:]
        child2 = parent2[:crossover_point] + parent1[crossover_point:]
        
        # Remove duplicate product IDs (same product shouldn't appear twice in recommendations)
        child1 = self.remove_duplicates(child1)
        child2 = self.remove_duplicates(child2)
        
        return child1, child2
    
    def remove_duplicates(self, chromosome):
        """
        Remove duplicate product IDs from a chromosome
        Preserves order of first occurrence
        """
        seen = set()
        unique_chromosome = []
        for product_id in chromosome:
            if product_id not in seen:
                seen.add(product_id)
                unique_chromosome.append(product_id)
        return unique_chromosome
    
    def mutate(self, chromosome, product_pool, mutation_rate=0.1):
        """
        Mutate chromosome by randomly replacing some products with new ones
        Mutation introduces genetic diversity and prevents premature convergence
        """
        if mutation_rate is None:
            print("no")
            mutation_rate = self.mutation_rate
        
        mutated = chromosome[:]
        
        # Mutate each gene independently
        for i in range(len(mutated)):
            if random.random() < mutation_rate:
                # Replace with a random product from the pool
                if product_pool:
                    new_product = random.choice(product_pool)
                    mutated[i] = new_product
        
        # Clean up duplicates after mutation
        mutated = self.remove_duplicates(mutated)
        
        # Ensure at least one recommendation
        if not mutated and product_pool:
            mutated = [random.choice(product_pool)]
        
        return mutated
    
    def get_suboptimal_results(self, population, fitness_scores, user_embedding, top_k=3):
        """
        Collect suboptimal results from different generations (diversity strategy)
        Instead of just taking the best chromosome, take top K and add some random products
        This provides recommendation diversity as suggested in the research paper
        
        NOTE: This now queries the database directly for random product selection
        """
        # Sort chromosomes by fitness
        sorted_pairs = sorted(zip(fitness_scores, population), reverse=True)
        
        suboptimal_results = []
        # Take top K chromosomes and add all their products
        for i in range(min(top_k, len(sorted_pairs))):
            fitness, chromosome = sorted_pairs[i]
            suboptimal_results.extend(chromosome)
        
        # Add random products for diversity
        cursor = self.conn.cursor()
        cursor.execute("SELECT product_id FROM products LIMIT 1000")
        all_products = [row['product_id'] for row in cursor.fetchall()]
        
        if len(all_products) > 20:
            suboptimal_results.extend(random.sample(all_products, min(5, len(all_products))))
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for pid in suboptimal_results:
            if pid not in seen:
                seen.add(pid)
                unique_results.append(pid)
        
        return unique_results
    
    def recommend_products(self, user_id, num_recommendations=10):
        """
        Main GA recommendation engine - orchestrates the entire recommendation process
        This is the public API method that clients call to get recommendations
        
        NOTE: This version makes database queries for product features each time they're needed
        """
        
        # 1 Get user embedding (user preference profile)
        print(f"starting the genetic algorithm for user with ID: {user_id}")
        user_embedding = self.get_user_embedding(user_id)
        if not user_embedding:
            print(f"User {user_id} not found!")
            return [], None
        
        # 2 Get candidate products
        product_pool = self.get_candidate_products(user_id, limit=600)
        if len(product_pool) < num_recommendations:
            print("Not enough products available!")
            return product_pool, None
        
        print(f"Found {len(product_pool)} products to start the algorithm with.")
        print('starting genes multiplying:')
        print('==============================')
        
        # 3 Initialize population ands chromosomes
        population = []
        for _ in range(self.population_size):
            chromosome = self.create_chromosome(product_pool, num_recommendations)
            population.append(chromosome)
        
        # Track best fitness for metrics
        best_fitness_history = []
        
        # 4 Evolution loop 
        for generation in range(self.generations):
            # Evaluate fitness of all chromosomes in current population
            fitness_scores = []
            for chromosome in population:
                # Pass user_embedding only (no cache parameter)
                fitness = self.calculate_chromosome_fitness(chromosome, user_embedding)
                fitness_scores.append(fitness)
            
            # Track best fitness for monitoring convergence
            best_fitness = max(fitness_scores) if fitness_scores else 0
            best_fitness_history.append(best_fitness)
            avg_fitness = sum(fitness_scores) / len(fitness_scores) if fitness_scores else 0
            
            # Progress report every 5 generations
            if generation % 5 == 0:
                print(f"Gen {generation}: Best={best_fitness:.4f}")
            
            # Selection: choose parents based on fitness
            population = self.selection_tournament(population, fitness_scores)
            # Crossover: create offspring by combining parents (with random pairing)
            new_population = []

            # Randomly shuffle population before pairing to avoid neighbor bias
            shuffled_population = random.sample(population, len(population))

            for i in range(0, len(shuffled_population), 2):
                if i + 1 < len(shuffled_population):
                    child1, child2 = self.crossover(shuffled_population[i], shuffled_population[i + 1])
                    new_population.append(child1)
                    new_population.append(child2)
                else:
                    # Odd number handling: last individual with no partner
                    new_population.append(shuffled_population[i][:])

            population = new_population
            
            # Mutation: introduce random variations
            for i in range(len(population)):
                population[i] = self.mutate(population[i], product_pool)
            
            # Elitism: preserve the best chromosome from previous generation
            if fitness_scores:
                best_idx = fitness_scores.index(max(fitness_scores))
                population[random.randrange(len(population))] = population[best_idx][:]
        
        # Step 5: Calculate final fitness scores
        final_fitness = []
        for chromosome in population:
            fitness = self.calculate_chromosome_fitness(chromosome, user_embedding)
            final_fitness.append(fitness)
        
        # Step 6: Get suboptimal results
        recommendations = self.get_suboptimal_results(population, final_fitness, user_embedding, top_k=5)
        
        # Step 7: Score and sort final recommendations
        scored_recs = []
        for pid in recommendations[:num_recommendations * 2]:
            product_features = self.get_product_features(pid)
            if product_features:
                score = self.calculate_product_score(user_embedding, product_features)
                # Convert score to percentage for display (0-100 scale)
                score_percentage = score * 100
                scored_recs.append((pid, score_percentage, product_features))
        scored_recs.sort(key=lambda x: x[1], reverse=True)
        final_recs = scored_recs[:num_recommendations]
        
        # Calculate algorithm metrics
        best_fitness_final = max(final_fitness) if final_fitness else 0
        initial_best_fitness = best_fitness_history[0] if best_fitness_history else 0
        fitness_improvement = ((best_fitness_final - initial_best_fitness) / initial_best_fitness) if initial_best_fitness > 0 else 0
        
        algorithm_metrics = {
            "generations": self.generations,
            "best_fitness": round(best_fitness_final * 100, 2),  # Convert to percentage
            "fitness_improvement": round(fitness_improvement, 2)
        }
        
        # Prepare user profile for output
        user_profile = {
            "id": user_embedding.get('id',0),
            "age": user_embedding.get('age', 0),
            "country": user_embedding.get('country', 'Unknown'),
            "segment": user_embedding.get('customer_segment', 'Unknown'),
            "purchased_count": user_embedding.get('purchased_count', 0)
        }
        print('========================')
        print("the algorithm is done!")
        
        return final_recs, algorithm_metrics, user_profile
    
    def save_recommendations_to_json(self, user_id, recommendations, algorithm_metrics, user_profile, output_file='src/recommendations.json'):
        """
        Save recommendations to a JSON file with the specified structure
        
        Args:
            user_id: The user ID
            recommendations: List of tuples (product_id, score, product_features)
            algorithm_metrics: Dictionary with algorithm performance metrics
            user_profile: Dictionary with user information
            output_file: Output filename (default: recommendations_user_{user_id}_{timestamp}.json)
        """
        # Prepare the JSON structure
        output_data = {
            "user_id": user_id,
            "recommendations": [],
            "algorithm_metrics": algorithm_metrics,
            "user_profile": user_profile,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_recommendations": len(recommendations)
            }
        }
        
        # Add each recommendation
        for product_id, score, product_features in recommendations:
            rec_item = {
                "product_id": product_id,
                "category": product_features['category'],
                "price": round(product_features['price'], 2),
                "product_name": product_features['product_name'],
                "subcategory": product_features['subcategory'],
                "price_tier": product_features['price_tier'],
                "seasonality": product_features['seasonality'],
                "recommendation_score": round(score, 2),
                "avg_rating": round(product_features['avg_rating'], 2),
                "rating_count": product_features['rating_count']
            }
            output_data["recommendations"].append(rec_item)
        
        # Save to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        return output_file

    def clear_cache(self):
        """Clear the product features cache"""
        self._product_cache.clear()


def main():
    """
    Example usage of the ProductRecommenderGA class
    Demonstrates how to get recommendations and save to JSON for a specific user
    """
    # call class to initialize
    recommender = ProductRecommenderGA('projject_database.db')
    
    # User ID to get recommendations for (change to actual user ID from your database)
    user_id = 3
    num_recommendations=10
    # Get recommendations (returns list of tuples with product_id, score, features)
    recommendations, algorithm_metrics, user_profile = recommender.recommend_products(user_id, num_recommendations)
    
    if recommendations:
        # Save to JSON file
        output_file = recommender.save_recommendations_to_json(
            user_id=user_id,
            recommendations=recommendations,
            algorithm_metrics=algorithm_metrics,
            user_profile=user_profile,
            output_file='src/recommendations.json'
        )

        print("===========================")
        print(f'the best {num_recommendations} products for user with ID: {user_id} ')

        # output recommended products
        for i, (product_id, score, product) in enumerate(recommendations, 1):
            print(f"{i} name: {product['product_name']} , ID: {product_id} ")
            
        print("===========================")
        print(f"algorithm Best Fitness is: {algorithm_metrics['best_fitness']}")
        print('=============================')
        print('done!')


if __name__ == "__main__":
    main()