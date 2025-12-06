"""
EClass Management Cog
Handles all eclass-related commands and functionality
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import asyncio
import json
import os
from utils.helpers import send_error, send_success, can_manage_eclass, can_create_eclass, is_teacher_member

def format_duration(minutes: int) -> str:
    """Format duration in minutes to readable format (Xh Ymin)"""
    if minutes < 60:
        return f"{minutes} min"
    
    hours = minutes // 60
    mins = minutes % 60
    
    if mins == 0:
        return f"{hours}h"
    
    return f"{hours}h {mins}min"

class EClassCog(commands.Cog):
    # Create the command group as a class attribute
    eclass = app_commands.Group(name="eclass", description="Gestion des cours en ligne")
    
    def __init__(self, bot):
        self.bot = bot
        self.data = bot.data_manager
        self.check_eclass_reminders.start()
        self.tracking_tasks = {}
        self.class_modules = self.load_class_modules()
    
    def load_class_modules(self):
        """Load class modules from JSON file"""
        modules_file = 'data/class_modules.json'
        if os.path.exists(modules_file):
            with open(modules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.check_eclass_reminders.cancel()
        for task in self.tracking_tasks.values():
            if not task.done():
                task.cancel()
    
    async def subject_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for subjects based on selected year"""
        # Try to get the selected year from the command namespace
        try:
            # Access the namespace to get the year parameter if it's been filled
            namespace = interaction.namespace
            selected_year = namespace.year if hasattr(namespace, 'year') and namespace.year else None
        except:
            selected_year = None
        
        # Collect subjects based on selected year
        all_subjects = []
        
        if selected_year:
            # Filter subjects only for the selected year
            for category, data in self.class_modules.items():
                if f"-{selected_year}" in category:
                    subjects = data.get('matières', [])
                    all_subjects.extend(subjects)
            
            # If no subjects found for this year, show all with a prefix indicator
            if not all_subjects:
                for category, data in self.class_modules.items():
                    subjects = data.get('matières', [])
                    # Add year prefix to show which year each subject belongs to
                    year_tag = category.split('-')[-1] if '-' in category else ''
                    all_subjects.extend([(f"[{year_tag}] {s}", s) for s in subjects])
        else:
            # No year selected yet, show all subjects with year tags
            for category, data in self.class_modules.items():
                subjects = data.get('matières', [])
                year_tag = category.split('-')[-1] if '-' in category else ''
                all_subjects.extend([(f"[{year_tag}] {s}", s) for s in subjects])
        
        # Remove duplicates and filter based on current input
        if all_subjects and isinstance(all_subjects[0], tuple):
            # With year tags
            unique_subjects = list({v: k for k, v in all_subjects}.items())
            filtered = [(v, k) for k, v in unique_subjects if current.lower() in v.lower() or current.lower() in k.lower()]
            return [
                app_commands.Choice(name=display[:100], value=value)
                for display, value in sorted(filtered, key=lambda x: x[0])[:25]
            ]
        else:
            # Without year tags (when year is selected)
            unique_subjects = list(set(all_subjects))
            filtered = [s for s in unique_subjects if current.lower() in s.lower()]
            return [
                app_commands.Choice(name=subject, value=subject)
                for subject in sorted(filtered)[:25]
            ]
    
    def get_category_for_year(self, year: str, subject: str) -> str:
        """Find the category (e.g., Info-P1, Maths-P2) for a given year and subject"""
        for category, data in self.class_modules.items():
            if f"-{year}" in category and subject in data.get('matières', []):
                return category
        return None
    
    @eclass.command(name="create", description="Créer un nouveau cours")
    @app_commands.describe(
        title="Titre du cours",
        description="Description du cours",
        year="Année concernée (P1, P2, I1)",
        subject="Matière du cours",
        date="Date et heure de début (format: DD-MM-YYYY HH:MM)",
        duration="Durée du cours en minutes",
        channel_type="Type de canal (vocal ou stage)",
        teacher="Enseignant (optionnel, admin/modérateur uniquement)"
    )
    @app_commands.choices(
        year=[
            app_commands.Choice(name="Prépa 1", value="P1"),
            app_commands.Choice(name="Prépa 2", value="P2"),
            app_commands.Choice(name="Ingé 1", value="I1")
        ],
        channel_type=[
            app_commands.Choice(name="🔊 Canal Vocal", value="vocal"),
            app_commands.Choice(name="🎭 Canal Conférence", value="stage")
        ]
    )
    @app_commands.autocomplete(subject=subject_autocomplete)
    async def create(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        year: app_commands.Choice[str],
        subject: str,
        date: str,
        duration: int,
        channel_type: app_commands.Choice[str],
        teacher: discord.Member = None
    ):
        # Check if user can create eclasses
        if not can_create_eclass(interaction):
            await send_error(interaction, "Vous devez avoir le rôle 'Étudiant-Prof', être modérateur ou administrateur pour créer des cours !")
            return
        
        # If teacher is specified, check if user has permission to create for others
        if teacher and not can_manage_eclass(interaction):
            await send_error(interaction, "Seuls les administrateurs et modérateurs peuvent créer des cours pour d'autres personnes !")
            return
        
        # If no teacher specified, use the command user
        actual_teacher = teacher if teacher else interaction.user
        
        # Verify the specified teacher has the Étudiant-Prof role
        if teacher and not is_teacher_member(actual_teacher):
            await send_error(interaction, f"{actual_teacher.mention} n'a pas le rôle 'Étudiant-Prof' !")
            return
        
        try:
            # Parse the date
            class_datetime = datetime.strptime(date, "%d-%m-%Y %H:%M")
            
            # Check if date is in the future
            if class_datetime <= datetime.now():
                await send_error(interaction, "La date du cours doit être dans le futur !")
                return
            
            # Calculate end time
            end_datetime = class_datetime + timedelta(minutes=duration)
            
            # Find the category for this subject and year
            category = self.get_category_for_year(year.value, subject)
            if not category:
                await send_error(
                    interaction,
                    f" La matière '{subject}' n'existe pas pour {year.name}. Utilisez l'autocomplétion pour voir les matières disponibles."
                )
                return
            
            # Get the channel ID from the JSON
            category_data = self.class_modules.get(category, {})
            channel_id_key = 'vocal-id' if channel_type.value == 'vocal' else 'stage-id'
            channel_id_str = category_data.get(channel_id_key, '')
            
            if not channel_id_str or not channel_id_str.isdigit():
                await send_error(
                    interaction,
                    f"Aucun canal {channel_type.name} configuré pour {category}. Veuillez configurer le canal dans `data/class_modules.json`."
                )
                return
            
            voice_channel = interaction.guild.get_channel(int(channel_id_str))
            if not voice_channel:
                await send_error(
                    interaction,
                    f"Canal introuvable ! Vérifiez que l'ID du canal {channel_type.name} pour {category} est correct."
                )
                return
            
            # Get configuration from ConfigCog
            config_cog = self.bot.get_cog('ConfigCog')
            if not config_cog:
                await send_error(interaction, "Erreur : Module de configuration non chargé !")
                return
            
            year_value = year.value
            
            # Get configured channel
            channel_id = config_cog.get_channel_for_year(interaction.guild.id, year_value)
            if not channel_id:
                await send_error(
                    interaction,
                    f"Canal non configuré pour {year.name} ! Un administrateur doit utiliser `/eclass_config_channel` pour le configurer."
                )
                return
            
            announcement_channel = interaction.guild.get_channel(channel_id)
            if not announcement_channel:
                await send_error(
                    interaction,
                    f"Canal configuré introuvable ! Veuillez contacter un administrateur."
                )
                return
            
            # Get configured role
            role_id = config_cog.get_role_for_year(interaction.guild.id, year_value)
            role = interaction.guild.get_role(role_id) if role_id else None
            
            # Create Discord timestamps (Unix timestamp)
            start_timestamp = int(class_datetime.timestamp())
            end_timestamp = int(end_datetime.timestamp())
            
            # Create embed
            embed = discord.Embed(
                title=f"{title}",
                description=description,
                color=discord.Color.orange(),
                timestamp=class_datetime
            )
            embed.add_field(name="📚 Matière", value=subject, inline=False)
            embed.add_field(
                name="📅 Début", 
                value=f"<t:{start_timestamp}:F>\n<t:{start_timestamp}:R>", 
                inline=True
            )
            embed.add_field(
                name="🏁 Fin", 
                value=f"<t:{end_timestamp}:t>", 
                inline=True
            )
            embed.add_field(name="⏱️ Durée", value=format_duration(duration), inline=True)
            embed.add_field(name="🔊 Lieu", value=voice_channel.mention, inline=True)
            embed.add_field(name="👨‍🏫 E-Prof", value=actual_teacher.mention, inline=True)
            embed.set_footer(text="Réagissez avec 🔔 pour être notifié 30 minutes avant le début du cours !")
            
            # Send to announcement channel with role mention
            if role:
                mention_text = role.mention
                announcement_msg = await announcement_channel.send(
                    content=f"{mention_text} 📢 **Nouveau cours programmé !**",
                    embed=embed
                )
            else:
                announcement_msg = await announcement_channel.send(
                    content=f"📢 **Nouveau cours programmé pour {year.name} !**",
                    embed=embed
                )
            
            # Send confirmation
            if teacher:
                # If created for someone else
                await interaction.response.send_message(
                    f"✅ Cours créé pour {actual_teacher.mention} et annoncé dans {announcement_channel.mention} !",
                    ephemeral=True
                )
            else:
                # If created for self
                await interaction.response.send_message(
                    f"✅ Cours créé et annoncé dans {announcement_channel.mention} !",
                    ephemeral=True
                )
            
            # Add reaction
            await announcement_msg.add_reaction("🔔")
            
            # Store eclass data
            eclass_data = {
                'title': title,
                'description': description,
                'datetime': class_datetime.isoformat(),
                'end_datetime': end_datetime.isoformat(),
                'duration': duration,
                'year': year_value,
                'channel_id': voice_channel.id,
                'subject': subject,
                'category': category,
                'teacher_id': actual_teacher.id,
                'message_id': announcement_msg.id,
                'guild_id': interaction.guild.id,
                'channel_message_id': announcement_channel.id,
                'subscribed_users': [],
                'status': 'scheduled',
                'started_at': None,
                'ended_at': None,
                'min_participants': 0,
                'max_participants': 0,
                'current_participants': 0,
                'notified': False
            }
            eclass_id = self.data.add_eclass(eclass_data)
            
            # Add eclass ID to the embed
            embed.add_field(name="🆔 ID du cours", value=f"`{eclass_id}`", inline=True)
            await announcement_msg.edit(embed=embed)
            
        except ValueError:
            await send_error(
                interaction,
                "Format de date invalide ! Veuillez utiliser : DD-MM-AAAA HH:MM (par exemple, 15-11-2025 14:30)"
            )
    
    async def ongoing_eclass_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for ongoing eclasses"""
        ongoing_classes = []
        
        for eclass_id, eclass in self.data.get_eclasses().items():
            if eclass['status'] != 'ongoing':
                continue
            
            # Check if user is teacher or has management permission
            is_owner = eclass['teacher_id'] == interaction.user.id
            can_manage = can_manage_eclass(interaction)
            
            if is_owner or can_manage:
                # Format: "EC0001 - Mathématiques"
                choice_name = f"{eclass_id} - {eclass['title']}"
                if current.lower() in choice_name.lower():
                    ongoing_classes.append((choice_name, eclass_id))
        
        # Return max 25 choices (Discord limit)
        return [
            app_commands.Choice(name=name, value=value)
            for name, value in sorted(ongoing_classes)[:25]
        ]
    
    async def scheduled_eclass_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for scheduled eclasses"""
        scheduled_classes = []
        
        for eclass_id, eclass in self.data.get_eclasses().items():
            if eclass['status'] != 'scheduled':
                continue
            
            # Check if user is teacher or has management permission
            is_owner = eclass['teacher_id'] == interaction.user.id
            can_manage = can_manage_eclass(interaction)
            
            if is_owner or can_manage:
                # Format: "EC0001 - Mathématiques"
                choice_name = f"{eclass_id} - {eclass['title']}"
                if current.lower() in choice_name.lower():
                    scheduled_classes.append((choice_name, eclass_id))
        
        # Return max 25 choices (Discord limit)
        return [
            app_commands.Choice(name=name, value=value)
            for name, value in sorted(scheduled_classes)[:25]
        ]
    
    @eclass.command(name="end", description="Terminer un cours")
    @app_commands.describe(eclass_id="Sélectionnez le cours à terminer")
    @app_commands.autocomplete(eclass_id=ongoing_eclass_autocomplete)
    async def end(self, interaction: discord.Interaction, eclass_id: str):
        # Check if user can create/manage eclasses
        if not can_create_eclass(interaction):
            await send_error(interaction, "Vous devez avoir le rôle 'Etudiant-prof' ou gestionnaire de cours !")
            return
        
        eclass = self.data.get_eclass(eclass_id)
        if not eclass:
            await send_error(interaction, "Cours introuvable !")
            return
        
        # Check if user is the teacher or has management permission
        is_owner = eclass['teacher_id'] == interaction.user.id
        can_manage = can_manage_eclass(interaction)
        
        if not is_owner and not can_manage:
            await send_error(interaction, "Seul l'étudiant-prof qui a créé ce cours ou un administrateur/modérateur peut le terminer !")
            return
        
        if eclass['status'] != 'ongoing':
            await send_error(interaction, f"Ce cours n'est pas en cours (statut : {eclass['status']}) !")
            return
        
        # Update eclass status
        updates = {'status': 'completed', 'ended_at': datetime.now().isoformat()}
        
        # Final participant count
        channel = self.bot.get_channel(eclass['channel_id'])
        if channel and isinstance(channel, discord.VoiceChannel):
            participant_count = len(channel.members)
            updates['current_participants'] = participant_count
            updates['max_participants'] = max(eclass['max_participants'], participant_count)
            updates['min_participants'] = min(eclass['min_participants'], participant_count)
        
        self.data.update_eclass(eclass_id, updates)
        
        # Stop tracking participants
        if eclass_id in self.tracking_tasks and not self.tracking_tasks[eclass_id].done():
            self.tracking_tasks[eclass_id].cancel()
        
        # Get updated eclass data
        eclass = self.data.get_eclass(eclass_id)
        
        # Create summary embed
        started = datetime.fromisoformat(eclass['started_at'])
        ended = datetime.fromisoformat(eclass['ended_at'])
        duration = ended - started
        
        embed = discord.Embed(
            title=f"📊 Résumé du cours : {eclass['title']}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Durée", value=str(duration).split('.')[0], inline=True)
        embed.add_field(name="Participants minimum", value=str(eclass['min_participants']), inline=True)
        embed.add_field(name="Participants maximum", value=str(eclass['max_participants']), inline=True)
        
        await interaction.response.send_message(
            f"✅ Le cours '{eclass['title']}' est terminé !",
            embed=embed,
            ephemeral=False
        )

    @eclass.command(name="cancel", description="Annuler un cours")
    @app_commands.describe(eclass_id="Sélectionnez le cours à annuler")
    @app_commands.autocomplete(eclass_id=scheduled_eclass_autocomplete)
    async def cancel(self, interaction: discord.Interaction, eclass_id: str):
        # Check if user can create/manage eclasses
        if not can_create_eclass(interaction):
            await send_error(interaction, "Vous devez avoir le rôle 'Etudiant-prof' ou gestionnaire de cours !")
            return
        
        eclass = self.data.get_eclass(eclass_id)
        if not eclass:
            await send_error(interaction, "Cours introuvable !")
            return
        
        # Check if user is the teacher or has management permission
        is_owner = eclass['teacher_id'] == interaction.user.id
        can_manage = can_manage_eclass(interaction)
        
        if not is_owner and not can_manage:
            await send_error(interaction, "Seul l'étudiant-prof qui a créé ce cours ou un gestionnaire de cours peut l'annuler !")
            return
        
        if eclass['status'] != 'scheduled':
            await send_error(interaction, f"Ce cours ne peut pas être annulé car il est {eclass['status']} !")
            return
        
        # Update eclass status
        updates = {'status': 'canceled'}
        self.data.update_eclass(eclass_id, updates)
        await send_success(interaction, f"Le cours '{eclass['title']}' a été annulé !", ephemeral=False)

    @eclass.command(name="edit", description="Modifier un cours programmé")
    @app_commands.describe(
        eclass_id="Sélectionnez le cours à modifier",
        title="Nouveau titre (optionnel)",
        description="Nouvelle description (optionnel)",
        date="Nouvelle date et heure (format: DD-MM-YYYY HH:MM, optionnel)",
        duration="Nouvelle durée en minutes (optionnel)"
    )
    @app_commands.autocomplete(eclass_id=scheduled_eclass_autocomplete)
    async def edit(
        self,
        interaction: discord.Interaction,
        eclass_id: str,
        title: str = None,
        description: str = None,
        date: str = None,
        duration: int = None
    ):
        # Check if user can create/manage eclasses
        if not can_create_eclass(interaction):
            await send_error(interaction, "Vous devez avoir le rôle 'Etudiant-prof' ou gestionnaire de cours !")
            return
        
        # Extract eclass_id if user manually typed "EC0001 - Title" instead of using autocomplete
        if ' - ' in eclass_id:
            eclass_id = eclass_id.split(' - ')[0].strip()
        
        eclass = self.data.get_eclass(eclass_id)
        if not eclass:
            await send_error(interaction, "Cours introuvable !")
            return
        
        # Check if user is the teacher or has management permission
        is_owner = eclass['teacher_id'] == interaction.user.id
        can_manage = can_manage_eclass(interaction)
        
        if not is_owner and not can_manage:
            await send_error(interaction, "Seul l'étudiant-prof qui a créé ce cours ou un gestionnaire peut le modifier !")
            return
        
        if eclass['status'] != 'scheduled':
            await send_error(interaction, f"Ce cours ne peut pas être modifié car il est {eclass['status']} !")
            return
        
        # Check if at least one field is provided
        if not any([title, description, date, duration]):
            await send_error(interaction, "Vous devez spécifier au moins un champ à modifier !")
            return
        
        updates = {}
        
        # Update title if provided
        if title:
            updates['title'] = title
        
        # Update description if provided
        if description:
            updates['description'] = description
        
        # Update date if provided
        if date:
            try:
                new_datetime = datetime.strptime(date, "%d-%m-%Y %H:%M")
                
                # Check if date is in the future
                if new_datetime <= datetime.now():
                    await send_error(interaction, "La nouvelle date du cours doit être dans le futur !")
                    return
                
                # Calculate new end time
                current_duration = eclass.get('duration', 60)
                if duration:
                    current_duration = duration
                    
                end_datetime = new_datetime + timedelta(minutes=current_duration)
                
                updates['datetime'] = new_datetime.isoformat()
                updates['end_datetime'] = end_datetime.isoformat()
                updates['notified'] = False  # Reset notification flag
                
            except ValueError:
                await send_error(
                    interaction,
                    "Format de date invalide ! Veuillez utiliser : DD-MM-YYYY HH:MM (par exemple, 15-12-2025 14:30)"
                )
                return
        
        # Update duration if provided (and date wasn't updated)
        if duration and not date:
            current_datetime = datetime.fromisoformat(eclass['datetime'])
            end_datetime = current_datetime + timedelta(minutes=duration)
            updates['duration'] = duration
            updates['end_datetime'] = end_datetime.isoformat()
        elif duration and date:
            # Duration already handled with date update
            updates['duration'] = duration
        
        # Update the eclass
        self.data.update_eclass(eclass_id, updates)
        
        # Get updated eclass for embed update
        updated_eclass = self.data.get_eclass(eclass_id)
        
        # Update the announcement message embed
        try:
            announcement_channel = self.bot.get_channel(updated_eclass['channel_message_id'])
            if announcement_channel:
                announcement_msg = await announcement_channel.fetch_message(updated_eclass['message_id'])
                
                # Recreate embed with updated info
                class_datetime = datetime.fromisoformat(updated_eclass['datetime'])
                end_datetime = datetime.fromisoformat(updated_eclass['end_datetime'])
                start_timestamp = int(class_datetime.timestamp())
                end_timestamp = int(end_datetime.timestamp())
                
                embed = discord.Embed(
                    title=updated_eclass['title'],
                    description=updated_eclass['description'],
                    color=discord.Color.orange(),
                    timestamp=class_datetime
                )
                embed.add_field(name="📚 Matière", value=updated_eclass['subject'], inline=False)
                embed.add_field(
                    name="📅 Début", 
                    value=f"<t:{start_timestamp}:F>\n<t:{start_timestamp}:R>", 
                    inline=True
                )
                embed.add_field(
                    name="🏁 Fin", 
                    value=f"<t:{end_timestamp}:t>", 
                    inline=True
                )
                embed.add_field(name="⏱️ Durée", value=format_duration(updated_eclass['duration']), inline=True)
                
                voice_channel = self.bot.get_channel(updated_eclass['channel_id'])
                if voice_channel:
                    embed.add_field(name="🔊 Lieu", value=voice_channel.mention, inline=True)
                
                embed.add_field(name="👨‍🏫 E-Prof", value=f"<@{updated_eclass['teacher_id']}>", inline=True)
                embed.add_field(name="🆔 ID du cours", value=f"`{eclass_id}`", inline=True)
                embed.set_footer(text="Réagissez avec 🔔 pour être notifié 30 minutes avant le début du cours !")
                
                await announcement_msg.edit(embed=embed)
        except Exception as e:
            print(f"Error updating announcement message: {e}")
        
        # Build success message
        changes = []
        if title:
            changes.append(f"titre: '{title}'")
        if description:
            changes.append(f"description: '{description}'")
        if date:
            changes.append(f"date: {date}")
        if duration:
            changes.append(f"durée: {duration}min")
        
        await send_success(
            interaction, 
            f"Cours '{updated_eclass['title']}' modifié !\nChangements: {', '.join(changes)}", 
            ephemeral=False
        )
    
    @eclass.command(name="list", description="Lister tous les cours programmés")
    async def list(self, interaction: discord.Interaction):
        eclasses = self.data.get_eclasses()
        scheduled_eclasses = [
            e for e in eclasses.values() if e['status'] == 'scheduled'
        ]
        
        if not scheduled_eclasses:
            await send_success(interaction, "Aucun cours programmé pour le moment.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📚 Cours programmés",
            color=discord.Color.orange()
        )
        
        for eclass in scheduled_eclasses:
            class_datetime = datetime.fromisoformat(eclass['datetime'])
            channel = self.bot.get_channel(eclass['channel_id'])
            embed.add_field(
                name=f"{eclass['title']} (`{eclass['eclass_id']}`)",
                value=(
                    f"📅 {class_datetime.strftime('%d-%m-%Y %H:%M')}\n"
                    f"🔊 {channel.mention if channel else 'Canal inconnu'}\n"
                    f"👨‍🏫 <@{eclass['teacher_id']}>"
                ),
                inline=False
            )
        
        embed.set_footer(text=f"Demandé par {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


    async def track_participants(self, eclass_id: str):
        """Background task to track participants during eclass"""
        while True:
            try:
                await asyncio.sleep(30)
                
                eclass = self.data.get_eclass(eclass_id)
                if not eclass or eclass['status'] != 'ongoing':
                    break
                
                channel = self.bot.get_channel(eclass['channel_id'])
                if channel and isinstance(channel, discord.VoiceChannel):
                    participant_count = len(channel.members)
                    updates = {
                        'current_participants': participant_count,
                        'max_participants': max(eclass['max_participants'], participant_count),
                        'min_participants': min(eclass['min_participants'], participant_count)
                    }
                    self.data.update_eclass(eclass_id, updates)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error tracking participants: {e}")
    
    @tasks.loop(minutes=1)
    async def check_eclass_reminders(self):
        """Check for eclass reminders to send and auto-start classes"""
        now = datetime.now()
        
        for eclass_id, eclass in self.data.get_eclasses().items():
            # Skip if not scheduled
            if eclass['status'] != 'scheduled':
                continue
            
            class_datetime = datetime.fromisoformat(eclass['datetime'])
            time_until_class = class_datetime - now
            
            # Auto-start class at scheduled time
            if timedelta(minutes=-1) <= time_until_class <= timedelta(minutes=1):
                # Update eclass status to ongoing
                updates = {
                    'status': 'ongoing',
                    'started_at': datetime.now().isoformat()
                }
                
                # Get voice channel and count participants
                channel = self.bot.get_channel(eclass['channel_id'])
                if channel and isinstance(channel, discord.VoiceChannel):
                    participant_count = len(channel.members)
                    updates['min_participants'] = participant_count
                    updates['max_participants'] = participant_count
                    updates['current_participants'] = participant_count
                
                self.data.update_eclass(eclass_id, updates)
                
                # Send notification that class has started
                announcement_channel = self.bot.get_channel(eclass['channel_message_id'])
                if announcement_channel:
                    embed = discord.Embed(
                        title="🎓 Le cours a démarré !",
                        description=f"Le cours **{eclass['title']}** vient de commencer !",
                        color=discord.Color.green()
                    )
                    
                    voice_channel = self.bot.get_channel(eclass['channel_id'])
                    if voice_channel:
                        embed.add_field(name="Rejoindre", value=voice_channel.mention, inline=True)
                    
                    await announcement_channel.send(embed=embed)
                
                # Send DM notifications to subscribed users that class has started
                for user_id in eclass['subscribed_users']:
                    try:
                        user = await self.bot.fetch_user(user_id)
                        dm_embed = discord.Embed(
                            title="🎓 Le cours a démarré !",
                            description=f"Le cours **{eclass['title']}** vient de commencer !",
                            color=discord.Color.green()
                        )
                        dm_embed.add_field(
                            name="Matière",
                            value=eclass.get('subject', 'N/A'),
                            inline=True
                        )
                        
                        voice_channel = self.bot.get_channel(eclass['channel_id'])
                        if voice_channel:
                            dm_embed.add_field(name="Rejoindre", value=voice_channel.mention, inline=True)
                        
                        await user.send(embed=dm_embed)
                    except:
                        pass  # User has DMs disabled or other error
                
                # Start tracking participants
                if eclass_id not in self.tracking_tasks or self.tracking_tasks[eclass_id].done():
                    self.tracking_tasks[eclass_id] = self.bot.loop.create_task(
                        self.track_participants(eclass_id)
                    )
                
                continue
            
            # Send reminder 30 minutes before (skip if already notified)
            if eclass['notified']:
                continue
            
            # Notify 30 minutes before
            if timedelta(minutes=29) <= time_until_class <= timedelta(minutes=31):
                self.data.update_eclass(eclass_id, {'notified': True})

                # Send in eclass channel
                channel = self.bot.get_channel(eclass['channel_message_id'])
                if channel:
                    embed = discord.Embed(
                        title="🔔 Rappel cours Horizon",
                        description=f"Le cours **{eclass['title']}** commence dans 30 minutes !",
                        color=discord.Color.orange()
                    )
                    embed.add_field(
                        name="Heure",
                        value=class_datetime.strftime("%d-%m-%Y %H:%M"),
                        inline=True
                    )
                    
                    voice_channel = self.bot.get_channel(eclass['channel_id'])
                    if voice_channel:
                        embed.add_field(name="Lieu", value=voice_channel.mention, inline=True)
                    
                    await channel.send(embed=embed)
                
                
                # Send notifications to subscribed users
                for user_id in eclass['subscribed_users']:
                    try:
                        user = await self.bot.fetch_user(user_id)
                        embed = discord.Embed(
                            title="🔔 Rappel cours Horizon",
                            description=f"Le cours **{eclass['title']}** commence dans 30 minutes !",
                            color=discord.Color.orange()
                        )
                        embed.add_field(
                            name="Heure",
                            value=class_datetime.strftime("%d-%m-%Y %H:%M"),
                            inline=True
                        )
                        
                        channel = self.bot.get_channel(eclass['channel_id'])
                        if channel:
                            embed.add_field(name="Lieu", value=channel.mention, inline=True)
                        
                        await user.send(embed=embed)
                    except:
                        pass  # User has DMs disabled or other error
    
    @check_eclass_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()
    

async def setup(bot):
    await bot.add_cog(EClassCog(bot))
