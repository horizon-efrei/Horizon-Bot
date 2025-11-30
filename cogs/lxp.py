"""
LXP Cog
Handles LXP related commands
"""
import discord
from discord.ext import commands
from discord import app_commands

class LXPCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="lxp", description="Gagner des points LXP avec Horizon")
    async def lxp(self, interaction: discord.Interaction):
        """Display LXP information"""
        embed = discord.Embed(
            title="📚 Comment gagner des points LXP avec Horizon ?",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="👨‍🏫 Cours en ligne",
            value="**2 à 5 points**",
            inline=False
        )
        
        embed.add_field(
            name="📜 Fiches",
            value="**2 à 4 points**\n*Corrections de TD, Fiche de vocabulaire ou copier-coller de cours ne donnent pas de points*",
            inline=False
        )
        
        embed.add_field(
            name="✍️ Secrétaire d'examen",
            value="Points LXP + **rémunéré par l'EFREI**",
            inline=False
        )
        
        embed.add_field(
            name="🗣️ Investissement important sur Discord",
            value="**1 à 3 points**",
            inline=False
        )

        embed.add_field(
            name="❓ Plus d'informations",
            value="Contactez une personne du bureau Horizon",
            inline=False
        )
        
        embed.set_footer(text=f"Demandé par {interaction.user.display_name}")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(LXPCog(bot))
