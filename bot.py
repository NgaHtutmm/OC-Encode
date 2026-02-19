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
FONT_FILE = "font.ttf" 
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

# ==========================================
# 🤖 Bot Handlers
# ==========================================
@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text("👋 Video ပို့လိုက်ပါ။ ပို့ပြီးပါက စိတ်ကြိုက်ရွေးချယ်ခွင့် ပေးပါမည်။")

@app.on_message(filters.video | filters.document)
async def handle_video(client, message):
    user_id = message.from_user.id
    if user_data.get(user_id, {}).get("state") == "WAITING_SUBTITLE":
        return
        
    user_data[user_id] = {"video_msg": message, "state": "ASK_PREROLL"}
    cancel_flags[user_id] = False
    
    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Preroll + Watermark + Compress", callback_data="preroll_yes")],
        [InlineKeyboardButton("🗜 Compress Only (File Size လျှော့ရန်)", callback_data="preroll_no")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
    ])
    await message.reply_text("ဒီဗီဒီယိုအတွက် ဘာလုပ်ချင်ပါသလဲ ရွေးပေးပါ-", reply_markup=btns)

@app.on_message(filters.document)
async def handle_subtitle(client, message):
    user_id = message.from_user.id
    data = user_data.get(user_id)
    
    if data and data.get("state") == "WAITING_SUBTITLE":
        if message.document.file_name.endswith(('.srt', '.ass')):
            data["sub_msg"] = message
            data["state"] = "PROCESSING"
            await process_everything(client, user_id)
        else:
            await message.reply_text("⚠️ ကျေးဇူးပြု၍ .srt သို့မဟုတ် .ass ဖိုင်ကိုသာ ပို့ပေးပါ။")

@app.on_callback_query()
async def callback_handler(client, callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data.startswith("cancel_"):
        cancel_flags[user_id] = True
        if user_id in active_processes:
            try:
                active_processes[user_id].terminate()
            except: pass
        await callback.answer("❌ လုပ်ငန်းစဉ်ကို ရပ်တန့်လိုက်ပါပြီ။", show_alert=True)
        await callback.message.edit_text("❌ **Cancelled by User.**")
        return

    if user_id not in user_data:
        await callback.answer("⚠️ Session Expired. ဗီဒီယို အသစ်ပြန်ပို့ပါ။", show_alert=True)
        return

    if data in ["preroll_yes", "preroll_no"]:
        user_data[user_id]["use_preroll"] = (data == "preroll_yes")
        user_data[user_id]["state"] = "ASK_SUBTITLE"
        
        btns = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ဟုတ်ကဲ့၊ ထည့်မည်", callback_data="sub_yes")],
            [InlineKeyboardButton("❌ မထည့်ပါ", callback_data="sub_no")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
        ])
        await callback.message.edit_text("ဒီဗီဒီယိုမှာ **မြန်မာစာတန်းထိုး (Subtitle)** ထည့်ချင်ပါသလား?", reply_markup=btns)

    elif data in ["sub_yes", "sub_no"]:
        if data == "sub_yes":
            user_data[user_id]["use_sub"] = True
            user_data[user_id]["state"] = "WAITING_SUBTITLE"
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]])
            await callback.message.edit_text("📥 **Subtitle ဖိုင် (.srt သို့ .ass) ကို အခုပေးပို့လိုက်ပါ...**", reply_markup=btn)
        else:
            user_data[user_id]["use_sub"] = False
            user_data[user_id]["state"] = "PROCESSING"
            await callback.message.edit_text("⏳ စတင် ပြင်ဆင်နေပါပြီ...")
            await process_everything(client, user_id)

# ==========================================
# ⚙️ MAIN PROCESSING ENGINE (Core)
# ==========================================
async def process_everything(client, user_id):
    ud = user_data[user_id]
    v_msg = ud["video_msg"]
    use_preroll = ud.get("use_preroll", False)
    use_sub = ud.get("use_sub", False)
    
    v_path = f"video_{user_id}.mp4"
    s_path = f"sub_{user_id}.srt" 
    out_path = f"encoded_{user_id}.mp4"
    
    status = await v_msg.reply_text("⏳ ပြင်ဆင်နေပါသည်...")
    cancel_btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]])

    try:
        start_time = time.time()
        v_path = await v_msg.download(file_name=v_path, progress=progress, progress_args=(status, "📥 **Downloading Video...**", user_id, start_time))
        
        if use_sub:
            s_msg = ud["sub_msg"]
            start_time = time.time()
            s_path = await s_msg.download(file_name=s_path, progress=progress, progress_args=(status, "📥 **Downloading Subtitle...**", user_id, start_time))

        await status.edit_text("⚙️ **Calculating Smart Bitrate...**", reply_markup=cancel_btn)
        
        file_size_mb = os.path.getsize(v_path) / (1024 * 1024)
        duration = await get_video_duration(v_path)
        if duration <= 0: duration = 3600 

        target_mb = file_size_mb * 0.7 
        if file_size_mb >= 3072:       
            target_mb = file_size_mb / 2
        elif file_size_mb >= 2048:     
            target_mb = 1280 
            
        video_bitrate_k = int((target_mb * 8192) / duration) - 128
        if video_bitrate_k < 500: video_bitrate_k = 500 
        b_v = f"-b:v {video_bitrate_k}k -maxrate {int(video_bitrate_k*1.5)}k -bufsize {video_bitrate_k*2}k"

        if cancel_flags.get(user_id): raise asyncio.CancelledError()

        await status.edit_text("⚙️ **FFmpeg စတင် အလုပ်လုပ်နေပါပြီ...**\n(Progress Bar ပေါ်လာရန် စက္ကန့်အနည်းငယ် စောင့်ပေးပါ...)", reply_markup=cancel_btn)

        sub_style = ":force_style='PrimaryColour=&H0000FFFF,FontSize=26,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Bold=1'"
        sub_filter = f",subtitles={s_path}{sub_style}" if use_sub else ""

        if use_preroll:
            preroll_dur = await get_video_duration(PREROLL_FILE)
            total_dur = duration + (preroll_dur * 2)
            cmd = (
                f'ffmpeg -i "{PREROLL_FILE}" -i "{v_path}" '
                f'-filter_complex "'
                f'[0:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p,split=2[v_start][v_end];'
                f'[0:a:0]aresample=48000,asplit=2[a_start][a_end];'
                f'[1:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p'
                f'{sub_filter},'
                f'drawtext=fontfile={FONT_FILE}:text=\'t.me/ocadults\':x=20:y=20:fontsize=24:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2,'
                f'drawtext=fontfile={FONT_FILE}:text=\'ocadults.net\':x=w-tw-20:y=20:fontsize=24:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2[main_v];'
                f'[1:a:0]aresample=48000[main_a];'
                f'[v_start][a_start][main_v][main_a][v_end][a_end]concat=n=3:v=1:a=1[outv][outa]" '
                f'-map "[outv]" -map "[outa]" '
                f'-c:v libx265 {b_v} -preset fast -c:a aac -b:a 128k -y "{out_path}"'
            )
        else:
            total_dur = duration
            cmd = (
                f'ffmpeg -i "{v_path}" '
                f'-filter_complex "'
                f'[0:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p{sub_filter}[outv];'
                f'[0:a:0]aresample=48000[outa]" '
                f'-map "[outv]" -map "[outa]" '
                f'-c:v libx265 {b_v} -preset fast -c:a aac -b:a 128k -y "{out_path}"'
            )

        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        active_processes[user_id] = process
        
        last_update = 0 
        enc_start = time.time()
        error_log = "" 
        
        # 📌 FIX: chunk exceed the limit ပြဿနာကို read(4096) ဖြင့် ဖြေရှင်းထားသည်
        while True:
            if cancel_flags.get(user_id):
                process.terminate()
                raise asyncio.CancelledError()
                
            chunk = await process.stderr.read(4096)
            if not chunk: 
                break
                
            chunk_str = chunk.decode('utf-8', errors='replace')
            error_log += chunk_str 
            
            # chunk ထဲက time= တွေကို အကုန်ရှာပြီး နောက်ဆုံးတစ်ခုကိုပဲ ယူမည်
            matches = re.findall(r"time=\s*(\d+:\d{2}:\d{2}[\.\d]*)", chunk_str)
            if matches and total_dur > 0:
                current_sec = get_seconds_from_time(matches[-1])
                percentage = min((current_sec / total_dur) * 100, 100)
                
                now = time.time()
                if now - last_update >= 5: 
                    last_update = now
                    elapsed = now - enc_start
                    speed = current_sec / elapsed if elapsed > 0 else 0
                    eta_sec = (total_dur - current_sec) / speed if speed > 0 else 0
                    
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
            
            thumb_to_use = THUMB_FILE if os.path.exists(THUMB_FILE) else None

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
        for f in files_to_delete:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
                
        if user_id in user_data: del user_data[user_id]
        if user_id in cancel_flags: del cancel_flags[user_id]
        if user_id in active_processes: del active_processes[user_id]

print("Chunk Fixed Bot Started...")
app.run()
