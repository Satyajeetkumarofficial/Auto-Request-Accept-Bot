from bot import Bot 
from pyrogram import Client, filters 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, Message, ChatJoinRequest 
from config import LOGGER, OWNER_ID
logger = LOGGER("auto_accept.py")



@Bot.on_chat_join_request(filters.group | filters.channel)
async def auto_accept(client: Bot, message: ChatJoinRequest):
    chat, user = message.chat, message.from_user
    
    # remove those two when public the repo
    LOGGER.info(f"{'@' + user.username if user.username else user.user_id} Joined {chat.title} in {chat.id} with id: {user.id}") 
    await client.send_message(chat_id=OWNER_ID, text=f"{user.mention}!\n\n Joined {chat.title} ID:{chat.id} USER ID:{user.id}")
    # accept request
    await client.approve_chat_join_request(chat_id=chat.id, user_id=user.id)
    
    # generate invite link 
    try:
      invite_link = await client.export_chat_invite_link(chat.id) 
    except Exception:
      invite_link = f"https://t.me/{chat.username}" if chat.username else None
    
    
    
    # channel buttons
    buttons = None
    if invite_link:
      buttons = InlineKeyboardMarkup([
        [
          InlineKeyboardButton("🧭 Vɪsɪᴛ Vʜᴀɴɴᴇʟ", url=invite_link)
        ]
      ]) if invite_link else None
    
    
    await client.send_message(
      chat_id=user.id,
      text=f"Wᴇʟᴄᴏᴍᴇ, {user.mention}!\n\nYᴏᴜʀ ʀʀᴇsᴘᴇᴄᴛᴇᴅ ʀᴇǫᴜᴇsᴛ ᴏғ ᴊᴏɪɴɪɴɢ {chat.title} ʜᴀs ʙᴇᴇɴ ᴀʟʀᴇᴀᴅʏ ᴀᴄᴄᴇᴘᴛᴇᴅ.",
      reply_markup=buttons,
    ) 