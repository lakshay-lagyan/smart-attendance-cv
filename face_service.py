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
    """Enhanced face recognition service with strong anti-false-positive measures"""
    
    def __init__(self, index_path='faiss_index', threshold=0.75):
        self.index_path = index_path
        # Stricter threshold (0.75 instead of 0.6) to reduce false positives
        self.threshold = threshold
        # Very strict threshold for critical operations
        self.strict_threshold = 0.85
        self.index = None
        self.person_ids = []
        # Using Facenet512 for 512-dim embeddings (more accurate than 128-dim)
        self.embedding_dim = 512
        self.model_name = "Facenet512"
        # Use more accurate detector
        self.detector_backend = "retinaface"
        
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
        """Initialize new FAISS index with Inner Product for normalized vectors"""
        # Use Inner Product index for normalized embeddings (cosine similarity)
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.person_ids = []
        logger.info("Initialized new FAISS index with Inner Product")
    
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
    
    def check_face_quality(self, image):
        """Check face image quality to prevent false positives"""
        try:
            # Convert to grayscale for quality checks
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Check image size
            height, width = gray.shape[:2]
            if height < 80 or width < 80:
                return False, "Face too small (min 80x80)"
            
            # Check brightness
            brightness = np.mean(gray)
            if brightness < 40:
                return False, "Image too dark"
            if brightness > 220:
                return False, "Image overexposed"
            
            # Check sharpness using Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < 100:
                return False, "Image too blurry"
            
            # Check contrast
            contrast = gray.std()
            if contrast < 20:
                return False, "Low contrast"
            
            return True, "Quality OK"
        except Exception as e:
            logger.error(f"Quality check error: {e}")
            return False, str(e)
    
    def extract_embedding(self, image, check_quality=True):
        """Extract face embedding from image with quality checks"""
        try:
            # Perform quality check
            if check_quality:
                quality_ok, quality_msg = self.check_face_quality(image)
                if not quality_ok:
                    logger.warning(f"Quality check failed: {quality_msg}")
                    return None
            
            # Try primary detector (retinaface)
            try:
                result = DeepFace.represent(
                    img_path=image,
                    model_name=self.model_name,
                    enforce_detection=True,
                    detector_backend=self.detector_backend,
                    align=True  # Enable face alignment for better accuracy
                )
            except:
                # Fallback to opencv detector if retinaface fails
                logger.info("Falling back to opencv detector")
                result = DeepFace.represent(
                    img_path=image,
                    model_name=self.model_name,
                    enforce_detection=True,
                    detector_backend="opencv",
                    align=True
                )
            
            if result and len(result) > 0:
                embedding = np.array(result[0]["embedding"], dtype=np.float32)
                # Normalize embedding for better comparison
                embedding = embedding / np.linalg.norm(embedding)
                return embedding
            return None
        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            return None
    
    def add_person(self, person_id, embeddings):
        """Add person embeddings to FAISS index with normalization"""
        try:
            if not isinstance(embeddings, list):
                embeddings = [embeddings]
            
            for embedding in embeddings:
                embedding = np.array(embedding, dtype=np.float32)
                # Normalize embedding for cosine similarity
                embedding = embedding / np.linalg.norm(embedding)
                embedding = embedding.reshape(1, -1)
                self.index.add(embedding)
                self.person_ids.append(person_id)
            
            self.save_index()
            logger.info(f"Added person {person_id} with {len(embeddings)} normalized embeddings")
            return True
        except Exception as e:
            logger.error(f"Error adding person: {e}")
            return False
    
    def recognize_face(self, embedding, strict_mode=False):
        """Recognize face from embedding with anti-false-positive measures"""
        try:
            if self.index.ntotal == 0:
                return None, 0.0
            
            # Normalize embedding
            embedding = np.array(embedding, dtype=np.float32)
            embedding = embedding / np.linalg.norm(embedding)
            embedding = embedding.reshape(1, -1)
            
            # Search for top 3 matches to check for ambiguity
            k = min(3, self.index.ntotal)
            scores, indices = self.index.search(embedding, k=k)
            
            # IndexFlatIP returns inner product scores (higher is better)
            # For normalized vectors, inner product = cosine similarity
            similarities = [max(0.0, min(1.0, float(score))) for score in scores[0]]
            
            best_similarity = similarities[0]
            threshold = self.strict_threshold if strict_mode else self.threshold
            
            # Check if best match is good enough
            if best_similarity < threshold:
                logger.info(f"Match rejected: similarity {best_similarity:.3f} below threshold {threshold}")
                return None, best_similarity
            
            # Anti-ambiguity check: if two faces are too similar, reject
            if len(similarities) > 1:
                second_best = similarities[1]
                # If second best is within 0.1 of best, it's ambiguous
                if second_best > (best_similarity - 0.1):
                    logger.warning(f"Ambiguous match: best={best_similarity:.3f}, second={second_best:.3f}")
                    return None, best_similarity
            
            person_id = self.person_ids[indices[0][0]]
            logger.info(f"Match found: person_id={person_id}, similarity={best_similarity:.3f}")
            return person_id, best_similarity
            
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
