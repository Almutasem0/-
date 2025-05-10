import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio

# تحميل المتغيرات من ملف .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SUPPORT_CATEGORY_ID = int(os.getenv("SUPPORT_CATEGORY_ID", "0"))
TICKET_CHANNEL_ID = int(os.getenv("TICKET_CHANNEL_ID", "0"))
SUPPORT_ROLE_ID = int(os.getenv("SUPPORT_ROLE_ID", "0"))  # معرف رتبة الدعم

# إعداد البوت
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# قاموس لتخزين معلومات التذاكر
tickets = {}

# حدث عند تشغيل البوت
@bot.event
async def on_ready():
    print(f'تم تسجيل الدخول باسم {bot.user}')
    print(f'ID البوت: {bot.user.id}')
    print('------')
    
    # إنشاء زر التذاكر
    channel = bot.get_channel(TICKET_CHANNEL_ID)
    if channel:
        await create_ticket_button(channel)

# دالة إنشاء زر التذاكر
async def create_ticket_button(channel):
    embed = discord.Embed(
        title="🎫 الدعم الفني",
        description="اضغط على الزر أدناه لإنشاء تذكرة جديدة",
        color=discord.Color.blue()
    )
    class TicketButton(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
        
        @discord.ui.button(label="إنشاء تذكرة", style=discord.ButtonStyle.green, emoji="🎫")
        async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
            # التحقق من عدم وجود تذكرة مفتوحة
            if interaction.user.id in tickets:
                await interaction.response.send_message("❌ لديك تذكرة مفتوحة بالفعل!", ephemeral=True)
                return

            # إنشاء روم التذكرة
            category = bot.get_channel(SUPPORT_CATEGORY_ID)
            if not category:
                await interaction.response.send_message("❌ لم يتم العثور على فئة التذاكر!", ephemeral=True)
                return

            # إنشاء الروم
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            channel = await interaction.guild.create_text_channel(
                f"ticket-{interaction.user.name}",
                category=category,
                overwrites=overwrites
            )

            # حفظ معلومات التذكرة
            tickets[interaction.user.id] = {
                "channel_id": channel.id,
                "created_at": datetime.now(),
                "status": "open"
            }

            # إرسال رسالة الترحيب
            support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
            support_mention = support_role.mention if support_role else "فريق الدعم"
            
            embed = discord.Embed(
                title="تذكرة جديدة",
                description=f"مرحباً {interaction.user.mention}!\n{support_mention} سيتم الرد عليك قريباً.",
                color=discord.Color.green()
            )
            
            # إضافة أزرار التحكم
            class TicketControls(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)
                
                @discord.ui.button(label="إغلاق التذكرة", style=discord.ButtonStyle.red, emoji="🔒")
                async def close_ticket(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if not button_interaction.user.guild_permissions.manage_channels:
                        await button_interaction.response.send_message("❌ ليس لديك الصلاحية لإغلاق هذه التذكرة!", ephemeral=True)
                        return
                    
                    await button_interaction.response.send_message("🔒 جاري إغلاق التذكرة...")
                    await asyncio.sleep(5)
                    await channel.delete()
                    del tickets[interaction.user.id]
            
            await channel.send(embed=embed, view=TicketControls())
            await interaction.response.send_message(f"✅ تم إنشاء تذكرتك في {channel.mention}", ephemeral=True)

    # إرسال رسالة الزر
    await channel.send(embed=embed, view=TicketButton())

# أمر إعادة إنشاء زر التذاكر
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await create_ticket_button(ctx.channel)
    await ctx.send("✅ تم إنشاء زر التذاكر!")

# أمر إغلاق التذكرة
@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ هذا الأمر يمكن استخدامه فقط في روم التذكرة!")
        return

    await ctx.send("🔒 جاري إغلاق التذكرة...")
    await asyncio.sleep(5)
    await ctx.channel.delete()

# أمر إضافة عضو للتذكرة
@bot.command()
@commands.has_permissions(manage_channels=True)
async def add(ctx, member: discord.Member):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ هذا الأمر يمكن استخدامه فقط في روم التذكرة!")
        return

    await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
    await ctx.send(f"✅ تم إضافة {member.mention} إلى التذكرة")

# أمر إزالة عضو من التذكرة
@bot.command()
@commands.has_permissions(manage_channels=True)
async def remove(ctx, member: discord.Member):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ هذا الأمر يمكن استخدامه فقط في روم التذكرة!")
        return

    await ctx.channel.set_permissions(member, read_messages=False, send_messages=False)
    await ctx.send(f"✅ تم إزالة {member.mention} من التذكرة")

# أمر تغيير اسم التذكرة
@bot.command()
@commands.has_permissions(manage_channels=True)
async def rename(ctx, *, new_name: str):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ هذا الأمر يمكن استخدامه فقط في روم التذكرة!")
        return

    await ctx.channel.edit(name=f"ticket-{new_name}")
    await ctx.send(f"✅ تم تغيير اسم التذكرة إلى `ticket-{new_name}`")

# أمر نقل التذكرة
@bot.command()
@commands.has_permissions(manage_channels=True)
async def move(ctx, category: discord.CategoryChannel):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ هذا الأمر يمكن استخدامه فقط في روم التذكرة!")
        return

    await ctx.channel.edit(category=category)
    await ctx.send(f"✅ تم نقل التذكرة إلى {category.name}")

# أمر معلومات التذكرة
@bot.command()
async def ticketinfo(ctx):
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ هذا الأمر يمكن استخدامه فقط في روم التذكرة!")
        return

    # البحث عن معلومات التذكرة
    ticket_info = None
    for user_id, info in tickets.items():
        if info["channel_id"] == ctx.channel.id:
            ticket_info = info
            ticket_owner = user_id
            break

    if not ticket_info:
        await ctx.send("❌ لم يتم العثور على معلومات التذكرة!")
        return

    owner = await bot.fetch_user(ticket_owner)
    created_at = ticket_info["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    
    embed = discord.Embed(
        title="معلومات التذكرة",
        color=discord.Color.blue()
    )
    embed.add_field(name="صاحب التذكرة", value=owner.mention, inline=True)
    embed.add_field(name="تاريخ الإنشاء", value=created_at, inline=True)
    embed.add_field(name="الحالة", value=ticket_info["status"], inline=True)
    
    await ctx.send(embed=embed)

# أمر المساعدة
@bot.command(name="commands")
async def show_commands(ctx):
    help_text = """
**قائمة الأوامر المتاحة:**

**أوامر الإدارة:**
`!close` - إغلاق التذكرة
`!add [عضو]` - إضافة عضو للتذكرة
`!remove [عضو]` - إزالة عضو من التذكرة
`!rename [اسم جديد]` - تغيير اسم التذكرة
`!move [فئة]` - نقل التذكرة إلى فئة أخرى
`!ticketinfo` - عرض معلومات التذكرة
`!setup` - إعادة إنشاء زر التذاكر (للمالك فقط)
`!commands` - عرض هذه القائمة

**ملاحظة:** جميع أوامر الإدارة تتطلب صلاحيات إدارية
"""
    await ctx.send(help_text)
# ... existing code ...

# Add this to your environment variables section
TICKET_LOG_CHANNEL_ID = int(os.getenv("TICKET_LOG_CHANNEL_ID", "0"))  # معرف روم سجل التذاكر
TICKET_CLOSE_ROLE_ID = int(os.getenv("TICKET_CLOSE_ROLE_ID", "0"))  # معرف رتبة إغلاق التذاكر

# ... existing code ...

# Modify the TicketControls class in the create_ticket_button function
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="إغلاق التذكرة", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_ticket(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        # التحقق من الرتبة
        close_role = discord.Interaction.guild.get_role(TICKET_CLOSE_ROLE_ID)
        if not close_role or close_role not in button_interaction.user.roles:
            await button_interaction.response.send_message("❌ فقط الأعضاء الذين لديهم رتبة إغلاق التذاكر يمكنهم إغلاق التذكرة!", ephemeral=True)
            return
        
        await button_interaction.response.send_message("🔒 جاري إغلاق التذكرة...")
        
        # إنشاء سجل التذكرة
        log_channel = discord.Interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            # جمع محتوى التذكرة
            messages = []
            async for message in discord.ChannelType.history(limit=None, oldest_first=True):
                messages.append(f"{message.author.name}: {message.content}")
            
            # إنشاء embed للسجل
            log_embed = discord.Embed(
                title=f"سجل التذكرة: {discord.ChannelType.name}",
                description="\n".join(messages),
                color=discord.Color.blue()
            )
            log_embed.add_field(name="تم الإغلاق بواسطة", value=button_interaction.user.mention)
            log_embed.add_field(name="تاريخ الإغلاق", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            await log_channel.send(embed=log_embed)
        
        await asyncio.sleep(5)
        await discord.ChannelType.delete()
        del tickets[discord.Interaction.user.id]
    
    @discord.ui.button(label="حذف التذكرة", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_ticket(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        if not button_interaction.user.guild_permissions.administrator:
            await button_interaction.response.send_message("❌ فقط الإدارة يمكنها حذف التذاكر!", ephemeral=True)
            return
        
        await button_interaction.response.send_message("🗑️ جاري حذف التذكرة...")
        await asyncio.sleep(5)
        await discord.ChannelType.delete()
        del tickets[discord.Interaction.user.id]

# ... existing code ...
# تشغيل البوت
if __name__ == "__main__":
    if not TOKEN:
        print("❌ لم يتم العثور على توكن البوت في ملف .env")
        exit(1)
    print("🚀 جاري تشغيل البوت...")
    bot.run(TOKEN)