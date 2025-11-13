"""
In-memory cache for start codes
Loaded at startup, persists for application lifetime
Can be reloaded on-demand for admin updates
"""
from typing import Dict, Optional, Any
from datetime import datetime

# Global cache storage
_CACHE: Dict[str, Any] = {
    "codes": {},  # Dict: code (uppercase) -> start code dict
    "last_loaded": None
}


def load_cache():
    """Load all start codes from DB into memory"""
    from app.db.base import get_db
    from app.db import crud
    
    print("[START-CODE-CACHE] 📦 Loading start codes into memory...")
    
    with get_db() as db:
        start_codes = crud.get_all_start_codes(db)
        
        codes_dict = {}
        for sc in start_codes:
            code_data = {
                "code": sc.code,
                "description": sc.description,
                "persona_id": str(sc.persona_id) if sc.persona_id else None,
                "history_id": str(sc.history_id) if sc.history_id else None,
                "is_active": sc.is_active,
                "created_at": sc.created_at.isoformat(),
                "updated_at": sc.updated_at.isoformat() if sc.updated_at else None
            }
            codes_dict[sc.code.upper()] = code_data
        
        _CACHE["codes"] = codes_dict
        _CACHE["last_loaded"] = datetime.utcnow()
    
    print(f"[START-CODE-CACHE] ✅ Loaded {len(_CACHE['codes'])} start codes")


def get_start_code(code: str) -> Optional[Dict[str, Any]]:
    """Get cached start code by code
    
    Args:
        code: 5-character alphanumeric code (case-insensitive)
    
    Returns:
        Start code dict or None if not found
    """
    return _CACHE["codes"].get(code.upper())


def get_all_start_codes() -> Dict[str, Dict[str, Any]]:
    """Get all cached start codes
    
    Returns:
        Dict of code -> start code data
    """
    return _CACHE["codes"].copy()


def reload_cache():
    """Reload cache from database (call after admin changes)"""
    print("[START-CODE-CACHE] 🔄 Reloading start code cache...")
    load_cache()


def is_cache_loaded() -> bool:
    """Check if cache has been loaded"""
    return len(_CACHE["codes"]) > 0 or _CACHE["last_loaded"] is not None


def get_cache_info() -> Dict[str, Any]:
    """Get cache statistics"""
    return {
        "count": len(_CACHE["codes"]),
        "last_loaded": _CACHE["last_loaded"].isoformat() if _CACHE["last_loaded"] else None
    }

