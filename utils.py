import logging
import os
import re
import hashlib

# Enhanced embedding function with multiple fallback methods
def generate_embedding(text):
    """Generate embedding with multiple fallback methods"""
    if not text or not text.strip():
        return [0.0] * 1536  # Return zero vector for empty text (OpenAI dimension)
    
    try:
        # Clean and normalize text
        cleaned_text = clean_text(text)
        if not cleaned_text:
            return [0.0] * 1536
        
        # Attempt 1: Try OpenAI embeddings with direct API
        try:
            import openai
            import os
            
            client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=cleaned_text
            )
            return response.data[0].embedding
        except Exception as e:
            logging.warning(f"OpenAI embedding failed: {e}")
            pass
        
        # Attempt 2: Try sentence-transformers if available
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            return model.encode(cleaned_text).tolist()
        except Exception:
            pass
        
        # Attempt 3: Try TF-IDF with sklearn if available
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            import numpy as np
            
            # Create a simple TF-IDF representation
            vectorizer = TfidfVectorizer(max_features=1536, stop_words='english')
            # Need to fit on a corpus, so we'll use the text itself with some common words
            corpus = [cleaned_text, "the quick brown fox jumps over lazy dog"]
            tfidf_matrix = vectorizer.fit_transform(corpus)
            embedding = tfidf_matrix[0].toarray()[0].tolist()
            
            # Pad or truncate to 1536 dimensions
            if len(embedding) < 1536:
                embedding.extend([0.0] * (1536 - len(embedding)))
            else:
                embedding = embedding[:1536]
            
            return embedding
        except Exception:
            pass
        
        # Final fallback: Enhanced hash-based embedding
        embedding = []
        for i in range(1536):
            # Create multiple hash values for better distribution
            hash_input = f"{cleaned_text}_{i}_embedding_salt"
            hash_value = hash(hash_input) % 10000
            normalized_value = (hash_value / 10000.0) * 2 - 1  # Scale to -1 to 1
            embedding.append(normalized_value)
        
        return embedding
        
    except Exception as e:
        logging.error(f"Failed to generate embedding: {str(e)}")
        return [0.0] * 1536

def clean_text(text):
    """Clean and normalize text for better embedding quality"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?;:-]', '', text)
    
    # Trim whitespace
    text = text.strip()
    
    return text

def split_text(text, chunk_size=300, overlap=50):
    """Split text into overlapping chunks for better context preservation"""
    if not text:
        return []
    
    # Clean the text first
    text = clean_text(text)
    words = text.split()
    
    if len(words) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        
        if chunk.strip():  # Only add non-empty chunks
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        if start >= len(words):
            break
    
    return chunks

def format_memory_context(memories, max_context_length=2000):
    """Format memories into a context string with length limit"""
    if not memories:
        return ""
    
    context_parts = []
    current_length = 0
    
    for memory in memories:
        memory_length = len(memory)
        if current_length + memory_length > max_context_length:
            break
        
        context_parts.append(f"• {memory}")
        current_length += memory_length
    
    return "\n".join(context_parts)

def extract_key_phrases(text, max_phrases=10):
    """Extract key phrases from text for better memory indexing"""
    if not text:
        return []
    
    # Simple keyword extraction - can be enhanced with NLP libraries
    words = text.lower().split()
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
    }
    
    # Filter meaningful words
    key_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Count frequency
    word_freq = {}
    for word in key_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top phrases
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:max_phrases]]

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    if not filename:
        return "unknown_document"
    
    # Remove path separators and special characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    return filename[:100]  # Limit length

def validate_environment():
    """Validate that all required environment variables are present"""
    required_vars = [
        'NEO4J_URI',
        'NEO4J_USER', 
        'NEO4J_PASSWORD',
        'OPENROUTER_API_KEY',
        'APP_USERNAME',
        'APP_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True

def log_performance(func):
    """Decorator to log function performance"""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logging.info(f"{func.__name__} executed in {end_time - start_time:.2f} seconds")
        return result
    
    return wrapper
