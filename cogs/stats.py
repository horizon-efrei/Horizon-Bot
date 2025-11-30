"""
Statistics Cog
Handles server statistics for administrators
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = bot.data_manager
    
    @app_commands.command(name="stats", description="Afficher les statistiques du serveur")
    async def stats(self, interaction: discord.Interaction):
        # Check if user is admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Vous devez avoir les permissions d'administrateur pour utiliser cette commande !",
                ephemeral=True
            )
            return
        
        # Get statistics
        message_stats = self.data.get_message_stats()
        eclasses_since_sept = self.data.count_eclasses_since_sept()
        total_eclasses = len(self.data.get_eclasses())
        time_data = self.data.get_total_eclass_hours_since_sept()
        
        # Create stats embed
        embed = discord.Embed(
            title="📊 Statistiques du serveur",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="💬 Messages depuis le 1er septembre",
            value=f"{message_stats['since_sept']:,}",
            inline=False
        )
        embed.add_field(
            name="💾 Total messages enregistrés",
            value=f"{message_stats['total']:,}",
            inline=True
        )
        embed.add_field(
            name="📚 Cours depuis le 1er septembre",
            value=f"{eclasses_since_sept}",
            inline=False
        )
        
        # Format time
        time_str = f"{time_data['hours']}h{time_data['minutes']:02d}min" if time_data['hours'] > 0 or time_data['minutes'] > 0 else "0h00min"
        embed.add_field(
            name="⏱️ Heures de cours depuis le 1er septembre",
            value=time_str,
            inline=False
        )
        embed.add_field(
            name="📝 Total Cours",
            value=f"{total_eclasses}",
            inline=True
        )
        embed.set_footer(text=f"Demandé par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(StatsCog(bot))
