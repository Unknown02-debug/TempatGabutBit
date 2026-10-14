import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ---------------------------------------------------------
# SETUP & KONFIGURASI
# ---------------------------------------------------------
API_TOKEN = "8842150612:AAEV61j3-U4KbTf1b6BrV_0vWbHk8Uyb200"  # Ganti dengan token dari BotFather

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ---------------------------------------------------------
# PENYIMPANAN DATA SEMENTARA (In-Memory Data Structures)
# ---------------------------------------------------------
# Menyimpan profil pengguna: {user_id: {"age": "...", "gender": "...", "region": "..."}}
user_profiles = {}

# Menyimpan pasangan yang sedang ngobrol: {user_id: partner_id}
active_chats = {}

# Antrean pengguna yang sedang mencari pasangan acak: [user_id_1, user_id_2, ...]
waiting_queue = []

# State untuk pengisian profil/settings
class ProfileState(StatesGroup):
    waiting_for_age = State()
    waiting_for_gender = State()
    waiting_for_region = State()

# ---------------------------------------------------------
# NAVIGATION KEYBOARDS (Papan Tombol Navigation)
# ---------------------------------------------------------
def main_menu_keyboard():
    kb = [
        [KeyboardButton(text="▶️ Start"), KeyboardButton(text="⚙️ Setting")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def chat_menu_keyboard():
    kb = [
        [KeyboardButton(text="⏭️ Next"), KeyboardButton(text="🛑 Stop")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ---------------------------------------------------------
# LOGIKA PENGHUBUNG & PENCARI PASANGAN (Matching Logic)
# ---------------------------------------------------------
async def match_users(user_id: int):
    # Jika pengguna sudah punya pasangan atau sudah di antrean, lewati
    if user_id in active_chats or user_id in waiting_queue:
        return

    if waiting_queue:
        # Ambil orang pertama di antrean
        partner_id = waiting_queue.pop(0)

        # Pastikan tidak berpasangan dengan diri sendiri
        if partner_id == user_id:
            waiting_queue.append(user_id)
            return

        # Hubungkan kedua pengguna
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        # Format pesan pemberitahuan profil lawan bicara
        prof_a = user_profiles.get(user_id, {"age": "-", "gender": "-", "region": "-"})
        prof_b = user_profiles.get(partner_id, {"age": "-", "gender": "-", "region": "-"})

        msg_for_a = (
            "🎉 **Pasangan ditemukan!**\n\n"
            f"👤 **Umur:** {prof_b['age']}\n"
            f"🚻 **Gender:** {prof_b['gender']}\n"
            f"📍 **Wilayah:** {prof_b['region']}\n\n"
            "Mulai menyapa sekarang!"
        )
        msg_for_b = (
            "🎉 **Pasangan ditemukan!**\n\n"
            f"👤 **Umur:** {prof_a['age']}\n"
            f"🚻 **Gender:** {prof_a['gender']}\n"
            f"📍 **Wilayah:** {prof_a['region']}\n\n"
            "Mulai menyapa sekarang!"
        )

        await bot.send_message(user_id, msg_for_a, reply_markup=chat_menu_keyboard(), parse_mode="Markdown")
        await bot.send_message(partner_id, msg_for_b, reply_markup=chat_menu_keyboard(), parse_mode="Markdown")
    else:
        # Masukkan pengguna ke antrean jika belum ada lawan
        waiting_queue.append(user_id)
        await bot.send_message(
            user_id, 
            "🔍 **Mencari teman obrolan acak...**\nMohon tunggu sejenak.",
            reply_markup=chat_menu_keyboard(),
            parse_mode="Markdown"
        )

async def disconnect_user(user_id: int):
    # Hapus dari antrean jika ada
    if user_id in waiting_queue:
        waiting_queue.remove(user_id)

    # Putuskan hubungan obrolan jika sedang berpasangan
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        if partner_id in active_chats:
            del active_chats[partner_id]
            await bot.send_message(
                partner_id,
                "💔 **Teman bicara Anda telah meninggalkan obrolan.**",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )

# ---------------------------------------------------------
# COMMAND & BUTTON HANDLERS
# ---------------------------------------------------------
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Halo **{message.from_user.first_name}**! 👋\n\n"
        "Selamat datang di Bot Anonymous Chat.\n"
        "Klik **▶️ Start** untuk mencari teman obrolan acak, atau **⚙️ Setting** untuk mengatur profil Anda.",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

@router.message(F.text == "▶️ Start")
async def handle_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id in active_chats:
        await message.answer("Anda sedang dalam obrolan! Klik **🛑 Stop** terlebih dahulu jika ingin keluar.")
        return
    await match_users(user_id)

@router.message(F.text == "🛑 Stop")
async def handle_stop(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id in active_chats or user_id in waiting_queue:
        await disconnect_user(user_id)
        await message.answer("🛑 **Anda telah keluar dari obrolan/pencarian.**", reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    else:
        await message.answer("Anda sedang tidak berada dalam obrolan.", reply_markup=main_menu_keyboard())

@router.message(F.text == "⏭️ Next")
async def handle_next(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    await disconnect_user(user_id)
    await match_users(user_id)

# ---------------------------------------------------------
# SETTING PROFIL HANDLERS (FSM)
# ---------------------------------------------------------
@router.message(F.text == "⚙️ Setting")
async def handle_setting(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in active_chats:
        await message.answer("Anda harus menghentikan obrolan terlebih dahulu (**🛑 Stop**) untuk mengubah profil.")
        return

    await state.set_state(ProfileState.waiting_for_age)
    await message.answer("📝 **Pengaturan Profil (1/3)**\n\nMasukkan **Umur** Anda (contoh: 21):", reply_markup=ReplyKeyboardRemove())

@router.message(ProfileState.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(ProfileState.waiting_for_gender)
    
    # Keyboard pilihan gender
    gender_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Laki-Laki"), KeyboardButton(text="Perempuan")]],
        resize_keyboard=True
    )
    await message.answer("📝 **Pengaturan Profil (2/3)**\n\nPilih atau ketik **Gender** Anda:", reply_markup=gender_kb)

@router.message(ProfileState.waiting_for_gender)
async def process_gender(message: Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await state.set_state(ProfileState.waiting_for_region)
    await message.answer("📝 **Pengaturan Profil (3/3)**\n\nMasukkan **Wilayah/Kota** Anda (contoh: Jakarta):", reply_markup=ReplyKeyboardRemove())

@router.message(ProfileState.waiting_for_region)
async def process_region(message: Message, state: FSMContext):
    user_data = await state.get_data()
    user_id = message.from_user.id

    # Simpan profil pengguna secara global
    user_profiles[user_id] = {
        "age": user_data["age"],
        "gender": user_data["gender"],
        "region": message.text
    }

    await state.clear()
    await message.answer(
        "✅ **Profil Anda berhasil diperbarui!**\n\n"
        f"👤 Umur: {user_profiles[user_id]['age']}\n"
        f"🚻 Gender: {user_profiles[user_id]['gender']}\n"
        f"📍 Wilayah: {user_profiles[user_id]['region']}",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

# ---------------------------------------------------------
# RELAY CHAT (Meneruskan Pesan Antar Pengguna)
# ---------------------------------------------------------
@router.message()
async def relay_message(message: Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        # Meneruskan pesan (teks, foto, voice note, stiker, dll)
        try:
            await message.copy_to(chat_id=partner_id)
        except Exception:
            await message.answer(" Gagal mengirim pesan ke pasangan Anda.", reply_markup=main_menu_keyboard())
            await disconnect_user(user_id)
    else:
        await message.answer(
            "Anda belum terhubung dengan siapapun. Klik **▶️ Start** untuk mulai mencari teman obrolan.",
            reply_markup=main_menu_keyboard()
        )

# ---------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------
async def main():
    print("Bot sedang berjalan...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
