import os
import asyncio
from pyrogram import Client, filters

# ==========================================
# ⚠️ အောက်ပါတို့ကို ဖြည့်သွင်းပါ
# ==========================================
API_ID = 7978114
API_HASH = "5f7839feeba133497f24acfd005ef2ec"
BOT_TOKEN = "8207859409:AAH3VQOt3Y84l6ZuQ9mVTP7vW86nwTu2YTM"

# ဖိုင်နာမည်များ (Folder ထဲမှာ ရှိနေရမည်)
PREROLL_FILE = "preroll.mp4"
FONT_FILE = "font.ttf" 

app = Client("simple_encode_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.video | filters.document)
async def simple_encode(client, message):
    # ၁။ အကြောင်းပြန်စာ ပို့ခြင်း
    status_msg = await message.reply_text("📥 ဇာတ်ကားကို ဒေါင်းလုတ်ဆွဲနေပါပြီ...")
    
    # ၂။ ဇာတ်ကား Download ဆွဲခြင်း
    try:
        video_path = await message.download()
        output_path = f"encoded_{os.path.basename(video_path)}"
    except Exception as e:
        await status_msg.edit_text(f"❌ Download Error: {e}")
        return

    await status_msg.edit_text("⚙️ စာတန်းထိုးပြီး Encode လုပ်နေပါပြီ... (အချိန်ကြာပါမည်)")

    # ==========================================
    # 🎬 FFmpeg Command (အဓိက အပိုင်း)
    # ==========================================
    # [0] = Preroll, [1] = Main Video
    # concat=n=3 ဆိုတာ (Preroll + Main + Preroll) ၃ ခုဆက်မယ်လို့ ပြောတာပါ
    
    cmd = (
        f'ffmpeg -i "{PREROLL_FILE}" -i "{video_path}" '
        f'-filter_complex "'
        # Main Video [1] ကို စာတန်း ၂ ခု ထိုးမည်
        f'[1:v]drawtext=fontfile={FONT_FILE}:text=\'t.me/ocadults\':x=20:y=20:fontsize=24:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2,'  # Top-Left
        f'drawtext=fontfile={FONT_FILE}:text=\'ocadults.net\':x=w-tw-20:y=20:fontsize=24:fontcolor=white:shadowcolor=black:shadowx=2:shadowy=2[main_txt];' # Top-Right
        # Preroll [0] + Main [main_txt] + Preroll [0] ကို ဆက်မည်
        f'[0:v][0:a][main_txt][1:a][0:v][0:a]concat=n=3:v=1:a=1[outv][outa]" '
        f'-map "[outv]" -map "[outa]" '
        # H.265 (CRF 24) ဖြင့် ချုံ့မည်
        f'-c:v libx265 -crf 24 -preset fast -c:a aac -b:a 128k -y "{output_path}"'
    )

    # ၃။ Command Run ခြင်း
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    # ၄။ ပြန်ပို့ခြင်း (Upload)
    if process.returncode == 0:
        await status_msg.edit_text("✅ ပြီးပါပြီ! Upload တင်နေပါသည်...")
        try:
            await message.reply_video(output_path, caption="✅ Encoded by OC Admin")
        except Exception as e:
            await status_msg.edit_text(f"Upload Error: {e}")
        
        # ပြီးရင် ဖိုင်ဖျက်မည်
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(output_path): os.remove(output_path)
    else:
        # Error တက်ရင် ဘာကြောင့်လဲ ပြမည်
        await status_msg.edit_text(f"❌ Error ဖြစ်သွားပါသည်:\n{stderr.decode()[:500]}")

print("Bot စတင်ပါပြီ...")
app.run()
