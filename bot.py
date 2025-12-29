# bot.py
import discord
from discord.ext import commands, tasks
from datetime import datetime
import os

# ------------------------
# Intents المطلوبة
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ------------------------
# قاموس التحذيرات لكل عضو
warnings = {}

# ------------------------
# عند تشغيل البوت
@bot.event
async def on_ready():
    print(f'✅ البوت الآن متصل كـ: {bot.user}')

# ------------------------
# دالة لإنشاء Embed للوغ
def create_log_embed(title, description, color=0x00ff00):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return embed

# ------------------------
# دالة للوغ
async def log_action(guild, embed):
    log_channel = discord.utils.get(guild.text_channels, name='mod-log')
    if not log_channel:
        log_channel = await guild.create_text_channel('mod-log')
    await log_channel.send(embed=embed)

# ------------------------
# أمر طرد عضو
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

# ------------------------
# أمر حظر عضو
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

# ------------------------
# أمر الغاء الحظر
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

# ------------------------
# أمر حذف رسائل
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

# ------------------------
# أمر تحذير عضو
@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="لم يتم ذكر سبب"):
    if member.guild_permissions.administrator:
        await ctx.send("❌ لا يمكن تحذير الأدمن أو صاحب السيرفر!")
        return
    if member.id not in warnings:
        warnings[member.id] = []
    warnings[member.id].append({'reason': reason, 'by': ctx.author.name, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    
    # إرسال تحذير
    embed = create_log_embed("تم التحذير ⚠️", f"{member.mention} تم تحذيره!\nالسبب: {reason}\nبواسطة: {ctx.author.mention}")
    await ctx.send(embed=embed)
    await log_action(ctx.guild, embed)
    
    # طرد تلقائي إذا تجاوز 3 تحذيرات
    if len(warnings[member.id]) >= 3:
        await member.kick(reason="تجاوز عدد التحذيرات 3")
        embed2 = create_log_embed("تم الطرد تلقائياً ⚠️", f"{member.mention} تم طرده تلقائياً بعد 3 تحذيرات.")
        await ctx.send(embed=embed2)
        await log_action(ctx.guild, embed2)

# ------------------------
# عرض التحذيرات
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

# ------------------------
# أمر كتم عضو (نص)
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

# ------------------------
# أمر فك الكتم
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
# أمر مساعدة عربي
@bot.command()
async def help(ctx):
    help_msg = """
📌 **أوامر الإدارة:**
- `!kick @user سبب` → لطرد عضو.
- `!ban @user سبب` → لحظر عضو.
- `!unban username#1234` → لإلغاء حظر عضو.
- `!clear عدد` → حذف عدد من الرسائل.
- `!warn @user سبب` → لتحذير عضو.
- `!warnings_list @user` → عرض تحذيرات عضو.
- `!mute @user` → كتم العضو (نص وصوت).
- `!unmute @user` → فك الكتم.
"""
    await ctx.send(help_msg)

# ------------------------
# تشغيل البوت
TOKEN = os.environ.get('TOKEN')  # ضع توكن البوت هنا إذا لم تستخدم متغير البيئة
bot.run(TOKEN)
