from bot import Bot
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from database.database import get_all_users
from config import OWNER_ID

# --- /users command --- #
@Bot.on_message(filters.command("users") & filters.private & filters.user(OWNER_ID))
async def list_users(client: Bot, message: Message):
    users = await get_all_users()
    total_users = len(users)

    if total_users == 0:
        await message.reply_text("No users found in database.")
        return

    reply_text = f"**Total Users:** {total_users}\n\n"
    
    for idx, user_id in enumerate(users, 1):
        try:
            user = await client.get_users(user_id)  # Fetch current Telegram info
            reply_text += f"{idx}. {user.mention} ID: {user.id}\n"
        except Exception:
            reply_text += f"{idx}. User ID: {user_id} (Cannot fetch info)\n"

    # Send as multiple messages if too long
    if len(reply_text) > 4000:
        for i in range(0, len(reply_text), 4000):
            await message.reply_text(reply_text[i:i+4000], parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)


# --- /sendMessage <user_id> <message> --- #
@Bot.on_message(filters.command("sendMessage") & filters.private & filters.user(OWNER_ID))
async def send_to_user(client: Bot, message: Message):
    if len(message.command) < 3:
        await message.reply_text("Usage: /sendMessage <user_id> <message>")
        return

    user_id = int(message.command[1])
    msg_to_send = " ".join(message.command[2:])

    try:
        await client.send_message(chat_id=user_id, text=msg_to_send)
        await message.reply_text(f"✅ Message sent to user ID: {user_id}")
    except Exception as e:
        await message.reply_text(f"❌ Failed to send message: {e}")