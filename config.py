# Configuration settings for NeuroLM Advanced Memory System

# Default retrieval weights for memory scoring
DEFAULT_RETRIEVAL_WEIGHTS = {
    'vector': 0.4,        # Semantic similarity weight
    'temporal': 0.25,     # Recency/temporal relevance weight
    'access': 0.2,        # Access frequency weight
    'association': 0.15   # Associative strength weight
}

# Memory consolidation settings
CONSOLIDATION_CONFIG = {
    'strengthen_threshold': 5,      # Access count to consider memory important
    'prune_months': 3,             # Months before considering memory for pruning
    'prune_access_threshold': 2,   # Min accesses to prevent pruning
    'prune_confidence_threshold': 0.3,  # Min confidence to prevent pruning
    'association_threshold': 0.7,   # Similarity threshold for auto-linking
    'weak_association_threshold': 0.3  # Remove associations below this
}

# Association engine settings
ASSOCIATION_CONFIG = {
    'decay_rate': 0.005,           # Daily decay rate for associations
    'max_hops': 3,                 # Maximum hops for multi-hop discovery
    'context_threshold': 0.6,      # Threshold for contextual clustering
    'auto_association_strength': 0.85  # Default strength for auto-created associations
}

# Performance settings
PERFORMANCE_CONFIG = {
    'batch_size': 100,             # Batch size for processing operations
    'cache_size': 500,             # LRU cache size for memory objects
    'vector_candidates': 100,      # Number of vector candidates to retrieve
    'max_memories_per_query': 10   # Maximum memories returned per query
}

# Background job scheduling
SCHEDULE_CONFIG = {
    'consolidation_time': "02:00",  # Daily consolidation time (24h format)
    'association_interval': 60,     # Association maintenance interval (minutes)
    'schedule_check_interval': 60   # How often to check scheduled jobs (seconds)
}

# Memory importance scoring weights
IMPORTANCE_WEIGHTS = {
    'confidence': 0.4,
    'access_frequency': 0.3,
    'association_count': 0.3
}