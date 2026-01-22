import telebot
from flask import Flask
import os
from threading import Thread
import math

# --- CẤU HÌNH ---
# THAY BẰNG DÒNG NÀY (Nhớ dán token thật vào giữa hai dấu nháy)
TOKEN = '8560636939:AAFz7-aOYOzU3zNd49bzJYaEJoa4UKf3LYE'

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# ======================================================
# PHẦN 1: LOGIC RUNG LIVE PRO (CÔNG THỨC GPS)
# ======================================================
def calculate_live_gps(minute, da, sot, soo, corners, score_diff, red_card):
    """
    Tính chỉ số GPS (Goal Probability Score) dựa trên diễn biến trận đấu
    """
    if minute < 1: return None

    # 1. Base Pressure (Áp lực nền): DA và Góc
    raw_pressure = da + (corners * 3)
    pressure_per_min = raw_pressure / minute

    # 2. Efficiency (Độ hiệu quả): Thưởng cho sút trúng đích
    total_shots = sot + soo
    if total_shots > 0:
        accuracy = sot / total_shots
        # Nếu sút trúng nhiều -> Hệ số cao (Max 2.5)
        efficiency_factor = 1.0 + (accuracy * 1.5) 
    else:
        efficiency_factor = 0.8 # Cầm bóng nhiều mà không sút -> Phạt

    # 3. Urgency (Độ khẩn cấp): Dựa trên Tỷ số & Thẻ đỏ
    urgency_factor = 1.0
    
    if score_diff < 0: # Đang thua
        urgency_factor = 1.35 
        if minute > 80: urgency_factor = 1.6 # Thua cuối trận đá chết bỏ
    elif score_diff == 0: # Đang hòa
        if minute > 70: urgency_factor = 1.25 # Hòa cuối trận muốn ăn
    elif score_diff > 0: # Đang thắng
        urgency_factor = 0.7 # Đá giữ chân
    
    if red_card > 0: # Đối thủ bị thẻ đỏ
        urgency_factor += 0.4

    # --- TỔNG HỢP ĐIỂM GPS (Thang 10) ---
    gps = pressure_per_min * efficiency_factor * urgency_factor * 10 

    # Phân loại hành động
    signal = ""
    advice = ""
    
    if gps >= 9.0:
        signal = "🚀 CƠ HỘI KIM CƯƠNG (GPS > 9.0)"
        advice = "💰 ALL-IN ACTION: TÀI (Over) ngay lập tức!"
    elif gps >= 7.0:
        signal = "🔥 ÁP LỰC RẤT CAO (GPS > 7.0)"
        advice = "👉 BET: Rung 0.5 HT/FT hoặc Rung Góc (nếu Sút trượt nhiều)"
    elif gps >= 4.5:
        signal = "👀 CÓ TÍN HIỆU KHÁ (Wait)"
        advice = "👉 ACTION: Chờ Odds giảm rồi vào nhẹ"
    else:
        signal = "🧊 TRẬN ĐẤU 'CHẾT'"
        advice = "👉 SKIP: Bỏ qua hoặc đánh Xỉu (Under)"

    return f"""
🤖 **LIVE GPS ANALYZER**
⏱ Phút {minute} | 🥅 Tỷ số: {'Hòa' if score_diff==0 else ('Thắng' if score_diff>0 else 'Thua')}
---------------------------
📊 **Chỉ số GPS: {round(gps, 1)} / 10**
(Áp lực: {round(pressure_per_min,2)} | Hiệu quả: {round(efficiency_factor,1)} | Khẩn cấp: {round(urgency_factor,1)})
---------------------------
{signal}
{advice}
"""

# ======================================================
# PHẦN 2: LOGIC SOI KÈO PRE-MATCH (POISSON & KELLY)
# ======================================================
def poisson_probability(actual, mean):
    p = math.exp(-mean)
    for i in range(actual):
        p *= mean
        p /= (i+1)
    return p

def analyze_prematch_pro(home, away, hdp, ou, goal_h, goal_a, o1, ox, o2):
    # 1. Dự đoán tỷ số (Poisson)
    scores = []
    # Quét tỷ số từ 0-0 đến 5-5
    for h in range(6): 
        for a in range(6):
            prob = poisson_probability(h, goal_h) * poisson_probability(a, goal_a)
            scores.append({'score': f"{h}-{a}", 'prob': prob * 100})
    
    scores.sort(key=lambda x: x['prob'], reverse=True)
    top_3 = scores[:3]
    
    # Tính xG tổng (Expected Goals)
    total_xg = goal_h + goal_a
    
    # 2. Phân tích Kèo (Odds Analysis)
    pick_msg = ""
    
    # So sánh xG với Kèo Tài Xỉu
    if total_xg >= (ou + 0.4):
        pick_msg += f"👉 **TÀI (OVER) {ou}** (xG {round(total_xg,2)} > Kèo {ou})\n"
    elif total_xg <= (ou - 0.6):
        pick_msg += f"👉 **XỈU (UNDER) {ou}** (xG {round(total_xg,2)} < Kèo {ou})\n"
    else:
        pick_msg += "👉 Kèo Tài/Xỉu khá sát, nên bỏ qua.\n"

    # 3. Quản lý vốn (Kelly Criterion)
    # Tính xác suất thắng của đội được đánh giá cao hơn (theo Poisson)
    # Giả sử đánh theo đội có Odds thấp hơn (Cửa trên)
    if o1 < o2: # Chủ là cửa trên
        win_prob = sum(s['prob'] for s in scores if int(s['score'].split('-')[0]) > int(s['score'].split('-')[1])) / 100
        best_odd = o1
        team_pick = home
    else: # Khách là cửa trên
        win_prob = sum(s['prob'] for s in scores if int(s['score'].split('-')[1]) > int(s['score'].split('-')[0])) / 100
        best_odd = o2
        team_pick = away

    # Công thức Kelly: f = (bp - q) / b
    b = best_odd - 1
    q = 1 - win_prob
    kelly_f = ((b * win_prob) - q) / b
    
    # An toàn: Chỉ đánh Kelly/2
    stake_suggestion = ""
    if kelly_f > 0:
        stake_pc = round(kelly_f * 100 * 0.5, 1) # Kelly chia 2
        stake_suggestion = f"💰 **Vào tiền:** {stake_pc}% vốn cho {team_pick}"
    else:
        stake_suggestion = f"⚠️ **Cảnh báo:** Value thấp ({round(win_prob*100)}%), không nên cược lớn vào {team_pick}."

    return f"""
🔮 **PRE-MATCH PRO V6.0**
⚽ {home} vs {away}
---------------------------
🧮 **Dữ liệu Poisson:**
- Top tỷ số: {top_3[0]['score']} ({round(top_3[0]['prob'],1)}%), {top_3[1]['score']} ({round(top_3[1]['prob'],1)}%)
- Tổng bàn thắng kỳ vọng: {round(total_xg, 2)}
---------------------------
🎯 **KHUYẾN NGHỊ:**
{pick_msg}
{stake_suggestion}
"""

# ======================================================
# PHẦN 3: XỬ LÝ LỆNH TỪ NGƯỜI DÙNG
# ======================================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, """
🤖 **CHÀO MỪNG ĐẾN VỚI BOT V6.0 ULTIMATE**

1️⃣ **ĐÁNH RUNG LIVE:**
Gõ: `/calc [Phút] [DA] [On] [Off] [Góc] [HiệuSố] [ThẻĐỏ]`
Ví dụ: Phút 80, ép sân mạnh, đang hòa, không thẻ:
`/calc 80 55 6 4 5 0 0`

2️⃣ **SOI KÈO TRƯỚC TRẬN:**
Gõ: `/soi [Chủ] [Khách] [HDP] [OU] [TB_Goal_Chủ] [TB_Goal_Khách] [Odd1] [OddX] [Odd2]`
Ví dụ: Trận ManCity vs MU:
`/soi MC MU -1.5 3.5 2.8 1.2 1.3 5.0 9.0`
    """)

@bot.message_handler(commands=['calc'])
def handle_live(message):
    try:
        args = message.text.split()[1:]
        # Xử lý linh hoạt: Nếu nhập thiếu thì tự điền số 0
        params = [int(x) for x in args]
        while len(params) < 7: params.append(0) # Điền 0 vào các chỉ số thiếu
        
        res = calculate_live_gps(*params)
        bot.reply_to(message, res, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "⚠️ Lỗi: Nhập sai cú pháp. Gõ /help để xem lại.")

@bot.message_handler(commands=['soi'])
def handle_prematch(message):
    try:
        # Xóa chữ /soi và tách chuỗi
        content = message.text.replace("/soi", "").strip()
        args = content.split()
        
        if len(args) < 9:
            bot.reply_to(message, "⚠️ Thiếu thông số! Cần 9 thông số. Gõ /help xem ví dụ.")
            return

        home, away = args[0], args[1]
        # Chuyển các số liệu còn lại thành số thực (float)
        nums = [float(x) for x in args[2:]]
        
        res = analyze_prematch_pro(home, away, *nums)
        bot.reply_to(message, res, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Lỗi nhập liệu: {e}")

# ======================================================
# PHẦN 4: SERVER KEEPALIVE (CHO RENDER)
# ======================================================
@server.route('/')
def ping(): return "Bot V6.0 Ultimate is Alive!", 200

def run_web():
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    run_bot()


