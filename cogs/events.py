"""
Events Cog
Handles bot events like messages and reactions
"""
from discord.ext import commands

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = bot.data_manager
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Track messages for statistics"""
        if message.author.bot:
            return
        
        # Track messages
        self.data.increment_message_count(message.created_at)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle eclass subscription reactions"""
        if payload.user_id == self.bot.user.id:
            return
        
        message_id = payload.message_id
        eclass = self.data.get_eclass_by_message_id(message_id)
        
        if eclass and str(payload.emoji) == "🔔":
            if payload.user_id not in eclass['subscribed_users']:
                eclass['subscribed_users'].append(payload.user_id)
                self.data.update_eclass(eclass['eclass_id'], {'subscribed_users': eclass['subscribed_users']})
                
                # Send confirmation DM
                try:
                    user = await self.bot.fetch_user(payload.user_id)
                    await user.send(
                        f"✅ Vous êtes abonné aux notifications pour le cours : **{eclass['title']}**\n"
                        f"Vous serez notifié 30 minutes avant le début !"
                    )
                except:
                    pass  # User has DMs disabled
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle eclass unsubscription reactions"""
        message_id = payload.message_id
        eclass = self.data.get_eclass_by_message_id(message_id)
        
        if eclass and str(payload.emoji) == "🔔":
            if payload.user_id in eclass['subscribed_users']:
                eclass['subscribed_users'].remove(payload.user_id)
                self.data.update_eclass(eclass['eclass_id'], {'subscribed_users': eclass['subscribed_users']})

async def setup(bot):
    await bot.add_cog(EventsCog(bot))
