import os
from discohook import Client, Interaction, command
from utils.db import get_db_pool
from utils.discord_api import add_user_to_guild

# Initialize the discohook client
app = Client(
    application_id=os.environ["APPLICATION_ID"],
    public_key=os.environ["PUBLIC_KEY"],
    token=os.environ["DISCORD_TOKEN"],
    password=os.environ.get("APPLICATION_PASSWORD"),
    default_help_command=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Slash command: add a single user by ID (using token from database)
@app.load
@command.slash()
async def add_user(ctx: Interaction, user_id: str):
    """Add a user to this server using their stored OAuth token."""
    await ctx.response.defer(ephemeral=True)  # defer because API calls may take time

    pool = await get_db_pool()
    guild_id = str(ctx.guild_id)  # ensure string

    # Fetch user's tokens from Neon
    row = await pool.fetchrow(
        "SELECT access_token, refresh_token FROM users WHERE user_id = $1 AND guild_id = $2",
        user_id, guild_id
    )
    if not row:
        await ctx.response.followup("That user is not in the database.", ephemeral=True)
        return

    success = await add_user_to_guild(
        guild_id=guild_id,
        user_id=user_id,
        access_token=row["access_token"],
        refresh_token=row["refresh_token"],
        pool=pool
    )

    if success:
        await ctx.response.followup(f"Successfully added <@{user_id}> to the server!", ephemeral=True)
    else:
        await ctx.response.followup("Failed to add user. Token may be invalid or expired.", ephemeral=True)

# ─────────────────────────────────────────────────────────────────────────────
# Slash command: trigger batch adding (enqueues users for background processing)
@app.load
@command.slash()
async def add_all(ctx: Interaction):
    """Start adding all users from the database to this server (processed in background)."""
    await ctx.response.defer(ephemeral=True)

    pool = await get_db_pool()
    guild_id = str(ctx.guild_id)

    # Mark all users as not added (or you can have a separate 'pending' table)
    # Here we assume a column 'added' boolean that indicates if they are already in the guild.
    # We'll reset it to false for all users of this guild to trigger re‑add.
    await pool.execute(
        "UPDATE users SET added = false WHERE guild_id = $1",
        guild_id
    )

    await ctx.response.followup(
        "Batch addition started. Users will be added gradually in the background.",
        ephemeral=True
    )

# ─────────────────────────────────────────────────────────────────────────────
# Slash command: send a repeated message in the current channel
@app.load
@command.slash()
async def repeat(ctx: Interaction, text: str, times: int):
    """Send a message multiple times (up to 5 times to avoid timeout)."""
    if times > 5:
        await ctx.response.send("You can only repeat up to 5 times due to serverless limits.", ephemeral=True)
        return

    await ctx.response.defer()  # defer so we can send multiple messages
    channel = ctx.channel
    for i in range(times):
        await channel.send(text)
        await asyncio.sleep(1)  # be gentle to rate limits

# ─────────────────────────────────────────────────────────────────────────────
# Slash command: ping all members in batches of 5
@app.load
@command.slash()
async def ping_all(ctx: Interaction):
    """Mention all members in batches of 5 (limited to first 100 members for safety)."""
    await ctx.response.defer()

    # Fetch members (requires GUILD_MEMBERS intent and privileged intent enabled)
    members = await ctx.guild.fetch_members(limit=100)  # adjust limit as needed
    batch = []
    for member in members:
        if not member.bot:  # optionally skip bots
            batch.append(member.mention)
            if len(batch) == 5:
                await ctx.channel.send(" ".join(batch))
                batch = []
                await asyncio.sleep(1)

    if batch:
        await ctx.channel.send(" ".join(batch))

# ─────────────────────────────────────────────────────────────────────────────
# Error handler (optional)
@app.on_interaction_error()
async def on_error(interaction: Interaction, error: Exception):
    print(f"Error in interaction: {error}")
    # You could also log to a Discord channel using app.send

# Vercel serverless handler
def handler(request):
    return app.handle_request(request)
