import os
import asyncio
from http.server import BaseHTTPRequestHandler
from datetime import datetime
from utils.db import get_db_pool
from utils.discord_api import add_user_to_guild

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        asyncio.run(self.process_batch())
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    async def process_batch(self):
        pool = await get_db_pool()
        guild_id = os.environ["MAIN_GUILD_ID"]

        # Select up to 5 users who:
        # - are active, not deauthorized
        # - have this guild in their monitoredServers
        # - have a cooldown that is either null or in the past
        # - optionally order by lastMonitoredCheck (oldest first)
        rows = await pool.fetch(
            """
            SELECT "userId", "accessToken", "refreshToken", "rejoinAttempts", "cooldownUntil"
            FROM "User"
            WHERE "isActive" = true
              AND "deauthorized" = false
              AND $1 = ANY("monitoredServers")
              AND ("cooldownUntil" IS NULL OR "cooldownUntil" < NOW())
            ORDER BY "lastMonitoredCheck" ASC NULLS FIRST
            LIMIT 5
            """,
            guild_id
        )

        for row in rows:
            user_id = row["userId"]
            success = await add_user_to_guild(
                guild_id=guild_id,
                user_id=user_id,
                access_token=row["accessToken"],
                refresh_token=row["refreshToken"],
                pool=pool
            )

            now = datetime.utcnow()
            if success:
                # Update lastMonitoredCheck, reset rejoinAttempts
                await pool.execute(
                    """
                    UPDATE "User"
                    SET "lastMonitoredCheck" = $1, "rejoinAttempts" = 0
                    WHERE "userId" = $2
                    """,
                    now, user_id
                )
            else:
                # Increment rejoinAttempts, maybe set cooldown if too many failures
                await pool.execute(
                    """
                    UPDATE "User"
                    SET "rejoinAttempts" = "rejoinAttempts" + 1,
                        "lastMonitoredCheck" = $1
                    WHERE "userId" = $2
                    """,
                    now, user_id
                )
                # Optional: if rejoinAttempts > 3, set cooldown for 1 hour
                # (you can implement more sophisticated logic)

            await asyncio.sleep(1)  # be kind to rate limits
