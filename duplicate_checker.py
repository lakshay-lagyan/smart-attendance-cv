"""
Duplicate Face Detection using FAISS
Fast similarity search for duplicate checking before enrollment
"""
import numpy as np
import faiss
import pickle
import os
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class DuplicateChecker:
    """Fast duplicate detection using FAISS ANN search"""
    
    def __init__(self, index_path='faiss_index', dimension=512):
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.person_ids = []  # Maps index positions to person IDs
        self.metadata = {}  # person_id -> {name, email, etc.}
        
        os.makedirs(index_path, exist_ok=True)
        self.index_file = os.path.join(index_path, 'face_index.faiss')
        self.metadata_file = os.path.join(index_path, 'metadata.pkl')
        
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing index or create new one"""
        try:
            if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
                # Load existing index
                self.index = faiss.read_index(self.index_file)
                with open(self.metadata_file, 'rb') as f:
                    data = pickle.load(f)
                    self.person_ids = data.get('person_ids', [])
                    self.metadata = data.get('metadata', {})
                logger.info(f"Loaded FAISS index with {len(self.person_ids)} entries")
            else:
                # Create new index
                self._create_new_index()
        except Exception as e:
            logger.error(f"Error loading index: {e}. Creating new index.")
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index"""
        # Use L2 distance (Euclidean) for face embeddings
        self.index = faiss.IndexFlatL2(self.dimension)
        self.person_ids = []
        self.metadata = {}
        logger.info("Created new FAISS index")
    
    def add_embedding(self, person_id: int, embedding: np.ndarray, metadata: dict = None):
        """
        Add a face embedding to the index
        Args:
            person_id: Unique person identifier
            embedding: Face embedding vector (512-dim)
            metadata: Additional info (name, email, etc.)
        """
        try:
            # Ensure embedding is the right shape
            if embedding.ndim == 1:
                embedding = embedding.reshape(1, -1)
            
            if embedding.shape[1] != self.dimension:
                logger.error(f"Embedding dimension mismatch: expected {self.dimension}, got {embedding.shape[1]}")
                return False
            
            # Add to index
            self.index.add(embedding.astype('float32'))
            self.person_ids.append(person_id)
            
            # Store metadata
            if metadata:
                self.metadata[person_id] = metadata
            
            # Save index
            self._save_index()
            
            logger.info(f"Added embedding for person {person_id}. Total entries: {len(self.person_ids)}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding embedding: {e}")
            return False
    
    def find_duplicates(self, embedding: np.ndarray, k: int = 5, threshold: float = 0.6) -> List[dict]:
        """
        Find potential duplicates using ANN search
        Args:
            embedding: Query face embedding
            k: Number of top matches to return
            threshold: Similarity threshold (0-1, higher = more similar)
        Returns:
            List of dicts with person_id, distance, similarity, metadata
        """
        try:
            if len(self.person_ids) == 0:
                return []
            
            # Ensure embedding is the right shape
            if embedding.ndim == 1:
                embedding = embedding.reshape(1, -1)
            
            if embedding.shape[1] != self.dimension:
                logger.error(f"Embedding dimension mismatch")
                return []
            
            # Search for top k nearest neighbors
            k = min(k, len(self.person_ids))  # Don't search for more than available
            distances, indices = self.index.search(embedding.astype('float32'), k)
            
            # Convert distances to similarities (1 / (1 + distance))
            # Lower distance = higher similarity
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.person_ids):
                    person_id = self.person_ids[idx]
                    # Normalize distance to similarity score (0-1)
                    # Using inverse distance: similarity = 1 / (1 + distance)
                    similarity = 1.0 / (1.0 + float(dist))
                    
                    if similarity >= threshold:
                        result = {
                            'person_id': person_id,
                            'distance': float(dist),
                            'similarity': round(similarity, 4),
                            'confidence': round(similarity * 100, 2),
                            'metadata': self.metadata.get(person_id, {}),
                            'is_high_match': similarity >= 0.85
                        }
                        results.append(result)
            
            # Sort by similarity (highest first)
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return results
        
        except Exception as e:
            logger.error(f"Error finding duplicates: {e}")
            return []
    
    def remove_person(self, person_id: int):
        """
        Remove a person from the index
        Note: FAISS doesn't support deletion, so we rebuild the index
        """
        try:
            if person_id not in self.person_ids:
                return False
            
            # Get all embeddings except the one to remove
            all_embeddings = []
            new_person_ids = []
            new_metadata = {}
            
            # This requires storing embeddings separately or rebuilding from DB
            # For now, we'll just mark in metadata
            if person_id in self.metadata:
                self.metadata[person_id]['deleted'] = True
            
            logger.info(f"Marked person {person_id} as deleted")
            self._save_index()
            return True
        
        except Exception as e:
            logger.error(f"Error removing person: {e}")
            return False
    
    def rebuild_index(self, embeddings_data: List[Tuple[int, np.ndarray, dict]]):
        """
        Rebuild entire index from scratch
        Args:
            embeddings_data: List of (person_id, embedding, metadata) tuples
        """
        try:
            self._create_new_index()
            
            for person_id, embedding, metadata in embeddings_data:
                if embedding.ndim == 1:
                    embedding = embedding.reshape(1, -1)
                
                self.index.add(embedding.astype('float32'))
                self.person_ids.append(person_id)
                if metadata:
                    self.metadata[person_id] = metadata
            
            self._save_index()
            logger.info(f"Rebuilt index with {len(self.person_ids)} entries")
            return True
        
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            return False
    
    def _save_index(self):
        """Save index and metadata to disk"""
        try:
            faiss.write_index(self.index, self.index_file)
            
            with open(self.metadata_file, 'wb') as f:
                pickle.dump({
                    'person_ids': self.person_ids,
                    'metadata': self.metadata
                }, f)
            
            logger.debug("Index saved successfully")
        
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def get_stats(self) -> dict:
        """Get index statistics"""
        return {
            'total_entries': len(self.person_ids),
            'dimension': self.dimension,
            'index_type': 'IndexFlatL2',
            'metadata_count': len(self.metadata)
        }


# Global duplicate checker instance
duplicate_checker = DuplicateChecker()
