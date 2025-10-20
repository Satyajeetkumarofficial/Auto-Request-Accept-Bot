from database.database import del_user, get_all_users
import asyncio
import config
from pyrogram import Client, filters
from bot import Bot 
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from motor.motor_asyncio import AsyncIOMotorClient 

broadcast_cache = {}

@Bot.on_message(filters.incoming & filters.private & filters.user(config.OWNER_ID))
async def broadcast_handler(client: Bot, message): 
    # ignore commands
    if message.text and message.text.startswith("/"):
        return 

    broadcast_cache[message.from_user.id] = message 

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ʙʀᴏᴀᴅᴄᴀsᴛ", callback_data="confirm"),
            InlineKeyboardButton("ᴄᴀɴᴄᴇʟ", callback_data="cancel")
        ]
    ])

    await message.reply_text(
        "ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʙʀᴏᴀᴅᴄᴀsᴛ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴛᴏ ᴀʟʟ ᴜsᴇʀs?",
        reply_markup=keyboard
    )

# handle confirm or cancel callback 
@Bot.on_callback_query(filters.regex("^(confirm|cancel)$")) 
async def confirm(client: Bot, query: CallbackQuery):

    # ------ Confirm -------#
    if query.data == "confirm":
        msg = broadcast_cache.get(query.from_user.id) 

        if not msg:
            return await query.answer("sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ! ɴᴏ ᴍᴇssᴀɢᴇ ғᴏᴜɴᴅ:(", show_alert=True) 

        await query.answer("ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ...", show_alert=False) 

        try:
            await start_broadcast(client, query.message, msg)
        finally:
            broadcast_cache.pop(query.from_user.id, None)

    # ------- Cancel --------#
    elif query.data == "cancel":
        broadcast_cache.pop(query.from_user.id, None) 
        try:
            await query.message.delete()
        except Exception:
            pass

# ------ Main Broadcast Func (Optimized with async batches) ------- # 
async def start_broadcast(client: Bot, status_msg, broadcast_msg):
    users = await get_all_users() 
    total_users = len(users) 

    total = successful = blocked = deleted = failed = 0 
    start_time = asyncio.get_event_loop().time() 

    # ------ Live Status Update Loop ------- #
    async def edit_status():
        nonlocal total, successful, blocked, deleted, failed
        while total < total_users:
            try:
                await status_msg.edit_text(
                    f"<blockquote><b>ʙʀᴏᴀᴅᴄᴀsᴛ ᴏɴɢᴏɪɴɢ</b></blockquote>\n" 
                    f"ᴛᴏᴛᴀʟ ᴜsᴇʀs: <code>{total_users}</code>\n"
                    f"sᴜᴄᴄᴇssғᴜʟ: <code>{successful}</code>\n"
                    f"ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs: <code>{blocked}</code>\n"
                    f"ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs: <code>{deleted}</code>\n"
                    f"ᴜɴsᴜᴄᴄᴇssғᴜʟ: <code>{failed}</code>\n"
                    f"ᴏᴜᴛ ᴏғ: <b>{total_users}/{total}</b>\n",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass 
            await asyncio.sleep(3)

    updater_task = asyncio.create_task(edit_status()) 

    # ------ Send Broadcast in Async Batches ------- #
    batch_size = 20  # number of users to send in parallel
    for i in range(0, total_users, batch_size):
        batch = users[i:i + batch_size]

        async def send_user(user_id):
            nonlocal total, successful, blocked, deleted, failed
            try:
                await broadcast_msg.copy(user_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await broadcast_msg.copy(user_id)
                    successful += 1
                except Exception:
                    failed += 1
            except UserIsBlocked:
                await del_user(user_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(user_id)
                deleted += 1
            except:
                failed += 1
            total += 1

        await asyncio.gather(*[send_user(u) for u in batch])
        await asyncio.sleep(0.05)  # small delay between batches

    updater_task.cancel()
    try:
        await updater_task
    except asyncio.CancelledError:
        pass

    # ------ Final Summary ------- #
    duration = round(asyncio.get_event_loop().time() - start_time, 1) 

    summery = f"""
    <blockquote><b>ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b></blockquote>
    <b>sᴜᴄᴄᴇssғᴜʟ:</b> <code>{successful}</code>
    <b>ʙʟᴏᴄᴋᴇᴅ ᴜsᴇʀs:</b> <code>{blocked}</code>
    <b>ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛs:</b> <code>{deleted}</code>
    <b>ᴜɴsᴜᴄᴄᴇssғᴜʟ:</b> <code>{failed}</code>
    <b>⏱ ᴅᴜʀᴀᴛɪᴏɴ:</b> <code>{duration}</code>
    """ 

    await status_msg.edit_text(summery, parse_mode=ParseMode.HTML)