import os
import asyncio
import discohook
from utils.db import get_db_pool

_discohook_app = discohook.Client(
    application_id=os.environ["APPLICATION_ID"],
    public_key=os.environ["PUBLIC_KEY"],
    token=os.environ["DISCORD_TOKEN"],
    password=os.environ.get("APPLICATION_PASSWORD"),
    default_help_command=True,
)

@_discohook_app.load
@discohook.command.slash()
async def ping(i: discohook.Interaction):
    """Replies with Pong!"""
    await i.response.send("Pong!")

@_discohook_app.load
@discohook.command.slash(name="db_test", description="Test database connection")
async def db_test(i: discohook.Interaction):
    pool = await get_db_pool()
    count = await pool.fetchval('SELECT COUNT(*) FROM "User"')
    await i.response.send(f"Total users: {count}")

# Explicit handler for Vercel
async def handler(request):
    # discohook uses aiohttp - we need to bridge to Vercel's interface
    return await _discohook_app.app.handle_request(request)
    
