import telebot
from flask import Flask
import os
from threading import Thread
import math

# ========================================================
# KHU VỰC CÀI ĐẶT (BẠN CHỈ CẦN SỬA DÒNG DƯỚI ĐÂY)
# ========================================================

# HÃY DÁN TOKEN MỚI CỦA BẠN VÀO GIỮA HAI DẤU NHÁY ĐƠN
# Ví dụ đúng: TOKEN = '79999:AAH...'
TOKEN = '8560636939:AAE179IaRxp8g9rp4RT8Tb9kyHG5jnL470U'

# ========================================================

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# --- 1. LOGIC RUNG LIVE PRO (GPS) ---
def calculate_live_gps(minute, da, sot, soo, corners, score_diff, red_card):
    if minute < 1: return None
    raw_pressure = da + (corners * 3)
    pressure_per_min = raw_pressure / minute
    total_shots = sot + soo
    efficiency = 1.0 + (sot / total_shots * 1.5) if total_shots > 0 else 0.8
    urgency = 1.0
    if score_diff < 0: urgency = 1.35
    elif score_diff == 0 and minute > 70: urgency = 1.2
    if red_card: urgency += 0.4
    gps = pressure_per_min * efficiency * urgency * 10 
    
    signal = "🧊 BÌNH THƯỜNG"
    if gps >= 9.0: signal = "🚀 CƠ HỘI KIM CƯƠNG (ALL-IN)"
    elif gps >= 7.0: signal = "🔥 ÁP LỰC CỰC ĐẠI (RUNG)"
    elif gps >= 4.5: signal = "👀 CÓ TÍN HIỆU (WAIT)"
    
    return f"🤖 **GPS V6.0**\n⏱ {minute}' | GPS: {round(gps,1)}\n👉 {signal}"

# --- 2. LOGIC SOI KÈO PREMATCH ---
def analyze_prematch(home, away, hdp, ou, gh, ga):
    xg = gh + ga
    pick = "TÀI" if xg > ou else "XỈU"
    return f"🔮 **PREMATCH**\n⚽ {home} vs {away}\n📊 xG: {xg} | Kèo: {ou}\n👉 Pick: {pick}"

# --- 3. XỬ LÝ LỆNH ---
@bot.message_handler(commands=['calc'])
def handle_calc(message):
    try:
        args = [int(x) for x in message.text.split()[1:]]
        while len(args) < 7: args.append(0)
        bot.reply_to(message, calculate_live_gps(*args))
    except: bot.reply_to(message, "⚠️ Lỗi nhập liệu.")

@bot.message_handler(commands=['soi'])
def handle_soi(message):
    try:
        args = message.text.replace("/soi", "").split()
        bot.reply_to(message, analyze_prematch(args[0], args[1], float(args[2]), float(args[3]), float(args[4]), float(args[5])))
    except: bot.reply_to(message, "⚠️ Lỗi nhập liệu.")

@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m, "Bot V6.0 đã sẵn sàng! Gõ /calc hoặc /soi")

# --- 4. SERVER ---
@server.route('/')
def ping(): return "Bot Alive", 200

def run_web(): server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
def run_bot(): bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    run_bot()
