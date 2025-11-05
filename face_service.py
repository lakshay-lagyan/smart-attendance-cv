import os
import cv2
import numpy as np
import base64
import pickle
import faiss
from deepface import DeepFace
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

class FaceService:
    """Face recognition service using DeepFace and FAISS"""
    
    def __init__(self, index_path='faiss_index', threshold=0.6):
        self.index_path = index_path
        self.threshold = threshold
        self.index = None
        self.person_ids = []
        self.embedding_dim = 128
        
        os.makedirs(index_path, exist_ok=True)
        self.load_index()
    
    def load_index(self):
        """Load FAISS index from disk"""
        index_file = os.path.join(self.index_path, 'faiss.index')
        ids_file = os.path.join(self.index_path, 'person_ids.pkl')
        
        if os.path.exists(index_file) and os.path.exists(ids_file):
            try:
                self.index = faiss.read_index(index_file)
                with open(ids_file, 'rb') as f:
                    self.person_ids = pickle.load(f)
                logger.info(f"Loaded FAISS index with {len(self.person_ids)} persons")
            except Exception as e:
                logger.error(f"Error loading FAISS index: {e}")
                self.initialize_index()
        else:
            self.initialize_index()
    
    def initialize_index(self):
        """Initialize new FAISS index"""
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.person_ids = []
        logger.info("Initialized new FAISS index")
    
    def save_index(self):
        """Save FAISS index to disk"""
        try:
            index_file = os.path.join(self.index_path, 'faiss.index')
            ids_file = os.path.join(self.index_path, 'person_ids.pkl')
            
            faiss.write_index(self.index, index_file)
            with open(ids_file, 'wb') as f:
                pickle.dump(self.person_ids, f)
            logger.info("FAISS index saved")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")
    
    def base64_to_image(self, base64_string):
        """Convert base64 string to image"""
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        img_data = base64.b64decode(base64_string)
        img = Image.open(io.BytesIO(img_data))
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    def extract_embedding(self, image):
        """Extract face embedding from image"""
        try:
            result = DeepFace.represent(
                img_path=image,
                model_name="Facenet",
                enforce_detection=True,
                detector_backend="opencv"
            )
            
            if result and len(result) > 0:
                embedding = np.array(result[0]["embedding"], dtype=np.float32)
                return embedding
            return None
        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            return None
    
    def add_person(self, person_id, embeddings):
        """Add person embeddings to FAISS index"""
        try:
            if not isinstance(embeddings, list):
                embeddings = [embeddings]
            
            for embedding in embeddings:
                embedding = np.array(embedding, dtype=np.float32).reshape(1, -1)
                self.index.add(embedding)
                self.person_ids.append(person_id)
            
            self.save_index()
            logger.info(f"Added person {person_id} with {len(embeddings)} embeddings")
            return True
        except Exception as e:
            logger.error(f"Error adding person: {e}")
            return False
    
    def recognize_face(self, embedding):
        """Recognize face from embedding"""
        try:
            if self.index.ntotal == 0:
                return None, 0.0
            
            embedding = np.array(embedding, dtype=np.float32).reshape(1, -1)
            distances, indices = self.index.search(embedding, k=1)
            
            distance = distances[0][0]
            similarity = 1.0 / (1.0 + distance)
            
            if similarity >= self.threshold:
                person_id = self.person_ids[indices[0][0]]
                return person_id, similarity
            
            return None, similarity
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return None, 0.0
    
    def rebuild_index_from_db(self, db_persons):
        """Rebuild FAISS index from database persons"""
        try:
            self.initialize_index()
            
            for person in db_persons:
                if person.embedding and person.status == 'active':
                    embedding = pickle.loads(person.embedding)
                    self.add_person(person.id, embedding)
            
            logger.info(f"Rebuilt FAISS index with {len(db_persons)} persons")
            return True
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            return False
    
    def get_stats(self):
        """Get index statistics"""
        return {
            'total_persons': len(set(self.person_ids)),
            'total_embeddings': self.index.ntotal,
            'embedding_dim': self.embedding_dim
        }

face_service = FaceService()
