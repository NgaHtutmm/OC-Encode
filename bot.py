import os
import asyncio
from pyrogram import Client, filters

# ==========================================
# ⚠️ အောက်ပါတို့ကို ဖြည့်သွင်းပါ
# ==========================================
API_ID = 7978114
API_HASH = "5f7839feeba133497f24acfd005ef2ec"
BOT_TOKEN = "8207859409:AAH3VQOt3Y84l6ZuQ9mVTP7vW86nwTu2YTM"

# ဖိုင်နာမည်များ
PREROLL_FILE = "preroll.mp4"
FONT_FILE = "font.ttf" 

app = Client("smart_encode_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.video | filters.document)
async def smart_encode(client, message):
    status_msg = await message.reply_text("📥 ဇာတ်ကားကို ဒေါင်းလုတ်ဆွဲနေပါပြီ...")
    
    try:
        video_path = await message.download()
        output_path = f"encoded_{os.path.basename(video_path)}"
    except Exception as e:
        await status_msg.edit_text(f"❌ Download Error: {e}")
        return

    await status_msg.edit_text("⚙️ Resolution ညှိပြီး Encode လုပ်နေပါပြီ... (အချိန်ကြာပါမည်)")

    # ==========================================
    # 🎬 SMART FFmpeg Command
    # ==========================================
    # ရှင်းလင်းချက်:
    # 1. [0:v]scale=1920:1080... : Preroll ကို 1080p အတင်းပြောင်းမည် (Black bars ထည့်မည်)
    # 2. [1:v]scale=1920:1080... : Main Video ကို 1080p အတင်းပြောင်းမည်
    # 3. anullsrc : အသံမပါရင် အသံအလွတ် (Silent Audio) ထည့်ပေးမည်
    
    cmd = (
        f'ffmpeg -i "{PREROLL_FILE}" -i "{video_path}" '
        f'-f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 ' # [2] Silent Audio
        f'-filter_complex "'
        # --- အပိုင်း (၁) : Preroll ကို 1080p သို့ ပြောင်းခြင်း ---
        f'[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v0_scaled];'
        
        # --- အပိုင်း (၂) : Main Video ကို 1080p သို့ ပြောင်းပြီး စာတန်းထိုးခြင်း ---
        f'[1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,'
        f'drawtext=fontfile={FONT_FILE}:text=\'t.me/ocadults\':x=20:y=20:fontsize=24:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2,'
        f'drawtext=fontfile={FONT_FILE}:text=\'ocadults.net\':x=w-tw-20:y=20:fontsize=24:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2[v1_ready];'
        
        # --- အပိုင်း (၃) : Audio ညှိခြင်း (အသံမပါရင် Silent Audio ထည့်မည်) ---
        # Preroll Audio Check
        f'[0:a][2:a]amerge=inputs=1[a0_ready];' 
        # Main Video Audio Check
        f'[1:a][2:a]amerge=inputs=1[a1_ready];'

        # --- အပိုင်း (၄) : ဆက်ခြင်း (Preroll + Main + Preroll) ---
        f'[v0_scaled][a0_ready][v1_ready][a1_ready][v0_scaled][a0_ready]concat=n=3:v=1:a=1[outv][outa]" '
        
        f'-map "[outv]" -map "[outa]" '
        # H.265 Settings (လိုသလို ပြင်နိုင်သည်)
        f'-c:v libx265 -crf 26 -preset fast -c:a aac -b:a 128k -y "{output_path}"'
    )

    # Command Run ခြင်း
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        await status_msg.edit_text("✅ ပြီးပါပြီ! Upload တင်နေပါသည်...")
        try:
            await message.reply_video(output_path, caption="✅ Encoded by OC Admin")
        except Exception as e:
            await status_msg.edit_text(f"Upload Error: {e}")
        
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(output_path): os.remove(output_path)
    else:
        # Error တက်ရင် Log ဖိုင် ပို့ပေးမည် (ပိုတိကျအောင်)
        with open("error.txt", "w") as f:
            f.write(stderr.decode())
        await message.reply_document("error.txt", caption="❌ FFmpeg Error Log")

print("Smart Bot Started...")
app.run()
