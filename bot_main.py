import telebot
from flask import Flask, request
import os
from threading import Thread

# --- CẤU HÌNH ---
# Trên Render, chúng ta sẽ lưu TOKEN trong biến môi trường (Environment Variable) để bảo mật
TOKEN = os.environ.get('BOT_TOKEN') 
if not TOKEN:
    # Fallback nếu chạy trên máy cá nhân (nhập token của bạn vào đây để test)
    TOKEN = 'TOKEN_CỦA_BẠN_Ở_ĐÂY' 

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# --- LOGIC PHÂN TÍCH (GIỮ NGUYÊN) ---
def advanced_analysis(minute, da, sot, soo, corners=0):
    if minute < 1: return None
    raw_pressure = da + (sot * 5) + (soo * 2) + (corners * 3)
    pi = raw_pressure / minute
    total_shots = sot + soo
    ai = sot / total_shots if total_shots > 0 else 0
    
    signal, advice = "", ""
    if pi >= 2.0:
        signal = "🔥 CỰC NÓNG (HIGH PRESSURE)"
        if ai >= 0.5: advice = "👉 ACTION: Vào rung TÀI BÀN THẮNG"
        elif ai < 0.3: advice = "👉 ACTION: Vào rung TÀI GÓC"
        else: advice = "👉 ACTION: Chia vốn 70% Tài / 30% Góc"
    elif pi >= 1.2:
        signal = "⚡ CÓ BIẾN (MEDIUM)"
        advice = "👉 ACTION: Rình Odds hoặc chờ thêm"
    else:
        signal = "🧊 TRẬN ĐẤU CHẾT"
        advice = "👉 ACTION: Bỏ qua"

    return f"🤖 **PHÂN TÍCH V2.0**\n⏱ Phút: {minute}\n📈 PI: {round(pi, 2)} | AI: {round(ai*100)}%\n----------------\n{signal}\n{advice}"

@bot.message_handler(commands=['calc'])
def handle_calc(message):
    try:
        args = message.text.split()[1:]
        if len(args) < 4:
            bot.reply_to(message, "⚠️ Nhập thiếu số! Ví dụ: /calc 30 45 4 2 3")
            return
        minute, da, sot, soo = int(args[0]), int(args[1]), int(args[2]), int(args[3])
        corners = int(args[4]) if len(args) > 4 else 0
        bot.reply_to(message, advanced_analysis(minute, da, sot, soo, corners))
    except:
        bot.reply_to(message, "⚠️ Lỗi nhập liệu.")

# --- PHẦN QUAN TRỌNG: FAKE WEB SERVER CHO RENDER ---
@server.route('/')
def ping():
    return "Bot is alive!", 200

def run_web_server():
    # Render cung cấp biến PORT, nếu không có thì dùng 5000
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def run_bot():
    bot.infinity_polling()

# Chạy song song cả Bot Telegram và Web Server
if __name__ == "__main__":
    t = Thread(target=run_web_server)
    t.start()
    run_bot()