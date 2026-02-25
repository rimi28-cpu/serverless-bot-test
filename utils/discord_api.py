import os
import aiohttp
import asyncio
from datetime import datetime, timedelta

CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]

async def refresh_user_token(refresh_token: str):
    """Exchange a refresh token for a new access token."""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post("https://discord.com/api/oauth2/token", data=data) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                # Log error – you may want to raise or return None
                return None

async def add_user_to_guild(guild_id: str, user_id: str, access_token: str, refresh_token: str, pool):
    """
    Attempt to add a user to a guild using their OAuth2 token.
    If token expired, refresh it and update the database, then retry once.
    Returns True if successful, False otherwise.
    """
    url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    json_data = {"access_token": access_token}

    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers=headers, json=json_data) as resp:
            if resp.status in (201, 204):
                # Success – update lastMonitoredCheck or similar if you wish
                return True
            elif resp.status == 401:  # Unauthorized – token expired
                # Try to refresh
                new_tokens = await refresh_user_token(refresh_token)
                if not new_tokens:
                    return False
                # Calculate new expiry (typically 7 days, but check expires_in from Discord)
                expires_at = datetime.utcnow() + timedelta(seconds=new_tokens.get("expires_in", 604800))
                # Update database with new tokens
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE "User"
                        SET "accessToken" = $1, "refreshToken" = $2, "expiresAt" = $3
                        WHERE "userId" = $4
                        """,
                        new_tokens["access_token"], new_tokens["refresh_token"], expires_at, user_id
                    )
                # Retry with new token
                return await add_user_to_guild(guild_id, user_id, new_tokens["access_token"], new_tokens["refresh_token"], pool)
            else:
                # Other error (rate limit, forbidden, etc.)
                # You could increment rejoinAttempts or mark deauthorized if 403/404
                return False
