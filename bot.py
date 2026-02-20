import os
import time
import math
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ==========================================
# ⚠️ အောက်ပါတို့ကို ဖြည့်သွင်းပါ
# ==========================================
API_ID = 7978114
API_HASH = "5f7839feeba133497f24acfd005ef2ec"
BOT_TOKEN = "8207859409:AAH3VQOt3Y84l6ZuQ9mVTP7vW86nwTu2YTM"

PREROLL_FILE = "preroll.mp4"       
OUTRO_FILE = "outro.mp4"           
FONT_BOLD_FILE = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf"
LOGO_FILE = "logo.png"             
THUMB_FILE = "thumb.jpg"           

app = Client("ultimate_encode_bot_v2", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ==========================================
# 🗂 မှတ်သားရန် နေရာများ
# ==========================================
user_data = {}      
cancel_flags = {}   
active_processes = {} 

# ==========================================
# 📊 Helper Functions
# ==========================================
def humanbytes(size):
    if not size: return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

async def get_video_duration(file_path):
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await process.communicate()
    try:
        return float(stdout.decode().strip())
    except:
        return 0.0

def get_seconds_from_time(time_str):
    try:
        h, m, s = time_str.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except:
        return 0.0

async def progress(current, total, message, text, user_id, start_time):
    if cancel_flags.get(user_id):
        raise asyncio.CancelledError("User Cancelled")

    now = time.time()
    diff = now - start_time
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        
        bar_length = 15
        filled_length = int(bar_length * percentage // 100)
        bar = '■' * filled_length + '□' * (bar_length - filled_length)
        
        tmp = f"[{bar}] \n**Progress:** {round(percentage, 2)}%\n" \
              f"{humanbytes(current)} of {humanbytes(total)}\n" \
              f"**Speed:** {humanbytes(speed)}/s\n" \
              f"**ETA:** {TimeFormatter(time_to_completion)}"
        try:
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]])
            await message.edit_text(f"{text}\n{tmp}", reply_markup=btn)
        except:
            pass

# UI Functions
async def ask_front_preroll(message_or_callback, user_id):
    user_data[user_id]["state"] = "ASK_FRONT_PREROLL"
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 မူလ Preroll သာသုံးမည်", callback_data="front_default")],
        [InlineKeyboardButton("🆕 အသစ် + မူလ Preroll တွဲသုံးမည်", callback_data="front_custom")],
        [InlineKeyboardButton("❌ ရှေ့မှာဘာမှမထည့်ပါ", callback_data="front_none")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
    ])
    text = "🎬 **ရှေ့ပိုင်း (Intro) ကို ဘယ်လိုလုပ်မလဲ?**"
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=btns)
    else:
        await message_or_callback.reply_text(text, reply_markup=btns)
        
async def ask_outro(message_or_callback, user_id):
    user_data[user_id]["state"] = "ASK_OUTRO"
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ အသေထည့်မည် (outro.mp4)", callback_data="outro_yes")],
        [InlineKeyboardButton("❌ မထည့်ပါ", callback_data="outro_no")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
    ])
    text = "🎬 **နောက်ဆုံးပိုင်း (Outro - အသေ) ကို ဆက်ပြီး ထည့်မလား?**"
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=btns)
    else:
        await message_or_callback.reply_text(text, reply_markup=btns)

async def ask_thumb(message_or_callback, user_id):
    user_data[user_id]["state"] = "ASK_THUMB"
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ ပုံအသစ်ပြောင်းမည်", callback_data="thumb_custom")],
        [InlineKeyboardButton("✅ မူလပုံပဲသုံးမည် (thumb.jpg)", callback_data="thumb_default")],
        [InlineKeyboardButton("❌ လုံးဝမထည့်ပါ", callback_data="thumb_none")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
    ])
    text = "🖼️ **ဗီဒီယိုရဲ့ မျက်နှာဖုံးပုံ (Thumbnail) ကို ဘယ်လိုလုပ်မလဲ?**"
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=btns)
    else:
        await message_or_callback.reply_text(text, reply_markup=btns)

# ==========================================
# 🤖 Bot Handlers
# ==========================================
@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    if user_id in user_data: del user_data[user_id]
    await message.reply_text("👋 Video ပို့လိုက်ပါ။ ပို့ပြီးပါက စိတ်ကြိုက်ရွေးချယ်ခွင့် ပေးပါမည်။")

@app.on_message(filters.video | filters.document | filters.photo)
async def handle_media(client, message):
    user_id = message.from_user.id
    state = user_data.get(user_id, {}).get("state")
    
    if state == "WAITING_SUBTITLE":
        if message.document and message.document.file_name and message.document.file_name.endswith(('.srt', '.ass')):
            user_data[user_id]["sub_msg"] = message
            await ask_front_preroll(message, user_id)
        else:
            await message.reply_text("⚠️ ကျေးဇူးပြု၍ .srt သို့မဟုတ် .ass စာတန်းထိုးဖိုင်ကိုသာ ပို့ပေးပါ။")
        return

    if state == "WAITING_FRONT_PREROLL":
        is_video = False
        if message.video: is_video = True
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('video/'): is_video = True
        
        if is_video:
            user_data[user_id]["front_msg"] = message
            user_data[user_id]["use_custom_front"] = True
            user_data[user_id]["use_default_front"] = True
            user_data[user_id]["custom_front_path"] = f"custom_front_{user_id}.mp4"
            await ask_outro(message, user_id)
        else:
            await message.reply_text("⚠️ ကျေးဇူးပြု၍ Preroll အသစ်အတွက် Video ဖိုင်ကိုသာ ပို့ပေးပါ။")
        return
        
    if state == "WAITING_THUMB":
        is_image = False
        if message.photo: is_image = True
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'): is_image = True
        
        if is_image:
            thumb_dl_path = f"custom_thumb_{user_id}.jpg"
            status = await message.reply_text("📥 Thumbnail ကို ဒေါင်းလုတ်ဆွဲနေသည်...")
            downloaded_thumb = await message.download(file_name=thumb_dl_path)
            
            user_data[user_id]["use_thumb"] = True
            user_data[user_id]["thumb_path"] = downloaded_thumb
            user_data[user_id]["state"] = "PROCESSING"
            
            await status.edit_text("⏳ စတင် ပြင်ဆင်နေပါပြီ...")
            await process_everything(client, user_id)
        else:
            await message.reply_text("⚠️ ကျေးဇူးပြု၍ Thumbnail အတွက် ပုံ (Photo/Image) ကိုသာ ပို့ပေးပါ။")
        return

    is_video = False
    if message.video:
        is_video = True
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('video/'):
        is_video = True
        
    if is_video:
        user_data[user_id] = {"video_msg": message, "state": "ASK_TRIM_START"}
        cancel_flags[user_id] = False
        
        await message.reply_text("✂️ **ဗီဒီယို ရှေ့ဆုံး (Start) ကနေ ဘယ်နှစ်စက္ကန့် ဖြတ်ထုတ်မလဲ?**\n\n(ဂဏန်းသာ ရိုက်ထည့်ပါ။ ဘာမှမဖြတ်လိုပါက `0` ဟုသာ ပို့ပါ)")
    elif state not in ["WAITING_SUBTITLE", "WAITING_FRONT_PREROLL", "WAITING_THUMB"]:
        await message.reply_text("⚠️ ကျေးဇူးပြု၍ Video ဖိုင်ကိုသာ ပို့ပေးပါ။")

@app.on_message(filters.text)
async def handle_text(client, message):
    user_id = message.from_user.id
    if user_id not in user_data: return
    state = user_data[user_id].get("state")
    
    if state == "ASK_TRIM_START":
        try:
            trim_start = float(message.text.strip())
            user_data[user_id]["trim_start"] = trim_start
            user_data[user_id]["state"] = "ASK_TRIM_END"
            await message.reply_text("✂️ **ဗီဒီယို နောက်ဆုံး (End) ကနေ ဘယ်နှစ်စကန့် ဖြတ်ထုတ်မလဲ?**\n\n(ဘာမှမဖြတ်လိုပါက `0` ဟုသာ ပို့ပါ)")
        except:
            await message.reply_text("⚠️ ကျေးဇူးပြု၍ ဂဏန်းသာ ရိုက်ထည့်ပါ (ဥပမာ - 15, 20.5, 0)")
            
    elif state == "ASK_TRIM_END":
        try:
            trim_end = float(message.text.strip())
            user_data[user_id]["trim_end"] = trim_end
            user_data[user_id]["state"] = "ASK_CROP"
            
            btns = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ ဖြတ်ထုတ်မည် (Crop)", callback_data="crop_yes")],
                [InlineKeyboardButton("❌ မဖြတ်ပါ", callback_data="crop_no")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
            ])
            await message.reply_text("🔪 **အပေါ်ဘယ်/ညာက သူများစာတွေကို Crop နဲ့ လှီးထုတ်မလား?**\n(စာပျောက်သွားတဲ့အထိ အပေါ်ပိုင်းကို နည်းနည်း ဖြတ်ချပေးပါမည်)", reply_markup=btns)
        except:
            await message.reply_text("⚠️ ကျေးဇူးပြု၍ ဂဏန်းသာ ရိုက်ထည့်ပါ (ဥပမာ - 15, 20.5, 0)")

@app.on_callback_query()
async def callback_handler(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data.startswith("cancel_"):
        cancel_flags[user_id] = True
        if user_id in active_processes:
            try: active_processes[user_id].terminate()
            except: pass
        if user_id in user_data: del user_data[user_id]
        await callback.answer("❌ လုပ်ငန်းစဉ်ကို ရပ်တန့်လိုက်ပါပြီ။", show_alert=True)
        await callback.message.edit_text("❌ **Cancelled by User.**\n(စတင်ရန် Video အသစ်ပြန်ပို့ပါ)")
        return

    if user_id not in user_data:
        await callback.answer("⚠️ Session Expired. ဗီဒီယို အသစ်ပြန်ပို့ပါ။", show_alert=True)
        return

    if data in ["crop_yes", "crop_no"]:
        user_data[user_id]["use_crop"] = (data == "crop_yes")
        user_data[user_id]["state"] = "ASK_LOGO"
        
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Logo အုပ်မည်", callback_data="logo_yes")],
            [InlineKeyboardButton("❌ မအုပ်ပါ", callback_data="logo_no")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
        ])
        await callback.message.edit_text("🖼 **သူများ Logo နေရာမှာ ကိုယ့် Logo (logo.png) ကို ဖုံးအုပ်မလား?**", reply_markup=btns)

    elif data in ["logo_yes", "logo_no"]:
        user_data[user_id]["use_logo"] = (data == "logo_yes")
        user_data[user_id]["state"] = "ASK_SUB"
        
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ထည့်မည်", callback_data="sub_yes")],
            [InlineKeyboardButton("❌ မထည့်ပါ", callback_data="sub_no")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
        ])
        await callback.message.edit_text("📝 **မြန်မာစာတန်းထိုး (.srt) ထည့်မလား?**", reply_markup=btns)

    elif data in ["sub_yes", "sub_no"]:
        if data == "sub_yes":
            user_data[user_id]["use_sub"] = True
            user_data[user_id]["state"] = "WAITING_SUBTITLE"
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]])
            await callback.message.edit_text("📥 **Subtitle ဖိုင် (.srt သို့ .ass) ကို အခုပေးပို့လိုက်ပါ...**", reply_markup=btn)
        else:
            user_data[user_id]["use_sub"] = False
            await ask_front_preroll(callback, user_id)

    elif data in ["front_default", "front_custom", "front_none"]:
        if data == "front_default":
            user_data[user_id]["use_custom_front"] = False
            user_data[user_id]["use_default_front"] = True
            await ask_outro(callback, user_id)
        elif data == "front_custom":
            user_data[user_id]["state"] = "WAITING_FRONT_PREROLL"
            await callback.message.edit_text("📥 **ရှေ့ဆုံးမှာထည့်မည့် Video အတိုလေး (Intro အသစ်) ကို အခု ပို့ပေးပါ...**\n(ထိုအသစ်ပြီးလျှင် မူလ Preroll ကို အလိုအလျောက် ဆက်ပေးပါမည်)")
        elif data == "front_none":
            user_data[user_id]["use_custom_front"] = False
            user_data[user_id]["use_default_front"] = False
            await ask_outro(callback, user_id)
            
    elif data in ["outro_yes", "outro_no"]:
        user_data[user_id]["use_outro"] = (data == "outro_yes")
        await ask_thumb(callback, user_id)
        
    elif data in ["thumb_custom", "thumb_default", "thumb_none"]:
        if data == "thumb_custom":
            user_data[user_id]["state"] = "WAITING_THUMB"
            await callback.message.edit_text("🖼️ **Thumbnail အတွက် ပုံ (Photo) ကို အခု ပို့ပေးပါ...**")
        elif data == "thumb_default":
            user_data[user_id]["use_thumb"] = True
            user_data[user_id]["thumb_path"] = THUMB_FILE
            user_data[user_id]["state"] = "PROCESSING"
            await callback.message.edit_text("⏳ စတင် ပြင်ဆင်နေပါပြီ...")
            await process_everything(client, user_id)
        elif data == "thumb_none":
            user_data[user_id]["use_thumb"] = False
            user_data[user_id]["thumb_path"] = None
            user_data[user_id]["state"] = "PROCESSING"
            await callback.message.edit_text("⏳ စတင် ပြင်ဆင်နေပါပြီ...")
            await process_everything(client, user_id)

# ==========================================
# ⚙️ MAIN PROCESSING ENGINE (Core)
# ==========================================
async def process_everything(client, user_id):
    ud = user_data[user_id]
    v_msg = ud["video_msg"]
    
    trim_start = ud.get("trim_start", 0)
    trim_end = ud.get("trim_end", 0)
    use_crop = ud.get("use_crop", False)
    use_logo = ud.get("use_logo", False)
    use_sub = ud.get("use_sub", False)
    
    use_custom_front = ud.get("use_custom_front", False)
    use_default_front = ud.get("use_default_front", False)
    use_outro = ud.get("use_outro", False)
    use_thumb = ud.get("use_thumb", False)
    
    v_path = f"video_{user_id}.mp4"
    s_path = f"sub_{user_id}.srt" 
    out_path = f"encoded_{user_id}.mp4"
    
    status = await v_msg.reply_text("⏳ ပြင်ဆင်နေပါသည်...")
    cancel_btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]])

    try:
        if use_logo and not os.path.exists(LOGO_FILE):
            await status.edit_text("❌ `logo.png` ဖိုင်ကို မတွေ့ပါ။")
            return
        if use_default_front and not os.path.exists(PREROLL_FILE):
            await status.edit_text("❌ `preroll.mp4` ဖိုင်ကို မတွေ့ပါ။")
            return
        if use_outro and not os.path.exists(OUTRO_FILE):
            await status.edit_text("❌ `outro.mp4` ဖိုင်ကို မတွေ့ပါ။")
            return

        start_time = time.time()
        
        if use_custom_front and "front_msg" in ud:
            ud["custom_front_path"] = await ud["front_msg"].download(file_name=ud["custom_front_path"], progress=progress, progress_args=(status, "📥 **Downloading Intro...**", user_id, start_time))

        start_time = time.time()
        v_path = await v_msg.download(file_name=v_path, progress=progress, progress_args=(status, "📥 **Downloading Video...**", user_id, start_time))
        
        if use_sub:
            s_msg = ud["sub_msg"]
            start_time = time.time()
            s_path = await s_msg.download(file_name=s_path, progress=progress, progress_args=(status, "📥 **Downloading Subtitle...**", user_id, start_time))

        await status.edit_text("⚙️ **Calculating Setup & Bitrate...**", reply_markup=cancel_btn)
        
        file_size_mb = os.path.getsize(v_path) / (1024 * 1024)
        original_duration = await get_video_duration(v_path)
        if original_duration <= 0: original_duration = 3600 

        actual_duration = original_duration - trim_start - trim_end
        if actual_duration <= 0: actual_duration = original_duration

        target_mb = file_size_mb * 0.7 
        if file_size_mb >= 3072: target_mb = file_size_mb / 2
        elif file_size_mb >= 2048: target_mb = 1280 
            
        video_bitrate_k = int((target_mb * 8192) / actual_duration) - 128
        if video_bitrate_k < 500: video_bitrate_k = 500 
        b_v = f"-b:v {video_bitrate_k}k -maxrate {int(video_bitrate_k*1.5)}k -bufsize {video_bitrate_k*2}k"

        if cancel_flags.get(user_id): raise asyncio.CancelledError()

        await status.edit_text("⚙️ **FFmpeg စတင် အလုပ်လုပ်နေပါပြီ...**\n(Progress Bar ပေါ်လာရန် ခဏစောင့်ပေးပါ...)", reply_markup=cancel_btn)

        cmd = f'ffmpeg -y '
        input_idx = 0
        filters_list = []
        
        idx_cf = -1
        if use_custom_front:
            cf_path = ud.get("custom_front_path")
            cmd += f'-i "{cf_path}" '
            idx_cf = input_idx
            input_idx += 1
            
        idx_df = -1
        if use_default_front:
            cmd += f'-i "{PREROLL_FILE}" '
            idx_df = input_idx
            input_idx += 1
            
        trim_str = f"-ss {trim_start} " if trim_start > 0 else ""
        dur_str = f"-t {actual_duration} " if (trim_end > 0 and actual_duration > 0) else ""
        cmd += f'{trim_str}{dur_str}-i "{v_path}" '
        idx_main = input_idx
        input_idx += 1
        
        idx_logo = -1
        if use_logo:
            cmd += f'-i "{LOGO_FILE}" '
            idx_logo = input_idx
            input_idx += 1
            
        idx_outro = -1
        if use_outro:
            cmd += f'-i "{OUTRO_FILE}" '
            idx_outro = input_idx
            input_idx += 1

        if use_custom_front:
            filters_list.append(f"[{idx_cf}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[cf_v]")
            filters_list.append(f"[{idx_cf}:a:0]aresample=48000[cf_a]")

        if use_default_front:
            filters_list.append(f"[{idx_df}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[df_v]")
            filters_list.append(f"[{idx_df}:a:0]aresample=48000[df_a]")

        crop_filter = "crop=iw:ih-110:0:110," if use_crop else ""
        filters_list.append(f"[{idx_main}:v:0]{crop_filter}scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[main_scaled]")
        
        current_v = "main_scaled"

        if use_logo:
            # ⭐ FIX: Logo နေရာကို အပေါ်ကနေ 40px အောက်ဆွဲချထားသည် ⭐
            filters_list.append(f"[{idx_logo}:v:0]scale=100:-1[logo_scaled]")
            filters_list.append(f"[{current_v}][logo_scaled]overlay=W-w-10:40[{current_v}_logo]")
            current_v = f"{current_v}_logo"

        if use_sub:
            sub_style = ":force_style='Fontname=Pyidaungsu,PrimaryColour=&H0000FFFF,FontSize=22,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Bold=1'"
            filters_list.append(f"[{current_v}]subtitles={s_path}{sub_style}[{current_v}_sub]")
            current_v = f"{current_v}_sub"

        filters_list.append(f"[{current_v}]drawtext=fontfile={FONT_BOLD_FILE}:text='t.me/ocadults':x=30:y=30:fontsize=36:fontcolor=yellow:borderw=2:bordercolor=black,drawtext=fontfile={FONT_BOLD_FILE}:text='ocadults.net':x=w-tw-30:y=30:fontsize=36:fontcolor=yellow:borderw=2:bordercolor=black[main_v_final]")
        filters_list.append(f"[{idx_main}:a:0]aresample=48000[main_a_final]")

        if use_outro:
            filters_list.append(f"[{idx_outro}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[out_v]")
            filters_list.append(f"[{idx_outro}:a:0]aresample=48000[out_a]")

        concat_inputs = ""
        concat_count = 0
        
        if use_custom_front:
            concat_inputs += "[cf_v][cf_a]"
            concat_count += 1
            
        if use_default_front:
            concat_inputs += "[df_v][df_a]"
            concat_count += 1
        
        concat_inputs += "[main_v_final][main_a_final]"
        concat_count += 1

        if use_outro:
            concat_inputs += "[out_v][out_a]"
            concat_count += 1

        if concat_count > 1:
            filters_list.append(f"{concat_inputs}concat=n={concat_count}:v=1:a=1[outv][outa]")
            map_cmd = '-map "[outv]" -map "[outa]"'
        else:
            map_cmd = '-map "[main_v_final]" -map "[main_a_final]"'

        filter_complex = ";".join(filters_list)
        cmd += f'-filter_complex "{filter_complex}" {map_cmd} -c:v libx265 {b_v} -preset fast -c:a aac -b:a 128k "{out_path}"'

        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        active_processes[user_id] = process
        
        last_update = 0 
        enc_start = time.time()
        error_log = "" 
        
        total_enc_dur = actual_duration
        if use_custom_front:
            cf_path = ud.get("custom_front_path")
            total_enc_dur += await get_video_duration(cf_path)
        if use_default_front:
            total_enc_dur += await get_video_duration(PREROLL_FILE)
        if use_outro:
            total_enc_dur += await get_video_duration(OUTRO_FILE)
        
        while True:
            if cancel_flags.get(user_id):
                process.terminate()
                raise asyncio.CancelledError()
                
            chunk = await process.stderr.read(4096)
            if not chunk: 
                break
                
            chunk_str = chunk.decode('utf-8', errors='replace')
            error_log += chunk_str 
            
            matches = re.findall(r"time=\s*(\d+:\d{2}:\d{2}[\.\d]*)", chunk_str)
            if matches and total_enc_dur > 0:
                current_sec = get_seconds_from_time(matches[-1])
                percentage = min((current_sec / total_enc_dur) * 100, 100)
                
                now = time.time()
                if now - last_update >= 5: 
                    last_update = now
                    elapsed = now - enc_start
                    speed = current_sec / elapsed if elapsed > 0 else 0
                    eta_sec = (total_enc_dur - current_sec) / speed if speed > 0 else 0
                    
                    bar = '■' * int(15 * percentage // 100) + '□' * (15 - int(15 * percentage // 100))
                    try:
                        await status.edit_text(
                            f"⚙️ **Encoding Video...**\n"
                            f"[{bar}]\n"
                            f"**Progress:** {percentage:.1f}%\n"
                            f"**Target Size:** ~{round(target_mb, 2)} MB\n"
                            f"**ETA:** {TimeFormatter(eta_sec*1000)}",
                            reply_markup=cancel_btn
                        )
                    except: pass

        await process.wait()

        if cancel_flags.get(user_id): raise asyncio.CancelledError()

        if process.returncode == 0 and os.path.exists(out_path):
            await status.edit_text("✅ **Encoding ပြီးပါပြီ! Upload တင်နေပါသည်...**", reply_markup=cancel_btn)
            start_time = time.time()
            caption = f"✅ Encoded by OC Admin\nOriginal Size: {round(file_size_mb, 2)} MB\nTarget Size: ~{round(target_mb, 2)} MB"
            
            thumb_to_use = None
            if use_thumb:
                t_path = ud.get("thumb_path")
                if t_path and os.path.exists(t_path):
                    thumb_to_use = t_path

            await v_msg.reply_video(
                out_path, 
                caption=caption, 
                thumb=thumb_to_use, 
                progress=progress, 
                progress_args=(status, "📤 **Uploading...**", user_id, start_time)
            )
            await status.delete()
        else:
            await status.edit_text("❌ **Encoding Error ဖြစ်သွားပါသည်။ Log ဖိုင်ကို စစ်ဆေးပါ။**")
            with open("error_log.txt", "w") as f:
                f.write(error_log)
            await v_msg.reply_document("error_log.txt")

    except asyncio.CancelledError:
        pass
    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")
        
    finally:
        files_to_delete = [v_path, s_path, out_path]
        if use_custom_front and "front_msg" in ud and "custom_front_path" in ud and os.path.exists(ud["custom_front_path"]):
            files_to_delete.append(ud["custom_front_path"])
            
        if use_thumb:
            t_path = ud.get("thumb_path")
            if t_path and "custom_thumb_" in t_path and os.path.exists(t_path):
                files_to_delete.append(t_path)
            
        for f in files_to_delete:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
                
        if user_id in user_data: del user_data[user_id]
        if user_id in cancel_flags: del cancel_flags[user_id]
        if user_id in active_processes: del active_processes[user_id]

print("Ultimate Editor Bot Started...")
app.run()
