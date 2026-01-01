"""
SQLite-based Audio Cache with LRU eviction logic.
Replaces file-based .cache/ directory with a database.
"""

import sqlite3
import time
from pathlib import Path
from typing import Optional, Tuple

class AudioCache:
    """
    SQLite-based audio cache with LRU (Least Recently Used) eviction.
    Stores WAV audio data as BLOB with automatic size management.
    """
    
    def __init__(self, db_path: Path, max_size_mb: float = 200.0):
        """
        Args:
            db_path: Path to SQLite database file
            max_size_mb: Maximum cache size in MB (default: 200MB)
        """
        self.db_path = db_path
        self.max_size_mb = max_size_mb
        self._init_db()
    
    def _init_db(self):
        """Create database schema if not exists."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_cache (
                cache_key TEXT PRIMARY KEY,
                audio_data BLOB NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at REAL NOT NULL,
                accessed_at REAL NOT NULL
            )
        """)
        
        # Index for LRU cleanup (sort by accessed_at)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_accessed_at 
            ON audio_cache(accessed_at)
        """)
        
        conn.commit()
        conn.close()
    
    def get(self, cache_key: str) -> Optional[bytes]:
        """
        Retrieve audio data from cache.
        Updates access time (LRU tracking).
        
        Returns:
            bytes: WAV audio data, or None if not found
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get audio data
        cursor.execute(
            "SELECT audio_data FROM audio_cache WHERE cache_key = ?",
            (cache_key,)
        )
        row = cursor.fetchone()
        
        if row:
            # Update access time (LRU)
            cursor.execute(
                "UPDATE audio_cache SET accessed_at = ? WHERE cache_key = ?",
                (time.time(), cache_key)
            )
            conn.commit()
            conn.close()
            return row[0]
        
        conn.close()
        return None
    
    def put(self, cache_key: str, audio_data: bytes):
        """
        Store audio data in cache.
        Triggers LRU cleanup if size limit exceeded.
        
        Args:
            cache_key: MD5 hash key
            audio_data: WAV file bytes
        """
        size_bytes = len(audio_data)
        current_time = time.time()
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Insert or replace
        cursor.execute("""
            INSERT OR REPLACE INTO audio_cache 
            (cache_key, audio_data, size_bytes, created_at, accessed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (cache_key, audio_data, size_bytes, current_time, current_time))
        
        conn.commit()
        conn.close()
        
        # Check if cleanup needed
        self._cleanup_if_needed()
    
    def _cleanup_if_needed(self):
        """
        Evict oldest entries (LRU) if cache exceeds max size.
        """
        total_size_mb = self.get_size_mb()
        
        if total_size_mb <= self.max_size_mb:
            return  # Within limit
        
        print(f"\n[CACHE CLEANUP] Size {total_size_mb:.2f}MB exceeds {self.max_size_mb}MB limit")
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get all entries sorted by access time (oldest first)
        cursor.execute("""
            SELECT cache_key, size_bytes, accessed_at 
            FROM audio_cache 
            ORDER BY accessed_at ASC
        """)
        
        entries = cursor.fetchall()
        current_size_bytes = sum(e[1] for e in entries)
        target_size_bytes = int(self.max_size_mb * 1024 * 1024)
        
        # Delete oldest until under limit
        deleted_count = 0
        for cache_key, size_bytes, accessed_at in entries:
            if current_size_bytes <= target_size_bytes:
                break
            
            cursor.execute("DELETE FROM audio_cache WHERE cache_key = ?", (cache_key,))
            current_size_bytes -= size_bytes
            deleted_count += 1
        
        conn.commit()
        conn.close()
        
        final_size_mb = current_size_bytes / (1024 * 1024)
        print(f"[CACHE CLEANUP] Deleted {deleted_count} entries")
        print(f"[CACHE CLEANUP] New size: {final_size_mb:.2f}MB\n")
    
    def get_size_mb(self) -> float:
        """Get total cache size in MB."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(size_bytes) FROM audio_cache")
        total_bytes = cursor.fetchone()[0] or 0
        
        conn.close()
        return total_bytes / (1024 * 1024)
    
    def get_count(self) -> int:
        """Get total number of cached entries."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM audio_cache")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def clear_all(self) -> Tuple[int, float]:
        """
        Delete all cached audio.
        
        Returns:
            (files_deleted, freed_mb)
        """
        count = self.get_count()
        size_mb = self.get_size_mb()
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM audio_cache")
        
        conn.commit()
        conn.close()
        
        return count, size_mb

