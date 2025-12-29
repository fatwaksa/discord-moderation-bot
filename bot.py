import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from datetime import datetime
import os
import random
import asyncio
import json

# ------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ------------------------
# نقاط المستخدمين
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

# ------------------------
warnings = {}

# ------------------------
@bot.event
async def on_ready():
    print(f'✅ البوت الآن متصل كـ: {bot.user}')
    print(f"📊 تم تحميل نقاط {sum(len(users) for users in points.values())} مستخدم")

# ------------------------
# Embed للوغ
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
# أوامر النقاط
@bot.command(aliases=['points'])
async def mypoints(ctx):
    pts = get_points(ctx.guild.id, ctx.author.id)
    embed = discord.Embed(title="🏆 نقاطك", color=0x00ff00)
    embed.add_field(name="اللاعب", value=ctx.author.mention, inline=False)
    embed.add_field(name="النقاط", value=f"**{pts}** نقطة", inline=False)
    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=['top', 'lb'])
async def leaderboard(ctx):
    guild_points = points.get(str(ctx.guild.id), {})
    if not guild_points:
        await ctx.send("📭 لا توجد نقاط مسجلة في هذا السيرفر بعد!")
        return
    sorted_players = sorted(guild_points.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title=f"🏆 أعلى 10 لاعبين في {ctx.guild.name}", color=0xffd700)
    ranks = ["🥇","🥈","🥉","🏅","🏅","🏅","🏅","🏅","🏅","🏅"]
    for i, (user_id, pts) in enumerate(sorted_players):
        user = bot.get_user(int(user_id))
        name = user.display_name if user else f"مستخدم غادر ({user_id})"
        embed.add_field(name=f"{ranks[i]} المركز {i+1}", value=f"{name} → **{pts}** نقطة", inline=False)
    await ctx.send(embed=embed)

# ------------------------
# ألعاب بسيطة
@bot.command()
async def roll(ctx):
    number = random.randint(1, 6)
    await ctx.send(f"🎲 {ctx.author.mention} رميت النرد وحصلت على: **{number}**")

@bot.command()
async def coin(ctx):
    side = random.choice(["**رأس** 🪙", "**ذيل** 🪙"])
    await ctx.send(f"🪙 {ctx.author.mention} رميت العملة وطلعت: {side}")

@bot.command()
async def eight_ball(ctx, *, question):
    if not question.endswith("?"):
        await ctx.send("❓ يجب أن يكون سؤالاً!")
        return
    responses = ["نعم بالتأكيد! 👍", "لا أبداً ❌", "ربما... 🤔", "اسأل مرة أخرى لاحقاً ⏳",
                 "الإجابة غير واضحة الآن 🌫️", "من الأفضل ألا أخبرك الآن 😶",
                 "كل الدلائل تشير إلى نعم ✅", "لا تعتمد عليه 🚫"]
    await ctx.send(f"🎱 {ctx.author.mention} سؤالك: {question}\nالإجابة: **{random.choice(responses)}**")

# ------------------------
# الترحيب الذكي واستجابات مخصصة
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()
    # الترحيب
    if content in ["تمرة", "تمره", "tmrh", "tmrh"]:
        await message.channel.send(f"👋 أهلاً وسهلاً {message.author.mention}!")

    # استجابات مخصصة
    if "صدام حسين" in content:
        await message.channel.send("نعم ابو عداي")
    if "اطلق قرار الحكم" in content:
        await message.channel.send(f"⚖️ نطلق قرار الحكم على المدعي {message.author.mention}!")

    await bot.process_commands(message)

# ------------------------
# تشغيل البوت
TOKEN = os.environ.get('TOKEN')
bot.run(TOKEN)
