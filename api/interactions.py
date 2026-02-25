import os
import asyncio
from discohook import Client, Interaction, command
from utils.db import get_db_pool
from utils.discord_api import add_user_to_guild

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
    await ctx.response.defer(ephemeral=True)

    pool = await get_db_pool()
    guild_id = str(ctx.guild_id)

    # Fetch user from database
    row = await pool.fetchrow(
        """
        SELECT "accessToken", "refreshToken", "isActive", "deauthorized"
        FROM "User"
        WHERE "userId" = $1
        """,
        user_id
    )
    if not row:
        await ctx.response.followup("User not found in database.", ephemeral=True)
        return

    if not row["isActive"] or row["deauthorized"]:
        await ctx.response.followup("User is inactive or deauthorized.", ephemeral=True)
        return

    success = await add_user_to_guild(
        guild_id=guild_id,
        user_id=user_id,
        access_token=row["accessToken"],
        refresh_token=row["refreshToken"],
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
    """Start adding all eligible users to this server (processed in background)."""
    await ctx.response.send(
        "Batch addition started. Users will be added gradually in the background.",
        ephemeral=True
    )
    # Nothing else to do – the cron job will pick them up.

# ─────────────────────────────────────────────────────────────────────────────
# Slash command: send a repeated message in the current channel
@app.load
@command.slash()
async def repeat(ctx: Interaction, text: str, times: int):
    """Send a message multiple times (up to 5 times to avoid timeout)."""
    if times > 5:
        await ctx.response.send("You can only repeat up to 5 times due to serverless limits.", ephemeral=True)
        return

    await ctx.response.defer()
    channel = ctx.channel
    for i in range(times):
        await channel.send(text)
        await asyncio.sleep(1)

# ─────────────────────────────────────────────────────────────────────────────
# Slash command: ping all members in batches of 5
@app.load
@command.slash()
async def ping_all(ctx: Interaction):
    """Mention all members in batches of 5 (limited to first 100 members for safety)."""
    await ctx.response.defer()

    members = await ctx.guild.fetch_members(limit=100)
    batch = []
    for member in members:
        if not member.bot:
            batch.append(member.mention)
            if len(batch) == 5:
                await ctx.channel.send(" ".join(batch))
                batch = []
                await asyncio.sleep(1)
    if batch:
        await ctx.channel.send(" ".join(batch))

# ─────────────────────────────────────────────────────────────────────────────
@app.on_interaction_error()
async def on_error(interaction: Interaction, error: Exception):
    print(f"Error in interaction: {error}")

def handler(request):
    return app.handle_request(request)
