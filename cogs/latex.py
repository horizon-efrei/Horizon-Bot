"""
LaTeX Cog
Handles LaTeX to image conversion using Matplotlib
"""
import discord
from discord.ext import commands
from discord import app_commands
import matplotlib.pyplot as plt
import matplotlib
import io

# Use non-interactive backend
matplotlib.use('Agg')
matplotlib.rcParams["mathtext.fontset"] = "cm"
plt.rcParams['text.usetex'] = True
plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath}\usepackage{amssymb}\usepackage{amsfonts}'

class LaTeXCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="latex", description="Convertis une chaîne LaTeX en image")
    @app_commands.describe(code="La chaîne LaTeX à convertir")
    async def latex_to_image(self, interaction: discord.Interaction, code: str):
        # Check if code is too long
        if len(code) > 2000:
            await interaction.response.send_message(
                "❌ Le code LaTeX est trop long (max 2000 caractères).",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Create figure with white background - will be cropped to content
            fig = plt.figure(figsize=(1, 1), facecolor='white', dpi=200)
            ax = fig.add_subplot(111)
            ax.axis('off')
            
            # Render LaTeX with proper formatting
            # Check if code uses environments like \begin{...} or \[...\]
            if '\\begin{' in code or '\\[' in code or '\\]' in code:
                # Remove equation numbering by converting equation to equation*
                latex_text = code.replace('\\begin{equation}', '\\begin{equation*}')
                latex_text = latex_text.replace('\\end{equation}', '\\end{equation*}')
                latex_text = latex_text.replace('\\begin{align}', '\\begin{align*}')
                latex_text = latex_text.replace('\\end{align}', '\\end{align*}')
                
                # Wrap aligned/gathered environments in display math if not already wrapped
                if '\\begin{aligned}' in latex_text or '\\begin{gathered}' in latex_text:
                    if not latex_text.startswith('$') and '\\[' not in latex_text:
                        latex_text = f'$${latex_text}$$'
                # If \[...\] is present, don't add any wrapping (it's already display math)
            elif not code.startswith('$'):
                # Add $ for inline math if not already present
                latex_text = f'${code}$'
            else:
                latex_text = code
            
            # Render the LaTeX text
            ax.text(
                0.5, 0.5, latex_text,
                fontsize=20,
                ha='center',
                va='center',
                color='black',
                transform=ax.transAxes
            )
            
            # Draw to calculate the text size
            fig.canvas.draw()
            
            # Save to buffer with tight bounding box (auto-adjusts to content)
            buf = io.BytesIO()
            plt.savefig(
                buf,
                format='png',
                dpi=200,
                bbox_inches='tight',
                pad_inches=0.05,  # Minimal padding around the image
                facecolor='white',
                edgecolor='none'
            )
            buf.seek(0)
            
            # Check file size (Discord limit is 8MB for regular users, 25MB for nitro)
            file_size = buf.tell()
            buf.seek(0)
            
            if file_size > 8 * 1024 * 1024:  # 8MB
                plt.close(fig)
                await interaction.followup.send(
                    "❌ L'image générée est trop grande (> 8MB). Essayez de simplifier votre formule.",
                    ephemeral=True
                )
                return
            
            plt.close(fig)
            
            # Create Discord file
            file = discord.File(buf, filename='latex.png')
            
            embed = discord.Embed(
                title="Rendu LaTeX",
                color=discord.Color.orange()
            )
            embed.set_image(url="attachment://latex.png")
            embed.set_footer(text=f"Demandé par {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, file=file)

        except RuntimeError as e:
            # Handle LaTeX compilation errors
            error_msg = str(e)
            if "latex was not able to process" in error_msg:
                await interaction.followup.send(
                    "❌ Erreur de compilation LaTeX.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Erreur : {error_msg[:500]}",
                    ephemeral=True
                )
        except Exception as e:
            error_msg = str(e)
            # Truncate error message if too long
            if len(error_msg) > 1500:
                error_msg = error_msg[:1500] + "..."
            await interaction.followup.send(
                f"❌ Erreur lors de la génération de l'image LaTeX : {error_msg}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(LaTeXCog(bot))
