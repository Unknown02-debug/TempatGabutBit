import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

# Ambil token dari Koyeb (biar aman)
API_TOKEN = os.getenv("BOT_TOKEN")
if not API_TOKEN:
    print("ERROR: BOT_TOKEN belum di set di Koyeb!")
    exit()

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Data disimpan di memory (cukup untuk Koyeb)
waiting_user = None  # orang yang lagi nunggu
chats = {}  # pasangan yang lagi ngobrol {user_id: partner_id}

@dp.message(Command("start"))
async def start_cmd(message: Message):
    global waiting_user
    user_id = message.from_user.id

    if user_id in chats:
        await message.answer("Kamu sedang dalam obrolan. Ketik /stop untuk berhenti, /next untuk cari teman baru.")
        return

    if waiting_user and waiting_user != user_id:
        # KETEMU TEMAN!
        partner_id = waiting_user
        chats[user_id] = partner_id
        chats[partner_id] = user_id
        waiting_user = None
        
        await bot.send_message(user_id, "✅ Teman obrolan ditemukan! Chat kamu sekarang diteruskan. Ketik /stop untuk berhenti, /next untuk ganti teman.")
        await bot.send_message(partner_id, "✅ Teman obrolan ditemukan! Chat kamu sekarang diteruskan. Ketik /stop untuk berhenti, /next untuk ganti teman.")
    else:
        waiting_user = user_id
        await message.answer("🔍 Mencari teman obrolan acak... Mohon tunggu sejenak.\n\nAda 1 orang menunggu (kamu). Ajak temanmu pencet /start juga biar langsung ketemu!")

@dp.message(Command("stop"))
async def stop_cmd(message: Message):
    global waiting_user
    user_id = message.from_user.id
    
    if user_id == waiting_user:
        waiting_user = None
        await message.answer("❌ Pencarian dibatalkan. Klik /start untuk cari lagi.")
        return

    if user_id in chats:
        partner_id = chats[user_id]
        del chats[user_id]
        if partner_id in chats:
            del chats[partner_id]
        await message.answer("✅ Obrolan diakhiri. Klik /start untuk cari teman baru.")
        await bot.send_message(partner_id, "❌ Teman obrolanmu telah mengakhiri chat. Klik /start untuk cari teman baru.")
    else:
        await message.answer("Anda belum terhubung dengan siapapun. Klik /start untuk mulai.")

@dp.message(Command("next"))
async def next_cmd(message: Message):
    await stop_cmd(message)
    await start_cmd(message)

@dp.message(F.text)
async def chat_handler(message: Message):
    user_id = message.from_user.id
    if user_id in chats:
        partner_id = chats[user_id]
        try:
            await bot.send_message(partner_id, message.text)
        except:
            await message.answer("Gagal mengirim pesan, temanmu mungkin sudah keluar. /start lagi ya.")
    else:
        # Kalau belum ada teman, jangan diteruskan
        if message.text not in ["/start", "/stop", "/next"]:
            await message.answer("Anda sedang tidak berada dalam obrolan. Klik /start untuk mencari teman.")

async def main():
    print("Bot Tempat Gabut jalan...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())