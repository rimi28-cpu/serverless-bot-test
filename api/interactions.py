import os
import discohook
from utils.db import get_db_pool

app = discohook.Client(
    application_id=os.environ["APPLICATION_ID"],
    public_key=os.environ["PUBLIC_KEY"],
    token=os.environ["DISCORD_TOKEN"],
    password=os.environ.get("APPLICATION_PASSWORD"),
    default_help_command=True,
)

@app.load
@discohook.command.slash()
async def ping(i: discohook.Interaction):
    """Replies with Pong!"""
    await i.response.send("Pong!")

@app.load
@discohook.command.slash(name="db_test", description="Test database connection")
async def db_test(i: discohook.Interaction):
    pool = await get_db_pool()
    count = await pool.fetchval('SELECT COUNT(*) FROM "User"')
    await i.response.send(f"Total users: {count}")

# Export the underlying aiohttp application
# discohook.Client stores the aiohttp app in .app attribute
handler = app.app
