#!/usr/bin/env python3
"""
Embedding Cleanup Script
Fixes invalid embeddings that cause vector similarity errors
"""

import os
from dotenv import load_dotenv
from neural_memory import NeuralMemorySystem

def main():
    """Run embedding cleanup"""
    load_dotenv()
    
    print("Starting embedding cleanup...")
    print("This will fix invalid embeddings causing vector similarity errors.")
    
    try:
        # Initialize memory system
        memory = NeuralMemorySystem()
        
        # Run cleanup
        memory.cleanup_invalid_embeddings()
        
        # Close connection
        memory.close()
        
        print("\nEmbedding cleanup completed successfully!")
        print("Vector similarity errors should now be resolved.")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    main()