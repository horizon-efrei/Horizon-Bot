"""
Configuration Cog
Handles server configuration for eclasses (channels and role mappings)
"""
import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class ConfigCog(commands.Cog):
    # Create the config group as a class attribute
    config = app_commands.Group(name="config", description="Configuration du bot")
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = 'config.json'  # Simplified config file at root
        self.config_data = self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        # Default config structure
        return {
            "guild_id": "",
            "channels": {"P1": "", "P2": "", "I1": ""},
            "roles": {"P1": "", "P2": "", "I1": ""},
            "teacher_role": "Étudiant-Prof"
        }
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=4, ensure_ascii=False)
    
    def get_channel_for_year(self, guild_id: int, year: str) -> int:
        """Get channel ID for a specific year"""
        channel_id = self.config_data.get('channels', {}).get(year)
        return int(channel_id) if channel_id and channel_id.isdigit() else None
    
    def get_role_for_year(self, guild_id: int, year: str) -> int:
        """Get role ID for a specific year"""
        role_id = self.config_data.get('roles', {}).get(year)
        return int(role_id) if role_id and role_id.isdigit() else None
    
    @config.command(name="channel", description="Configurer le canal d'annonces pour une année")
    @app_commands.describe(
        year="L'année concernée",
        channel="Le canal textuel pour les annonces"
    )
    @app_commands.choices(year=[
        app_commands.Choice(name="Prépa 1", value="P1"),
        app_commands.Choice(name="Prépa 2", value="P2"),
        app_commands.Choice(name="Ingé 1", value="I1")
    ])
    async def config_channel(
        self,
        interaction: discord.Interaction,
        year: app_commands.Choice[str],
        channel: discord.TextChannel
    ):
        # Check if user is admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Vous devez être administrateur pour configurer le bot !",
                ephemeral=True
            )
            return
        
        self.config_data['channels'][year.value] = str(channel.id)
        self.save_config()
        
        await interaction.response.send_message(
            f"✅ Canal configuré : {year.name} → {channel.mention}",
            ephemeral=True
        )
    
    @config.command(name="role", description="Configurer le rôle à mentionner pour une année")
    @app_commands.describe(
        year="L'année concernée",
        role="Le rôle à mentionner"
    )
    @app_commands.choices(year=[
        app_commands.Choice(name="Prépa 1", value="P1"),
        app_commands.Choice(name="Prépa 2", value="P2"),
        app_commands.Choice(name="Ingé 1", value="I1")
    ])
    async def config_role(
        self,
        interaction: discord.Interaction,
        year: app_commands.Choice[str],
        role: discord.Role
    ):
        # Check if user is admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Vous devez être administrateur pour configurer le bot !",
                ephemeral=True
            )
            return
        
        self.config_data['roles'][year.value] = str(role.id)
        self.save_config()
        
        await interaction.response.send_message(
            f"✅ Rôle configuré : {year.name} → {role.mention}",
            ephemeral=True
        )
    
    @config.command(name="view", description="Voir la configuration actuelle")
    async def config_view(self, interaction: discord.Interaction):
        # Check if user is admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Vous devez être administrateur pour voir la configuration !",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="⚙️ Configuration EClass",
            description="Configuration des canaux et rôles pour les annonces de cours",
            color=discord.Color.blue()
        )
        
        # Channel mapping
        channels_text = ""
        year_names = {"P1": "Prépa 1", "P2": "Prépa 2", "I1": "Ingé 1"}
        
        for year_code, year_name in year_names.items():
            channel_id = self.config_data.get('channels', {}).get(year_code)
            if channel_id and channel_id.isdigit():
                channel = interaction.guild.get_channel(int(channel_id))
                channels_text += f"**{year_name}** : {channel.mention if channel else '`Canal supprimé`'}\n"
            else:
                channels_text += f"**{year_name}** : `Non configuré`\n"
        
        embed.add_field(
            name="📢 Canaux d'annonces",
            value=channels_text or "Aucun canal configuré",
            inline=False
        )
        
        # Role mapping
        roles_text = ""
        for year_code, year_name in year_names.items():
            role_id = self.config_data.get('roles', {}).get(year_code)
            if role_id and role_id.isdigit():
                role = interaction.guild.get_role(int(role_id))
                roles_text += f"**{year_name}** : {role.mention if role else '`Rôle supprimé`'}\n"
            else:
                roles_text += f"**{year_name}** : `Non configuré`\n"
        
        embed.add_field(
            name="👥 Rôles à mentionner",
            value=roles_text or "Aucun rôle configuré",
            inline=False
        )
        
        embed.set_footer(text=f"Serveur : {interaction.guild.name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
