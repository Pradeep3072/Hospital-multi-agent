import json
import time
import threading
from typing import List, Dict, Any, Optional
from collections import defaultdict, deque

from backend.app.config import settings
from backend.app.database.session import SessionLocal
from backend.app.database.models import Conversation, MemoryRecord


class SessionMemoryManager:
    """
    Hybrid Short-Term State & Session Memory Manager.
    Uses Redis when connected, falling back seamlessly to an in-memory
    thread-safe LRU store + relational database persistence.
    """

    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = 3600):
        self.redis_url = redis_url or settings.REDIS_URL
        self.ttl_seconds = ttl_seconds
        self._redis_client = None
        self._redis_available = False
        self._in_memory_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self._in_memory_timestamps: Dict[str, float] = {}
        self._local_locks: Dict[str, threading.Lock] = {}
        self._lock_meta = threading.Lock()

        self._init_redis()

    def _init_redis(self):
        """Attempts connection to Redis with short timeout for instant degradation"""
        try:
            import redis
            client = redis.Redis.from_url(
                self.redis_url,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
                decode_responses=True
            )
            client.ping()
            self._redis_client = client
            self._redis_available = True
            print(f"SessionMemoryManager: Connected to Redis at {self.redis_url}")
        except Exception as e:
            self._redis_client = None
            self._redis_available = False
            print(f"SessionMemoryManager: Redis unavailable ({e}). Using in-memory fallback store.")

    @property
    def is_redis_active(self) -> bool:
        if not self._redis_available or not self._redis_client:
            return False
        try:
            self._redis_client.ping()
            return True
        except Exception:
            self._redis_available = False
            return False

    def get_status(self) -> Dict[str, Any]:
        """Returns the current operational status of the memory backend"""
        active = self.is_redis_active
        return {
            "engine": "redis" if active else "in_memory_fallback",
            "redis_connected": active,
            "ttl_seconds": self.ttl_seconds,
            "in_memory_active_sessions": len(self._in_memory_cache)
        }

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        patient_id: Optional[int] = None
    ):
        """
        Stores a dialogue turn into short-term cache and persists to relational DB.
        """
        turn_data = {
            "role": role,
            "agent_name": agent_name,
            "content": content,
            "timestamp": time.time()
        }

        # 1. Update Short-Term Fast Store
        if self.is_redis_active:
            try:
                key = f"session:{session_id}:messages"
                self._redis_client.rpush(key, json.dumps(turn_data))
                self._redis_client.expire(key, self.ttl_seconds)
            except Exception as e:
                print(f"Redis write error ({e}), writing to in-memory fallback.")
                self._write_in_memory(session_id, turn_data)
        else:
            self._write_in_memory(session_id, turn_data)

        # 2. Persist to Relational DB for Audit & Long-Term History
        self._persist_to_db(session_id, role, content, agent_name, patient_id)

    def _write_in_memory(self, session_id: str, turn_data: Dict[str, Any]):
        with self._lock_meta:
            self._in_memory_cache[session_id].append(turn_data)
            self._in_memory_timestamps[session_id] = time.time()

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves the last `limit` conversation turns for the active session.
        """
        # Try Redis first
        if self.is_redis_active:
            try:
                key = f"session:{session_id}:messages"
                raw_messages = self._redis_client.lrange(key, -limit, -1)
                if raw_messages:
                    return [json.loads(m) for m in raw_messages]
            except Exception as e:
                print(f"Redis read error ({e}), reading from in-memory fallback.")

        # Fallback to In-Memory
        with self._lock_meta:
            if session_id in self._in_memory_cache:
                items = list(self._in_memory_cache[session_id])
                return items[-limit:]

        # If cache missed, load recent from Database
        return self._load_from_db(session_id, limit)

    def clear_session(self, session_id: str) -> bool:
        """
        Flushes active memory cache for a given session.
        """
        cleared = False
        if self.is_redis_active:
            try:
                key = f"session:{session_id}:messages"
                self._redis_client.delete(key)
                cleared = True
            except Exception as e:
                print(f"Redis delete error: {e}")

        with self._lock_meta:
            if session_id in self._in_memory_cache:
                del self._in_memory_cache[session_id]
            if session_id in self._in_memory_timestamps:
                del self._in_memory_timestamps[session_id]
            cleared = True

        return cleared

    def acquire_lock(self, lock_name: str, timeout: float = 5.0) -> bool:
        """
        Acquires a distributed or thread lock for coordinating concurrent bookings.
        """
        if self.is_redis_active:
            try:
                # Redis atomic SET NX EX
                acquired = self._redis_client.set(
                    f"lock:{lock_name}",
                    "1",
                    nx=True,
                    ex=int(timeout)
                )
                return bool(acquired)
            except Exception:
                pass

        # In-memory local lock fallback
        with self._lock_meta:
            if lock_name not in self._local_locks:
                self._local_locks[lock_name] = threading.Lock()
            return self._local_locks[lock_name].acquire(timeout=timeout)

    def release_lock(self, lock_name: str):
        """
        Releases the distributed or thread lock.
        """
        if self.is_redis_active:
            try:
                self._redis_client.delete(f"lock:{lock_name}")
                return
            except Exception:
                pass

        with self._lock_meta:
            if lock_name in self._local_locks:
                try:
                    self._local_locks[lock_name].release()
                except RuntimeError:
                    pass

    def _persist_to_db(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_name: Optional[str],
        patient_id: Optional[int]
    ):
        db = SessionLocal()
        try:
            conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
            if not conv:
                conv = Conversation(session_id=session_id, patient_id=patient_id or 1)
                db.add(conv)
                db.commit()
                db.refresh(conv)

            rec = MemoryRecord(
                conversation_id=conv.id,
                role=role,
                agent_name=agent_name,
                content=content
            )
            db.add(rec)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"MemoryManager DB persist error: {e}")
        finally:
            db.close()

    def _load_from_db(self, session_id: str, limit: int) -> List[Dict[str, Any]]:
        db = SessionLocal()
        turns = []
        try:
            conv = db.query(Conversation).filter(Conversation.session_id == session_id).first()
            if conv:
                recs = (
                    db.query(MemoryRecord)
                    .filter(MemoryRecord.conversation_id == conv.id)
                    .order_by(MemoryRecord.id.desc())
                    .limit(limit)
                    .all()
                )
                for r in reversed(recs):
                    turns.append({
                        "role": r.role,
                        "agent_name": r.agent_name,
                        "content": r.content,
                        "timestamp": r.timestamp.timestamp() if r.timestamp else time.time()
                    })
        except Exception as e:
            print(f"MemoryManager DB read error: {e}")
        finally:
            db.close()
        return turns


# Global singleton memory manager
memory_manager = SessionMemoryManager()
