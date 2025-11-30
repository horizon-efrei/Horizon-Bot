"""
Teachers Cog
Handles teacher statistics and information
"""
import discord
from discord.ext import commands
from discord import app_commands

class TeachersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = bot.data_manager
    
    @app_commands.command(name="teachers", description="Afficher les statistiques des enseignants")
    async def teachers(self, interaction: discord.Interaction):
        """Display teacher statistics"""
        # Get teacher statistics
        teachers_stats = self.data.get_teacher_statistics()
        
        if not teachers_stats:
            await interaction.response.send_message(
                "📚 Aucun cours terminé pour le moment.",
                ephemeral=True
            )
            return
        
        # Create embed
        embed = discord.Embed(
            title="👨‍🏫 Statistiques des Enseignants",
            description="Classement par nombre de cours donnés",
            color=discord.Color.green()
        )
        
        # Add field for each teacher
        for i, teacher in enumerate(teachers_stats[:10], 1):  # Limit to top 10
            teacher_user = await self.bot.fetch_user(teacher['teacher_id'])
            teacher_name = teacher_user.display_name if teacher_user else f"Utilisateur {teacher['teacher_id']}"
            
            # Create medal emoji for top 3
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
            
            # Format time
            time_str = f"{teacher['total_hours']}h{teacher['total_minutes']:02d}min" if teacher['total_hours'] > 0 or teacher['total_minutes'] > 0 else "0h00min"
            
            embed.add_field(
                name=f"{medal}{i}. {teacher_name}",
                value=(
                    f"📚 **{teacher['completed_classes']}** cours donnés\n"
                    f"⏱️ **{time_str}** au total\n"
                    f"👥 **{teacher['max_participants']}** participants max"
                ),
                inline=True
            )
        
        embed.set_footer(text=f"Demandé par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(TeachersCog(bot))
