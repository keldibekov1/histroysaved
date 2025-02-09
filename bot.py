from telethon import TelegramClient, events
import asyncio
import os

# Telegram API ma'lumotlari
api_id =   # O'zingizning API ID'ni kiriting
api_hash = ''  # O'zingizning API Hash'ni kiriting
log_channel = -1002036170298  # O‘zingizning kanal ID'ni kiriting
media_folder = "deleted_media"  # O‘chirilgan media saqlanadigan papka

client = TelegramClient('session_name', api_id, api_hash)

if not os.path.exists(media_folder):
    os.makedirs(media_folder)

saved_messages = {}

@client.on(events.NewMessage)
async def save_message(event):
    """Har bir yangi kelgan xabarni eslab qolish"""
    message_data = {
        "text": event.text,
        "chat_id": event.chat_id,
        "sender_id": event.sender_id,
        "media": None,
        "media_type": None
    }

    if event.media:
        media_type = "file"
        file_extension = "bin"

        if event.photo:
            media_type = "photo"
            file_extension = "jpg"
        elif event.voice:
            media_type = "voice"
            file_extension = "ogg"
        elif event.video_note:
            media_type = "video_note"
            file_extension = "mp4"
        elif event.video:
            media_type = "video"
            file_extension = "mp4"
        elif event.audio:
            media_type = "audio"
            file_extension = "mp3"
            if event.document and event.document.mime_type == "audio/mp4":
                file_extension = "m4a"
        elif event.document:
            media_type = "document"
            file_extension = event.document.attributes[0].file_name.split('.')[-1] if event.document.attributes else "bin"

        file_path = os.path.join(media_folder, f"{event.message.id}.{file_extension}")
        await event.download_media(file_path)
        message_data["media"] = file_path
        message_data["media_type"] = media_type

    saved_messages[event.message.id] = message_data

@client.on(events.MessageDeleted)
async def on_message_deleted(event):
    """O‘chirilgan xabarni kanalga yuborish"""
    for msg_id in event.deleted_ids:
        if msg_id in saved_messages:
            message_data = saved_messages[msg_id]
            sender = await client.get_entity(message_data["sender_id"])

            # Foydalanuvchi yoki kanal nomini olish
            if hasattr(sender, "first_name"):
                profile_name = sender.first_name
            else:
                profile_name = sender.title

            profile_link = f"[{profile_name}](tg://user?id={sender.id})"

            log_text = f"🗑 **Xabar o‘chirildi!**\n\n👤 **Kim:** {profile_link}"
            if message_data["text"]:
                log_text += f"\n📌 **Xabar:** `{message_data['text']}`"

            if message_data["media"] and os.path.exists(message_data["media"]):
                caption = log_text + "\n📂 **Fayl o‘chirildi!**"

                try:
                    await client.send_file(log_channel, message_data["media"], caption=caption, link_preview=False)
                    os.remove(message_data["media"])  # Faylni o‘chiramiz
                except Exception as e:
                    await client.send_message(log_channel, f"⚠️ **Faylni yuborishda xatolik:** `{str(e)}`")
            else:
                await client.send_message(log_channel, log_text, link_preview=False)

            del saved_messages[msg_id]

@client.on(events.MessageEdited)
async def on_message_edited(event):
    """Tahrirlangan xabarni kanalga yuborish"""
    if event.message.id in saved_messages:
        old_text = saved_messages[event.message.id]["text"]
        new_text = event.text  # Yangi matn

        sender = await client.get_entity(saved_messages[event.message.id]["sender_id"])

        # Foydalanuvchi yoki kanal nomini olish
        if hasattr(sender, "first_name"):
            profile_name = sender.first_name
        else:
            profile_name = sender.title

        profile_link = f"[{profile_name}](tg://user?id={sender.id})"

        log_text = (
            f"✏️ **Xabar tahrirlandi!**\n\n"
            f"👤 **Kim:** {profile_link}\n"
            f"📌 **Oldingi matn:** `{old_text}`\n"
            f"🆕 **Yangi matn:** `{new_text}`"
        )
        await client.send_message(log_channel, log_text, link_preview=False)

        saved_messages[event.message.id]["text"] = new_text

async def check_chat_history():
    """Har 30 soniyada chat tarixini tekshirib turish"""
    while True:
        for user_id in list(set([data["sender_id"] for data in saved_messages.values()])):  # Foydalanuvchilar ro‘yxati
            messages = await client.get_messages(user_id, limit=1)  # Oxirgi xabarni tekshirish
            if not messages:  # Agar chat bo‘sh bo‘lsa, tarix tozalangan
                sender = await client.get_entity(user_id)

                if hasattr(sender, "first_name"):
                    profile_name = sender.first_name
                else:
                    profile_name = sender.title

                profile_link = f"[{profile_name}](tg://user?id={sender.id})"

                log_text = f"⚠️ **{profile_link} chat tarixini tozaladi!**"
                await client.send_message(log_channel, log_text, link_preview=False)

                # Lug‘atdan o‘chirish
                for msg_id in list(saved_messages.keys()):
                    if saved_messages[msg_id]["sender_id"] == user_id:
                        del saved_messages[msg_id]

        await asyncio.sleep(30)  # Har 30 soniyada tekshirish

client.loop.create_task(check_chat_history())  # Chatni kuzatishni ishga tushiramiz
client.start()
client.run_until_disconnected()