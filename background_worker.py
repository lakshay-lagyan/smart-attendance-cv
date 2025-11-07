"""
Background Worker for CPU-intensive tasks
Handles face embedding generation asynchronously
"""
import threading
import queue
import logging
import time
from typing import Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class Task:
    """Background task wrapper"""
    
    def __init__(self, task_id: str, func: Callable, args: tuple = (), kwargs: dict = None):
        self.task_id = task_id
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.status = 'pending'
        self.result = None
        self.error = None
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
    
    def execute(self):
        """Execute the task"""
        try:
            self.status = 'running'
            self.started_at = datetime.utcnow()
            logger.info(f"Executing task {self.task_id}")
            
            self.result = self.func(*self.args, **self.kwargs)
            self.status = 'completed'
            self.completed_at = datetime.utcnow()
            
            logger.info(f"Task {self.task_id} completed in {(self.completed_at - self.started_at).total_seconds():.2f}s")
            
        except Exception as e:
            self.status = 'failed'
            self.error = str(e)
            self.completed_at = datetime.utcnow()
            logger.error(f"Task {self.task_id} failed: {e}")
    
    def to_dict(self):
        """Convert task to dictionary"""
        return {
            'task_id': self.task_id,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': (self.completed_at - self.started_at).total_seconds() if self.completed_at and self.started_at else None
        }


class BackgroundWorker:
    """Background task worker with thread pool"""
    
    def __init__(self, num_workers: int = 2):
        self.num_workers = num_workers
        self.task_queue = queue.Queue()
        self.tasks = {}  # task_id -> Task
        self.workers = []
        self.is_running = False
        self.lock = threading.Lock()
        
        logger.info(f"BackgroundWorker initialized with {num_workers} workers")
    
    def start(self):
        """Start worker threads"""
        if self.is_running:
            logger.warning("Worker already running")
            return
        
        self.is_running = True
        
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
            logger.info(f"Worker thread {i} started")
    
    def _worker_loop(self, worker_id: int):
        """Worker thread loop"""
        logger.info(f"Worker {worker_id} starting loop")
        
        while self.is_running:
            try:
                # Get task from queue (timeout to check is_running periodically)
                try:
                    task = self.task_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                logger.info(f"Worker {worker_id} picked up task {task.task_id}")
                
                # Execute task
                task.execute()
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
    
    def submit_task(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        """
        Submit a task for background execution
        Returns: task_id
        """
        with self.lock:
            if task_id in self.tasks:
                logger.warning(f"Task {task_id} already exists")
                return task_id
            
            task = Task(task_id, func, args, kwargs)
            self.tasks[task_id] = task
            self.task_queue.put(task)
            
            logger.info(f"Task {task_id} queued (queue size: {self.task_queue.qsize()})")
            return task_id
    
    def get_task_status(self, task_id: str) -> dict:
        """Get status of a task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return {'error': 'Task not found'}
            return task.to_dict()
    
    def get_task_result(self, task_id: str) -> Any:
        """Get result of completed task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            if task.status == 'completed':
                return task.result
            return None
    
    def wait_for_task(self, task_id: str, timeout: float = 30) -> dict:
        """Wait for task to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)
            if status.get('status') in ['completed', 'failed']:
                return status
            time.sleep(0.1)
        
        return {'error': 'Timeout waiting for task'}
    
    def get_queue_size(self) -> int:
        """Get number of pending tasks"""
        return self.task_queue.qsize()
    
    def get_all_tasks(self) -> list:
        """Get all tasks"""
        with self.lock:
            return [task.to_dict() for task in self.tasks.values()]
    
    def cleanup_old_tasks(self, max_age_seconds: int = 3600):
        """Remove old completed/failed tasks"""
        with self.lock:
            now = datetime.utcnow()
            to_remove = []
            
            for task_id, task in self.tasks.items():
                if task.status in ['completed', 'failed']:
                    if task.completed_at:
                        age = (now - task.completed_at).total_seconds()
                        if age > max_age_seconds:
                            to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old tasks")
    
    def stop(self):
        """Stop all workers"""
        logger.info("Stopping workers...")
        self.is_running = False
        
        for worker in self.workers:
            worker.join(timeout=5)
        
        logger.info("All workers stopped")


# Global worker instance
background_worker = BackgroundWorker(num_workers=2)


# Face embedding task wrapper
def generate_face_embedding_task(image_path: str, face_service):
    """
    Task function for generating face embeddings
    This runs in background to avoid blocking the main thread
    """
    try:
        from PIL import Image
        import numpy as np
        
        # Load image
        img = Image.open(image_path)
        img_array = np.array(img)
        
        # Generate embedding
        embedding = face_service.get_face_embedding(img_array)
        
        if embedding is not None:
            return {
                'success': True,
                'embedding': embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                'dimension': len(embedding)
            }
        else:
            return {
                'success': False,
                'error': 'No face detected'
            }
    
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return {
            'success': False,
            'error': str(e)
        }
