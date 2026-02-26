import os
import asyncpg

_pool = None

async def get_db_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["NEON_DATABASE_URL"])
    return _pool
