from database.database import del_user, get_all_users
import asyncio
import config 
from config import LOGGER
from pyrogram import Client, filters
from bot import Bot 
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, RPCError
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
from motor.motor_asyncio import AsyncIOMotorClient 

broadcast_cache = {}

@Bot.on_message(filters.incoming & filters.private & filters.user(config.OWNER_ID) & ~filters.command(["start", "report", "sendmessage", "users"]))
async def broadcast_handler(client: Bot, message): 
    '''# ignore messages from the owner (safety)
    if message.from_user.id == config.OWNER_ID:
        return'''

    broadcast_cache[message.from_user.id] = message 

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ʙʀᴏᴀᴅᴄᴀsᴛ", callback_data="broadcast")
        ],
        [
            InlineKeyboardButton("ᴘɪɴ-ᴄᴀsᴛ", callback_data="pbroadcast"),
            InlineKeyboardButton("ᴅᴇʟ-ᴄᴀsᴛ", callback_data="dbroadcast")
        ],
        [
            InlineKeyboardButton("ᴄᴀɴᴄᴇʟ", callback_data="cancel")
        ]
        
    ])

    await message.reply_text(
        "ꜱᴇʟᴇᴄᴛ ᴏɴᴇ ᴏꜰ ᴛʜᴇᴍ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ ᴡɪᴛʜ ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴛʜᴇ ᴍᴇssᴀɢᴇ.",
        reply_markup=keyboard
    )

# handle confirm or cancel callback 
@Bot.on_callback_query(filters.regex("^(broadcast|cancel|pbroadcast|dbroadcast)$")) 
async def confirm(client: Bot, query: CallbackQuery):

    msg = broadcast_cache.get(query.from_user.id) 

    if not msg:
        return await query.answer("sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ! ɴᴏ ᴍᴇssᴀɢᴇ ғᴏᴜɴᴅ:(", show_alert=True) 

    # ------ Confirm -------#
    try:
        if query.data == "broadcast":
            await query.answer("ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ...", show_alert=False) 

            try:
                await start_broadcast(client, query.message, msg)
            finally:
                broadcast_cache.pop(query.from_user.id, None) 
    except Exception as e:
        await query.message.reply_text(f"ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")


    
    try:
        # ------ Pin Broadcast --------#
        if query.data == "pbroadcast":
            try:
                await start_broadcast(client, query.message, msg, pin=True)
            finally:
                broadcast_cache.pop(query.from_user.id, None)
        
            #await query.message.reply_text("sᴇɴᴅ ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴇssᴀɢᴇ .") 
    except Exception as e:
        await query.message.reply_text(f"ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")


    try:
        # ------ Delete Broadcast --------#
        if query.data == "dbroadcast":
            try:
                await start_broadcast(client, query.message, msg, delete_after=config.BROADCAST_DELETE_TIME)
            finally:
                broadcast_cache.pop(query.from_user.id, None)
        
            await query.message.reply_text(f"ʙʀᴏᴀᴅᴄᴀꜱᴛ ᴍᴇꜱꜱᴀɢᴇ ᴀʟʀᴇᴀᴅʏ ꜱᴇɴᴛ, ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ - {config.BROADCAST_DELETE_TIME}") 
    except Exception as e:
        await query.message.reply_text(f"ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")



    try:
        # ------- Cancel --------#
        if query.data == "cancel":
            broadcast_cache.pop(query.from_user.id, None) 
            try:
                await query.message.delete()
            except Exception:
                pass 
            await query.answer("ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴀɴᴄᴇʟʟᴇᴅ.", show_alert=True)
    except Exception as e:
        await query.message.reply_text(f"ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")




# ------ Main Broadcast Func (Optimized with async batches) ------- # 
async def start_broadcast(client: Bot, status_msg, broadcast_msg, pin=False, delete_after=None):
    users = [u for u in await get_all_users() if u != config.OWNER_ID] 
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
                sent_msg = await broadcast_msg.copy(user_id) 
                if pin:
                    await client.pin_chat_message(
                        chat_id=user_id,
                        message_id=sent_msg.id,
                        both_sides=True
                    )
                if delete_after:
                    asyncio.create_task(delete_later(sent_msg, delete_after))
                successful += 1
            except FloodWait as e: 
                await asyncio.sleep(e.value) 
                try:
                    sent_msg = await broadcast_msg.copy(user_id)
                    if pin:
                        await client.pin_chat_message(
                            chat_id=user_id,
                            message_id=sent_msg.id,
                            both_sides=True
                        )
                    if delete_after:
                        asyncio.create_task(delete_later(sent_msg, delete_after)) 
                    successful += 1 
                except Exception as e:
                    failed += 1
                    LOGGER(__name__).error(f"Failed to send broadcast to {user_id} after FloodWait: {e}")
            except UserIsBlocked:
                await del_user(user_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(user_id)
                deleted += 1 
            except RPCError as e:
                failed += 1 
                LOGGER(__name__).error(f"RPCError while sending broadcast to {user_id}")
            except Exception as e:
                failed += 1 
                LOGGER(__name__).error(f"Unexpected error while sending broadcast to {user_id}: {e}") 
            finally:
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


async def delete_later(msg, seconds):
    await asyncio.sleep(seconds) 
    try:
        await msg.delete() 
    except Exception as e:
        pass