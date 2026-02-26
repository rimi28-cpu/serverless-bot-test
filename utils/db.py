import os

_pool = None

async def get_db_pool():
    global _pool
    if _pool is None:
        import asyncpg  # Import here instead of top-level
        _pool = await asyncpg.create_pool(os.environ["NEON_DATABASE_URL"])
    return _pool
    
