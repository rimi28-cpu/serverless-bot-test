import os
import discohook

# Create the discohook client (this is an ASGI app)
app = discohook.Client(
    application_id=os.environ["APPLICATION_ID"],
    public_key=os.environ["PUBLIC_KEY"],
    token=os.environ["DISCORD_TOKEN"],
    default_help_command=True,
)

# Add a simple ping command
@app.load
@discohook.command.slash()
async def ping(i: discohook.Interaction):
    """Replies with Pong!"""
    await i.response.send("Pong!")
