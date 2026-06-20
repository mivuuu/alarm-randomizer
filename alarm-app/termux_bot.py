import random
import time
import logging
import requests
import subprocess
import json
import os
import sys
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import math

# ========== CONFIG ==========
BOT_TOKEN = ""
CHANNEL_ID = ""
# ============================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "bot.log")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "bot_config.json")

ALERTS = [
    ("Воздушная тревога", "air_raid"),
    ("Беспилотная опасность", "drone_danger"),
    ("Ракетная опасность", "missile_danger"),
]

REGIONS = [
    (1,  "Калантия", 5),
    (2,  "Альтерия", 5),
    (3,  "Сильвания", 5),
    (4,  "Таврия", 5),
    (5,  "Валентия", 5),
    (6,  "Иллирия", 5),
    (7,  "Астралия", 5),
    (8,  "Лимнида", 5),
    (9,  "Монтания", 5),
    (10, "Меридиония", 5),
    (11, "Эстерия", 5),
    (12, "Гесперия", 3),
    (13, "Ориентия", 3),
    (14, "Люциния", 3),
    (15, "Нереида", 3),
    (16, "Аргезия", 3),
    (17, "Наяда", 3),
    (18, "Люмена", 3),
    (19, "Солария", 3),
    (20, "Небулия", 3),
    (21, "Медиолания", 3),
    (22, "Джаннат-аль-амн", 3),
    (23, "Мариния", 3),
    (24, "Иудейская автономия", 1),
    (25, "Салабимия", 1),
    (26, "Эндор", 1),
    (27, "Сидерия", 1),
    (28, "Селения", 1),
    (29, "Кастелия", 1),
    (30, "Окцидентия", 1),
    (31, "Виридия", 1),
    (32, "Тенебрия", 1),
    (33, "Ойл", 1),
    (34, "Гесперидия", 1),
]

# Map grid layout (column, row) from 0,0
GRID_POSITIONS = [
    (0,0), (1,0), (2,0), (3,0), (4,0), (5,0),
    (0,1), (1,1), (2,1), (3,1), (4,1), (5,1),
    (0,2), (1,2), (2,2), (3,2), (4,2), (5,2),
    (0,3), (1,3), (2,3), (3,3), (4,3), (5,3),
    (0,4), (1,4), (2,4), (3,4), (4,4), (5,4),
    (0,5), (1,5), (2,5), (3,5),
]

MAP_W = 1000
MAP_H = 720
PAD_L = 60
PAD_T = 50
CELL_W = (MAP_W - PAD_L - 40) / 6
CELL_H = (MAP_H - PAD_T - 40) / 6

REGION_COLORS = {
    5: (220, 60, 60, 40),
    3: (220, 200, 60, 30),
    1: (100, 180, 100, 25),
}


def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_config():
    global BOT_TOKEN, CHANNEL_ID
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            BOT_TOKEN = cfg.get("token", "")
            CHANNEL_ID = cfg.get("channel_id", "")
    if not BOT_TOKEN or not CHANNEL_ID:
        print("=" * 50)
        print("ПЕРВЫЙ ЗАПУСК — настройка бота")
        BOT_TOKEN = input("Введи токен Telegram-бота: ").strip()
        CHANNEL_ID = input("Введи ID канала (например -1001234567890): ").strip()
        with open(CONFIG_FILE, "w") as f:
            json.dump({"token": BOT_TOKEN, "channel_id": CHANNEL_ID}, f)
        print("Сохранено в bot_config.json\n")
        logging.info("Config saved")


def get_coords(grid_col, grid_row):
    x = PAD_L + grid_col * CELL_W + CELL_W / 2
    y = PAD_T + grid_row * CELL_H + CELL_H / 2
    return int(x), int(y)


def get_region_data():
    data = []
    for i, (rid, name, weight) in enumerate(REGIONS):
        col, row = GRID_POSITIONS[i]
        cx, cy = get_coords(col, row)
        data.append((rid, name, weight, cx, cy))
    return data


def load_font(size):
    paths = [
        "/system/fonts/DroidSansFallback.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    try:
        font_small = ImageFont.load_default()
        return font_small
    except:
        return None


def draw_map(highlight_ids):
    img = Image.new("RGB", (MAP_W, MAP_H), (245, 235, 215))
    draw = ImageDraw.Draw(img, "RGBA")
    font_reg = load_font(13)
    font_big = load_font(16)

    regions = get_region_data()

    # Draw land/region cells
    for rid, name, weight, cx, cy in regions:
        col, row = GRID_POSITIONS[regions.index((rid, name, weight, cx, cy))]
        x1 = PAD_L + col * CELL_W + 4
        y1 = PAD_T + row * CELL_H + 4
        x2 = PAD_L + (col + 1) * CELL_W - 4
        y2 = PAD_T + (row + 1) * CELL_H - 4

        bg = (235, 222, 195)
        draw.rectangle([x1, y1, x2, y2], fill=bg, outline=(180, 160, 120), width=1)

        # Frontline border (weight 5) — red accent
        if weight == 5:
            draw.rectangle([x1, y1, x2, y2], outline=(200, 50, 50), width=2)

        # Highlight if in alert
        if rid in highlight_ids:
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(overlay)
            o_draw.rectangle([x1, y1, x2, y2], fill=(200, 40, 40, 120))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img, "RGBA")

        # Region number
        if font_reg:
            draw.text((cx - 6, cy - 12), str(rid), fill=(80, 60, 40), font=font_reg)
            # Name (truncated)
            short = name if len(name) < 14 else name[:12] + "."
            draw.text((cx - 6, cy + 4), short, fill=(120, 100, 80), font=font_reg)

    # Title and legend
    if font_big:
        draw.text((MAP_W / 2, 15), "КАРТА ГОСУДАРСТВА", fill=(80, 60, 40), font=font_big, anchor="mt")
    legend_x = MAP_W - 180
    legend_y = MAP_H - 60
    if font_reg:
        draw.text((legend_x, legend_y), "— фронт (кр.)", fill=(200, 50, 50), font=font_reg)
        draw.text((legend_x, legend_y + 16), "— тыл (зел.)", fill=(80, 150, 80), font=font_reg)

    return img


def send_telegram_photo(image, caption):
    if not BOT_TOKEN or not CHANNEL_ID:
        logging.error("Bot not configured")
        return False
    try:
        buf = BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {"photo": ("map.png", buf, "image/png")}
        data = {"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"}
        r = requests.post(url, files=files, data=data, timeout=30)
        return r.status_code == 200
    except Exception as e:
        logging.error(f"Telegram send failed: {e}")
        return False


def send_termux_notification(title, message):
    try:
        subprocess.run(
            ["termux-notification", "--title", title, "--content", message, "--priority", "high"],
            capture_output=True, timeout=5,
        )
    except Exception as e:
        logging.error(f"termux-notification failed: {e}")


def random_interval(min_min, max_min):
    min_ms = min_min * 60_000
    max_ms = max_min * 60_000
    mean = (min_ms + max_ms) / 2
    jitter = (max_ms - min_ms) / 8
    raw = (-math.log(random.random())) * mean * 1.5 + random.randint(-int(jitter), int(jitter))
    return int(max(min_ms, min(max_ms, raw)))


def random_allclear_interval(ac_min, ac_max):
    return random.randint(ac_min * 60_000, ac_max * 60_000)


def random_strength():
    raw = (-math.log(random.random())) * 2.5 + 1
    return max(1, min(10, int(raw)))


def region_count(strength):
    return {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 4, 7: random.randint(4, 5),
            8: random.randint(5, 7), 9: random.randint(7, 9), 10: random.randint(9, 12)}.get(strength, 1)


def select_regions(count):
    pool = list(REGIONS)
    result = []
    n = min(count, len(pool))
    for _ in range(n):
        total = sum(w for _, _, w in pool)
        r = random.random() * total
        idx = 0
        for i, (_, _, w) in enumerate(pool):
            r -= w
            if r <= 0:
                idx = i
                break
        result.append(pool[idx])
        pool.pop(idx)
    return result


def build_caption(alert_name, strength, selected_regions, timestamp, is_clear=False):
    names = [r[1] for r in selected_regions]
    ids = [str(r[0]) for r in selected_regions]
    regions_str = ", ".join(names)

    if is_clear:
        text = (
            f"<b>{alert_name} — ОТБОЙ</b>\n\n"
            f"Регионы ({len(selected_regions)}): {regions_str}\n"
            f"Угроза миновала\n\n"
            f"<i>{timestamp}</i>"
        )
    else:
        text = (
            f"<b>{alert_name}</b>\n\n"
            f"Сила атаки: {strength}\n"
            f"Регионы ({len(selected_regions)}): {regions_str}\n"
            f"Номера: {', '.join(ids)}\n\n"
            f"<i>{timestamp}</i>"
        )
    return text


def main():
    setup_logging()
    load_config()

    logging.info("=== TERMUX БОТ ЗАПУЩЕН ===")

    print("=" * 50)
    print("  TERMUX БОТ ТРЕВОГ + КАРТА")
    print(f"  Канал: {CHANNEL_ID}")
    print("  Для остановки Ctrl+C")
    print("=" * 50)

    send_termux_notification("Бот тревог запущен", f"Канал: {CHANNEL_ID}")

    while True:
        min_interval = 5
        max_interval = 120
        ac_min = 1
        ac_max = 30

        # Phase 1: wait for alert
        interval = random_interval(min_interval, max_interval)
        dt = datetime.fromtimestamp(time.time() + interval)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] След. тревога через {interval/60:.1f} мин (~{dt.strftime('%H:%M')})")
        logging.info(f"Interval: {interval/60:.1f} min")
        time.sleep(interval / 1000)

                # Generate alert
        alert_name, alert_tag = random.choice(ALERTS)
        strength = random_strength()
        count = region_count(strength)
        selected = select_regions(count)
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        print(f"[{timestamp}] {alert_name} (сила {strength}, {count} рег.)")
        logging.info(f"ALERT: {alert_name}, strength={strength}, regions={len(selected)}")

        names = [r[1] for r in selected]
        ids = [r[0] for r in selected]
        local_msg = f"Сила: {strength} | Регионы ({len(selected)}): {', '.join(names)}"
        send_termux_notification(alert_name, local_msg)

        # Draw map + send to Telegram
        caption = build_caption(alert_name, strength, selected, timestamp)
        img = draw_map(ids)
        ok = send_telegram_photo(img, caption)
        logging.info(f"Telegram: {'OK' if ok else 'FAIL'}")

        # Phase 2: wait for all clear
        ac_interval = random_allclear_interval(ac_min, ac_max)
        dt_ac = datetime.fromtimestamp(time.time() + ac_interval)
        print(f"  Отбой через {ac_interval/60000:.1f} мин (~{dt_ac.strftime('%H:%M')})")
        time.sleep(ac_interval / 1000)

        # Send all clear
        timestamp_ac = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        caption_ac = build_caption(alert_name, strength, selected, timestamp_ac, is_clear=True)
        img_ac = draw_map([])  # Empty highlight = normal map
        ok_ac = send_telegram_photo(img_ac, caption_ac)
        logging.info(f"Telegram all-clear: {'OK' if ok_ac else 'FAIL'}")

        print(f"  Отбой отправлен")
        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nБот остановлен.")
        logging.info("=== БОТ ОСТАНОВЛЕН ===")
    except Exception as e:
        print(f"\nОшибка: {e}")
        logging.error(f"FATAL: {e}", exc_info=True)
