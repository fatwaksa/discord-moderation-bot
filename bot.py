import discord
from discord.ext import commands, tasks
from datetime import datetime
import os
import random
import asyncio
import json
import atexit

# ------------------------
# Intents المطلوبة
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ------------------------
# قاموس التحذيرات لكل عضو
warnings = {}

# ------------------------
# نظام النقاط
POINTS_FILE = "points.json"
points = {}

def load_points():
    global points
    if os.path.exists(POINTS_FILE):
        with open(POINTS_FILE, "r", encoding="utf-8") as f:
            points = json.load(f)
    else:
        points = {}

def save_points():
    with open(POINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(points, f, ensure_ascii=False, indent=4)

def get_points(guild_id, user_id):
    guild_id = str(guild_id)
    user_id = str(user_id)
    if guild_id not in points:
        points[guild_id] = {}
    if user_id not in points[guild_id]:
        points[guild_id][user_id] = 0
    return points[guild_id][user_id]

def add_points(guild_id, user_id, amount):
    guild_id = str(guild_id)
    user_id = str(user_id)
    if guild_id not in points:
        points[guild_id] = {}
    if user_id not in points[guild_id]:
        points[guild_id][user_id] = 0
    points[guild_id][user_id] += amount
    save_points()

load_points()
atexit.register(save_points)

# ------------------------
# Logging
def create_log_embed(title, description, color=0x00ff00):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return embed

async def log_action(guild, embed):
    log_channel = discord.utils.get(guild.text_channels, name='mod-log')
    if not log_channel:
        log_channel = await guild.create_text_channel('mod-log')
    await log_channel.send(embed=embed)

# ------------------------
# عند تشغيل البوت
@bot.event
async def on_ready():
    print(f'✅ البوت الآن متصل كـ: {bot.user}')
    print(f"📊 تم تحميل نقاط {sum(len(users) for users in points.values())} مستخدم")

# ------------------------
# أوامر الإدارة
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="لم يتم ذكر سبب"):
    if member.guild_permissions.administrator:
        await ctx.send("❌ لا يمكنك طرد الأدمن أو صاحب السيرفر!")
        return
    await member.kick(reason=reason)
    embed = create_log_embed("تم الطرد ✅", f"{member.mention} تم طرده!\nالسبب: {reason}\nبواسطة: {ctx.author.mention}")
    await ctx.send(embed=embed)
    await log_action(ctx.guild, embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="لم يتم ذكر سبب"):
    if member.guild_permissions.administrator:
        await ctx.send("❌ لا يمكنك حظر الأدمن أو صاحب السيرفر!")
        return
    await member.ban(reason=reason)
    embed = create_log_embed("تم الحظر ✅", f"{member.mention} تم حظره!\nالسبب: {reason}\nبواسطة: {ctx.author.mention}")
    await ctx.send(embed=embed)
    await log_action(ctx.guild, embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_name):
    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name == member_name or f"{user.name}#{user.discriminator}" == member_name:
            await ctx.guild.unban(user)
            embed = create_log_embed("تم إلغاء الحظر ✅", f"{user.mention} تم إلغاء حظره!\nبواسطة: {ctx.author.mention}")
            await ctx.send(embed=embed)
            await log_action(ctx.guild, embed)
            return
    await ctx.send(f"❌ لم أتمكن من العثور على المستخدم: {member_name}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount <= 0:
        await ctx.send("❌ الرجاء تحديد عدد أكبر من 0")
        return
    deleted = await ctx.channel.purge(limit=amount)
    embed = create_log_embed("تم حذف الرسائل ✅", f"تم حذف {len(deleted)} رسالة\nبواسطة: {ctx.author.mention}")
    await ctx.send(embed=embed, delete_after=5)
    await log_action(ctx.guild, embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="لم يتم ذكر سبب"):
    if member.guild_permissions.administrator:
        await ctx.send("❌ لا يمكن تحذير الأدمن أو صاحب السيرفر!")
        return
    if member.id not in warnings:
        warnings[member.id] = []
    warnings[member.id].append({'reason': reason, 'by': ctx.author.name, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    
    embed = create_log_embed("تم التحذير ⚠️", f"{member.mention} تم تحذيره!\nالسبب: {reason}\nبواسطة: {ctx.author.mention}")
    await ctx.send(embed=embed)
    await log_action(ctx.guild, embed)
    
    if len(warnings[member.id]) >= 3:
        await member.kick(reason="تجاوز عدد التحذيرات 3")
        embed2 = create_log_embed("تم الطرد تلقائياً ⚠️", f"{member.mention} تم طرده تلقائياً بعد 3 تحذيرات.")
        await ctx.send(embed=embed2)
        await log_action(ctx.guild, embed2)

@bot.command()
@commands.has_permissions(kick_members=True)
async def warnings_list(ctx, member: discord.Member):
    user_warnings = warnings.get(member.id, [])
    if not user_warnings:
        await ctx.send(f"✅ {member.mention} لا يوجد لديه أي تحذيرات.")
        return
    msg = f"⚠️ تحذيرات {member.mention}:\n"
    for i, w in enumerate(user_warnings, 1):
        msg += f"{i}. السبب: {w['reason']} | بواسطة: {w['by']} | في: {w['time']}\n"
    await ctx.send(msg)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not role:
        role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(role, send_messages=False, speak=False)
    await member.add_roles(role)
    embed = create_log_embed("تم كتم العضو 🔇", f"{member.mention} تم كتمه.\nبواسطة: {ctx.author.mention}")
    await ctx.send(embed=embed)
    await log_action(ctx.guild, embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if role in member.roles:
        await member.remove_roles(role)
        embed = create_log_embed("تم فك الكتم 🔊", f"{member.mention} تم فك كتمه.\nبواسطة: {ctx.author.mention}")
        await ctx.send(embed=embed)
        await log_action(ctx.guild, embed)
    else:
        await ctx.send(f"❌ {member.mention} ليس مكتمًا!")

# ------------------------
# XO Games
xo_games = {}

class XOView(discord.ui.View):
    def __init__(self, player1, player2):
        super().__init__(timeout=None)
        self.players = [player1, player2]
        self.current = 0
        self.board = ["⬜"]*9
        self.message = None
        self.add_buttons()
    
    def add_buttons(self):
        for i in range(9):
            self.add_item(discord.ui.Button(label=" ", style=discord.ButtonStyle.secondary, row=i//3, custom_id=str(i)))

    async def interaction_check(self, interaction: discord.Interaction):
        return True

    async def handle_click(self, interaction: discord.Interaction, pos: int):
        if interaction.user != self.players[self.current]:
            await interaction.response.send_message("❌ ليس دورك!", ephemeral=True)
            return
        if self.board[pos] != "⬜":
            await interaction.response.send_message("❌ هذه الخانة مشغولة!", ephemeral=True)
            return

        symbol = "❌" if self.current == 0 else "⭕"
        self.board[pos] = symbol
        self.current = 1 - self.current
        await self.update_buttons()

        winner = await self.check_winner(interaction)
        if winner:
            for child in self.children:
                child.disabled = True
            if winner == "Tie":
                await interaction.response.edit_message(content=f"⚖️ تعادل!\n{''.join(self.board[i] for i in [0,1,2])}\n{''.join(self.board[i] for i in [3,4,5])}\n{''.join(self.board[i] for i in [6,7,8])}", view=self)
            else:
                winner_user = interaction.user
                add_points(interaction.guild.id, winner_user.id, 10)
                await interaction.response.edit_message(content=f"🎉 {winner_user.mention} فاز وحصل على **+10** نقاط! 🏆\n{''.join(self.board[i] for i in [0,1,2])}\n{''.join(self.board[i] for i in [3,4,5])}\n{''.join(self.board[i] for i in [6,7,8])}", view=self)
            del xo_games[interaction.channel.id]
        else:
            await interaction.response.edit_message(content=f"الآن دور: {self.players[self.current].mention}\n{''.join(self.board[i] for i in [0,1,2])}\n{''.join(self.board[i] for i in [3,4,5])}\n{''.join(self.board[i] for i in [6,7,8])}", view=self)

    async def update_buttons(self):
        for i, btn in enumerate(self.children):
            btn.label = self.board[i]

    async def check_winner(self, interaction: discord.Interaction):
        b = self.board
        lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        for i,j,k in lines:
            if b[i] == b[j] == b[k] and b[i] != "⬜":
                return b[i]
        if "⬜" not in b:
            return "Tie"
        return None

@bot.command()
async def xo(ctx, opponent: discord.Member):
    if ctx.author == opponent:
        await ctx.send("❌ لا تلعب مع نفسك!")
        return
    if ctx.channel.id in xo_games:
        await ctx.send("❌ هناك لعبة قائمة بالفعل!")
        return

    view = XOView(ctx.author, opponent)
    board_display = "⬜⬜⬜\n⬜⬜⬜\n⬜⬜⬜"
    message = await ctx.send(f"🎮 لعبة XO بين {ctx.author.mention} (❌) و {opponent.mention} (⭕)\nدور البداية: {ctx.author.mention}\n{board_display}", view=view)
    view.message = message
    xo_games[ctx.channel.id] = view

# ------------------------
# Quiz أسئلة جاهزة
quiz_questions = [
    {"question": "ما عاصمة السعودية؟", "options": ["جدة","الرياض","مكة","الدمام"], "answer": 1},
    {"question": "أكبر كوكب في المجموعة الشمسية؟", "options": ["الأرض","المريخ","المشتري","زحل"], "answer": 2},
    {"question": "ما هو الحيوان الأسرع؟", "options": ["الفهد","الأسد","الذئب","النسور"], "answer": 0},
    {"question": "كم عدد أيام الأسبوع؟", "options": ["5","6","7","8"], "answer": 2},
]

# باقي الألعاب (roll, coin, rpssolo, guess, 8ball) يمكن إضافتها بنفس طريقة الكود السابق

# ------------------------
# أمر المساعدة
@bot.command()
async def help(ctx):
    help_msg = """
📌 **أوامر الإدارة:**
- `!kick @user سبب` → طرد عضو
- `!ban @user سبب` → حظر عضو
- `!unban username#1234` → إلغاء حظر
- `!clear عدد` → حذف رسائل
- `!warn @user سبب` → تحذير عضو
- `!warnings_list @user` → عرض تحذيرات
- `!mute @user` → كتم (نص وصوت)
- `!unmute @user` → فك كتم

📌 **أوامر الألعاب والنقاط:**
- `!roll` → رمية نرد 🎲
- `!coin` → رمية عملة 🪙
- `!xo @user` → لعبة XO (+10 نقاط)
- `!rpssolo` → حجر ورقة مقص ضد البوت (+10 نقاط)
- `!guess` → تخمين رقم (+10 نقاط)
- `!quiz` → كويز عشوائي (+15 نقطة عند الإجابة الصحيحة)
- `!8ball سؤال` → الكرة السحرية 8 🎱
- `!points` → عرض نقاطك 🏆
- `!leaderboard` أو `!top` → أعلى 10 لاعبين في السيرفر
"""
    await ctx.send(help_msg)

# ------------------------
# تشغيل البوت
TOKEN = os.environ.get('TOKEN')
bot.run(TOKEN)
