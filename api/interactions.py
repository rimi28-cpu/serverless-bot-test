# api/interactions.py
import os
from discohook import Client, Interaction, command
from utils.db import get_db_pool
from utils.discord_api import add_user_to_guild

app = Client(...)  # your config

@app.load
@command.slash()
async def add_user(ctx: Interaction, user_id: str):
    """Add a user by ID to this server (using stored token)."""
    pool = await get_db_pool()
    # Fetch token for this user from Neon
    token_data = await pool.fetchrow(
        "SELECT access_token, refresh_token FROM users WHERE user_id = $1",
        user_id
    )
    if not token_data:
        await ctx.response.send("User not found in database.", ephemeral=True)
        return
    
    # Try to add user to the current guild
    success = await add_user_to_guild(
        guild_id=ctx.guild_id,
        user_id=user_id,
        access_token=token_data['access_token'],
        refresh_token=token_data['refresh_token'],
        pool=pool  # so add_user_to_guild can refresh and update DB if needed
    )
    if success:
        await ctx.response.send(f"Added <@{user_id}> to the server!")
    else:
        await ctx.response.send("Failed to add user. Token might be invalid.", ephemeral=True)
