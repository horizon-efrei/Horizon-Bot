"""
HorizonBot - Online Class Management System
Main bot file
"""
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from utils.data_manager import DataManager

# Load environment variables from .env file
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

class HorizonBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.data_manager = DataManager()
    
    async def setup_hook(self):
        """Load all cogs"""
        cogs = ['cogs.eclass', 'cogs.latex', 'cogs.stats', 'cogs.events', 'cogs.config', 'cogs.lxp', 'cogs.teachers']
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f'✅ Loaded {cog}')
            except Exception as e:
                print(f'❌ Failed to load {cog}: {e}')
        
        # Sync commands
        try:
            # Clear guild-specific commands to avoid duplicates
            with open('config.json', 'r') as f:
                import json
                config = json.load(f)
                guild_id = int(config.get("guild_id", 0))
            guild = discord.Object(id=guild_id)
            self.tree.clear_commands(guild=guild)
            await self.tree.sync(guild=guild)
            print(f'🧹 Cleared guild-specific commands')
            
            # Sync globally (takes up to 1 hour to propagate)
            synced = await self.tree.sync()
            print(f'🔄 Synced {len(synced)} command(s) globally')
    
        except Exception as e:
            print(f'❌ Error syncing commands: {e}')
    
    async def on_ready(self):
        print(f'🤖 {self.user} has connected to Discord!')
        print(f'📡 Bot is in {len(self.guilds)} guild(s)')
        print('✅ Bot is ready!')

def main():
    bot = HorizonBot()
    
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN environment variable not set!")
        print("Please set it with your bot token in the .env file")
        return
    
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
