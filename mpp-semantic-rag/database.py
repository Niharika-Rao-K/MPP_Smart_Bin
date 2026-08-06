import chromadb
from chromadb.utils import embedding_functions

# 1. Initialize persistent storage on your hard drive
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# 2. Load a local embedding model (runs completely offline on your CPU)
# This converts text strings into mathematical vectors for mathematical rule evaluations
embedding_func = embedding_functions.DefaultEmbeddingFunction()

# 3. Create or fetch your semantic profile collection
collection = chroma_client.get_or_create_collection(
    name="recycling_profiles", 
    embedding_function=embedding_func
)

def seed_reference_data():
    """
    Populates the vector database with factory truth profiles tailored explicitly
    to our 3 compartments: Plastic Wrappers, Metal Waste, and E-Waste.
    """
    # 1. Expand the list to cover diverse items your camera might see
    ideal_profiles = [
        # Compartment 1: Plastic Wrappers
        "Cadbury Milk Chocolate Wrapper",
        "Lay's Potato Chip Packet",
        "Kurkure Masala Munch Wrapper",
        "Plastic Biscuit Packaging",
        
        # Compartment 2: Metal Waste
        "Coca-Cola Aluminum Can",
        "Pepsi Soda Can",
        "Steel Fruit Juice Tin",
        "Crushed Metal Beverage Can",
        
        # Compartment 3: E-Waste
        "Dead Smartphone Lithium Battery",
        "Broken Computer Mouse",
        "Discarded Green PCB Circuit Board",
        "Old USB Charging Cable"
    ]
    
    # 12 unique IDs for our 12 reference items
    profile_ids = [f"rec_{i:03d}" for i in range(1, 13)]
    
    # 2. Map them EXACTLY to your 3 hardware routing targets
    metadata_payloads = [
        # Plastic Wrappers
        {"material": "Plastic Wrapper", "ideal_weight_g": 5.0, "error_margin_g": 1.5},
        {"material": "Plastic Wrapper", "ideal_weight_g": 6.2, "error_margin_g": 1.5},
        {"material": "Plastic Wrapper", "ideal_weight_g": 5.8, "error_margin_g": 1.5},
        {"material": "Plastic Wrapper", "ideal_weight_g": 4.5, "error_margin_g": 1.0},
        
        # Metal Waste
        {"material": "Metal Waste", "ideal_weight_g": 13.0, "error_margin_g": 2.0},
        {"material": "Metal Waste", "ideal_weight_g": 13.5, "error_margin_g": 2.0},
        {"material": "Metal Waste", "ideal_weight_g": 25.0, "error_margin_g": 4.0},
        {"material": "Metal Waste", "ideal_weight_g": 12.8, "error_margin_g": 2.5},
        
        # E-Waste
        {"material": "E-Waste", "ideal_weight_g": 45.0, "error_margin_g": 5.0},
        {"material": "E-Waste", "ideal_weight_g": 80.0, "error_margin_g": 10.0},
        {"material": "E-Waste", "ideal_weight_g": 35.0, "error_margin_g": 7.0},
        {"material": "E-Waste", "ideal_weight_g": 20.0, "error_margin_g": 4.0}
    ]
    
    collection.upsert(
        documents=ideal_profiles, 
        ids=profile_ids, 
        metadatas=metadata_payloads
    )
    print("Database successfully re-seeded with explicit Wrapper, Metal, and E-Waste profiles!")

def evaluate_similarity(unrecognized_label: str):
    """
    Takes an unrecognized item string, queries ChromaDB, 
    and calculates a normalized similarity score percentage [source: 1].
    """
    # Query database for the single closest vector match
    results = collection.query(
        query_texts=[unrecognized_label],
        n_results=1
    )
    
    # Break safe if the database returns empty arrays
    if not results['documents'] or len(results['documents'][0]) == 0:
        return None
        
    # Extract structural attributes from the raw query output
    matched_text = results['documents'][0][0]
    metadata = results['metadatas'][0][0]
    distance = results['distances'][0][0]
    
    # ChromaDB uses L2 squared distance. Convert it to a readable similarity metric.
    # lower distance value = higher mathematical match percentage [source: 1].
    similarity_score = max(0, min(100, int((1.0 - (distance / 2.0)) * 100)))
    
    return {
        "input_queried": unrecognized_label,
        "closest_matched_profile": matched_text,
        "similarity_score_pct": similarity_score,
        "material": metadata["material"],
        "ideal_weight_g": metadata["ideal_weight_g"],
        "error_margin_g": metadata["error_margin_g"]
    }

def evaluate_weight_anomaly(ideal_weight: float, real_weight: float, error_margin: float):
    """
    The mathematical rule engine that evaluates variations.
    Checks if the actual weight falls within the allowed tolerance threshold.
    """
    lower_bound = ideal_weight - error_margin
    upper_bound = ideal_weight + error_margin
    
    # Check if the dropped item is within acceptable margins
    if lower_bound <= real_weight <= upper_bound:
        return {
            "status": "Valid",
            "action": "Proceed to Sort",
            "message": "Item weight matches reference profile specifications."
        }
    elif real_weight > upper_bound:
        return {
            "status": "Contaminated",
            "action": "Reject",
            "message": f"Anomalies Detected: Weight ({real_weight}g) exceeds maximum threshold ({upper_bound}g). Please empty liquids[cite: 29, 32]."
        }
    else:
        return {
            "status": "Underweight",
            "action": "Reject",
            "message": f"Anomalies Detected: Item too light ({real_weight}g). Expected at least {lower_bound}g."
        }

# Execute database seeding if run directly
if __name__ == "__main__":
    seed_reference_data()