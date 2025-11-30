"""
Utility functions for the bot
"""
import discord

def has_role(member: discord.Member, role_name: str) -> bool:
    """Check if a member has a specific role"""
    return discord.utils.get(member.roles, name=role_name) is not None

def is_teacher(interaction: discord.Interaction) -> bool:
    """Check if user has the Étudiant-Prof role"""
    return has_role(interaction.user, "Étudiant-Prof")

def is_teacher_member(member: discord.Member) -> bool:
    """Check if a member has the Étudiant-Prof role"""
    return has_role(member, "Étudiant-Prof")

def can_manage_eclass(interaction: discord.Interaction) -> bool:
    """Check if user can manage eclasses (Admin or specific role)"""
    # Check if user is administrator
    if interaction.user.guild_permissions.administrator:
        return True
    # Check if user has the management role
    roles = ["Respo Pôle Ef'Réussite", "Respo eProfs", "Respo Eprof P1", "Respo Eprof P2", "Respo Eprof I1"]
    return any(has_role(interaction.user, role) for role in roles)

def can_create_eclass(interaction: discord.Interaction) -> bool:
    """Check if user can create eclasses (Teacher, Admin, or Manager)"""
    return is_teacher(interaction) or can_manage_eclass(interaction)

async def send_error(interaction: discord.Interaction, message: str):
    """Send an error message"""
    await interaction.response.send_message(f"❌ {message}", ephemeral=True)

async def send_success(interaction: discord.Interaction, message: str, ephemeral: bool = False):
    """Send a success message"""
    await interaction.response.send_message(f"✅ {message}", ephemeral=ephemeral)
