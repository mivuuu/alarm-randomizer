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

# Path to your custom map image
MAP_FILE = os.path.join(SCRIPT_DIR, "map.png")

# Coordinates of each region center on map.png — fill from the other model!
# Format: region_id: (x, y)
# Replace ALL zeros with actual coordinates from your map image.
REGION_COORDS = {
    1: (220, 520), 2: (225, 590), 3: (475, 345), 4: (855, 245), 5: (740, 340),
    6: (675, 360), 7: (645, 410), 8: (565, 335), 9: (555, 385), 10: (595, 410),
    11: (550, 460), 12: (495, 485), 13: (580, 515), 14: (640, 485), 15: (850, 360),
    16: (775, 415), 17: (735, 465), 18: (680, 515), 19: (610, 570), 20: (645, 615),
    21: (560, 620), 22: (550, 560), 23: (475, 550), 24: (485, 605), 25: (400, 560),
    26: (435, 605), 27: (430, 640), 28: (480, 675), 29: (410, 690), 30: (435, 740),
    31: (485, 770), 32: (510, 825), 33: (115, 710), 34: (435, 470),
}

# Fallback grid layout (used when coordinates not set)
GRID_POSITIONS = [
    (0,0), (1,0), (2,0), (3,0), (4,0), (5,0),
    (0,1), (1,1), (2,1), (3,1), (4,1), (5,1),
    (0,2), (1,2), (2,2), (3,2), (4,2), (5,2),
    (0,3), (1,3), (2,3), (3,3), (4,3), (5,3),
    (0,4), (1,4), (2,4), (3,4), (4,4), (5,4),
    (0,5), (1,5), (2,5), (3,5),
]
GRID_W = 1000
GRID_H = 720
GRID_PAD_L = 60
GRID_PAD_T = 50
GRID_CELL_W = (GRID_W - GRID_PAD_L - 40) / 6
GRID_CELL_H = (GRID_H - GRID_PAD_T - 40) / 6


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


def get_grid_coords(grid_col, grid_row):
    x = GRID_PAD_L + grid_col * GRID_CELL_W + GRID_CELL_W / 2
    y = GRID_PAD_T + grid_row * GRID_CELL_H + GRID_CELL_H / 2
    return int(x), int(y)


def get_region_data():
    data = []
    for i, (rid, name, weight) in enumerate(REGIONS):
        col, row = GRID_POSITIONS[i]
        cx, cy = get_grid_coords(col, row)
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
    coords_set = any(v != (0, 0) for v in REGION_COORDS.values())
    if coords_set and os.path.exists(MAP_FILE):
        return draw_map_image(highlight_ids)
    if not coords_set and os.path.exists(MAP_FILE):
        print("  ВНИМАНИЕ: координаты регионов не заданы. Используется схема.")
    return draw_map_grid(highlight_ids)


def draw_map_image(highlight_ids):
    img = Image.open(MAP_FILE).convert("RGB")
    img_w, img_h = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    font_num = load_font(max(10, min(img_w, img_h) // 60))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)

    for rid, name, weight in REGIONS:
        x, y = REGION_COORDS.get(rid, (0, 0))
        if x == 0 and y == 0:
            continue
        r = max(6, min(img_w, img_h) // 80)

        if rid in highlight_ids:
            for gr in range(r * 3, r, -max(1, r // 2)):
                alpha = max(20, 80 - gr * 3)
                o_draw.ellipse([x - gr, y - gr, x + gr, y + gr], fill=(200, 40, 40, alpha))
            o_draw.ellipse([x - r, y - r, x + r, y + r], fill=(220, 30, 30, 220))
            o_draw.ellipse([x - r + 3, y - r + 3, x + r - 3, y + r - 3], fill=(255, 80, 80, 220))
        else:
            o_draw.ellipse([x - r // 2, y - r // 2, x + r // 2, y + r // 2], fill=(60, 60, 60, 40))

        if font_num:
            o_draw.text((x - 5, y - r - 14), str(rid), fill=(255, 255, 255), font=font_num, stroke_width=2, stroke_fill=(0, 0, 0))

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    font_title = load_font(max(16, min(img_w, img_h) // 40))
    if font_title:
        draw2 = ImageDraw.Draw(img)
        tw = draw2.textlength("КАРТА ГОСУДАРСТВА", font=font_title)
        bx = int((img_w - tw) / 2 - 12)
        draw2.rectangle([bx, 6, bx + int(tw) + 24, 34], fill=(255, 255, 255, 200))
        draw2.text((img_w / 2, 20), "КАРТА ГОСУДАРСТВА", fill=(60, 40, 20), font=font_title, anchor="mt")
    return img


def draw_map_grid(highlight_ids):
    img = Image.new("RGB", (GRID_W, GRID_H), (245, 235, 215))
    draw = ImageDraw.Draw(img, "RGBA")
    font_reg = load_font(13)
    font_big = load_font(16)

    regions = get_region_data()

    for rid, name, weight, cx, cy in regions:
        col, row = GRID_POSITIONS[regions.index((rid, name, weight, cx, cy))]
        x1 = GRID_PAD_L + col * GRID_CELL_W + 4
        y1 = GRID_PAD_T + row * GRID_CELL_H + 4
        x2 = GRID_PAD_L + (col + 1) * GRID_CELL_W - 4
        y2 = GRID_PAD_T + (row + 1) * GRID_CELL_H - 4

        bg = (235, 222, 195)
        draw.rectangle([x1, y1, x2, y2], fill=bg, outline=(180, 160, 120), width=1)

        if weight == 5:
            draw.rectangle([x1, y1, x2, y2], outline=(200, 50, 50), width=2)

        if rid in highlight_ids:
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(overlay)
            o_draw.rectangle([x1, y1, x2, y2], fill=(200, 40, 40, 120))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img, "RGBA")

        if font_reg:
            draw.text((cx - 6, cy - 12), str(rid), fill=(80, 60, 40), font=font_reg)
            short = name if len(name) < 14 else name[:12] + "."
            draw.text((cx - 6, cy + 4), short, fill=(120, 100, 80), font=font_reg)

    if font_big:
        draw.text((GRID_W / 2, 15), "КАРТА ГОСУДАРСТВА", fill=(80, 60, 40), font=font_big, anchor="mt")
    if font_reg:
        draw.text((GRID_W - 180, GRID_H - 60), "— фронт (кр.)", fill=(200, 50, 50), font=font_reg)
        draw.text((GRID_W - 180, GRID_H - 44), "— тыл (зел.)", fill=(80, 150, 80), font=font_reg)

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


def run_alert_cycle(alert_name, strength, selected):
    """Send one alert + all-clear (used both in main loop and test mode)."""
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    ids = [r[0] for r in selected]
    names = [r[1] for r in selected]

    print(f"[{timestamp}] {alert_name} (сила {strength}, {len(selected)} рег.)")
    logging.info(f"ALERT: {alert_name}, strength={strength}, regions={len(selected)}")
    send_termux_notification(alert_name, f"Сила: {strength} | Регионы ({len(selected)}): {', '.join(names)}")

    caption = build_caption(alert_name, strength, selected, timestamp)
    img = draw_map(ids)
    ok = send_telegram_photo(img, caption)
    logging.info(f"Telegram: {'OK' if ok else 'FAIL'}")
    if not ok:
        print("  Ошибка отправки в Telegram!")

    # All-clear phase
    timestamp_ac = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    caption_ac = build_caption(alert_name, strength, selected, timestamp_ac, is_clear=True)
    img_ac = draw_map([])
    ok_ac = send_telegram_photo(img_ac, caption_ac)
    logging.info(f"Telegram all-clear: {'OK' if ok_ac else 'FAIL'}")
    print(f"  Отбой отправлен")


def print_help():
    print("Использование: python termux_bot.py [опции]")
    print()
    print("Опции:")
    print("  --help          Показать эту справку")
    print("  --test          Отправить одну тестовую тревогу и выйти")
    print("  --min N         Мин. интервал между тревогами, мин (по умолч. 5)")
    print("  --max N         Макс. интервал между тревогами, мин (по умолч. 120)")
    print("  --ac-min N      Мин. интервал до отбоя, мин (по умолч. 1)")
    print("  --ac-max N      Макс. интервал до отбоя, мин (по умолч. 30)")
    print()
    print("Пример: python termux_bot.py --min 10 --max 60 --ac-min 2 --ac-max 15")


def main():
    setup_logging()
    load_config()

    # Parse args
    args = sys.argv[1:]
    is_test = "--test" in args
    if "--help" in args or "-h" in args:
        print_help()
        return

    # Helper to get arg value
    def get_arg(flag, default):
        if flag in args:
            idx = args.index(flag) + 1
            if idx < len(args):
                return int(args[idx])
        return default

    min_interval = get_arg("--min", 5)
    max_interval = get_arg("--max", 120)
    ac_min = get_arg("--ac-min", 1)
    ac_max = get_arg("--ac-max", 30)

    if min_interval > max_interval:
        min_interval, max_interval = max_interval, min_interval
        print("  Мин и макс интервал поменяны местами")
    if ac_min > ac_max:
        ac_min, ac_max = ac_max, ac_min
        print("  Отбой мин и макс поменяны местами")

    if is_test:
        logging.info("=== ТЕСТОВЫЙ ЗАПУСК ===")
        print("Тестовый запуск — отправляю одну тревогу...")
        alert_name, alert_tag = random.choice(ALERTS)
        strength = random_strength()
        count = region_count(strength)
        selected = select_regions(count)
        run_alert_cycle(alert_name, strength, selected)
        print("Тест завершён.")
        return

    logging.info("=== TERMUX БОТ ЗАПУЩЕН ===")
    print("=" * 50)
    print("  TERMUX БОТ ТРЕВОГ + КАРТА")
    print(f"  Канал: {CHANNEL_ID}")
    print(f"  Интервал: {min_interval}-{max_interval} мин")
    print(f"  Отбой: {ac_min}-{ac_max} мин")
    print("  Для остановки Ctrl+C")
    print("=" * 50)

    send_termux_notification("Бот тревог запущен", f"Канал: {CHANNEL_ID}")

    while True:
        interval = random_interval(min_interval, max_interval)
        dt = datetime.fromtimestamp(time.time() + interval)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] След. тревога через {interval/60:.1f} мин (~{dt.strftime('%H:%M')})")
        logging.info(f"Interval: {interval/60:.1f} min")
        time.sleep(interval / 1000)

        alert_name, alert_tag = random.choice(ALERTS)
        strength = random_strength()
        count = region_count(strength)
        selected = select_regions(count)
        run_alert_cycle(alert_name, strength, selected)

        print(f"  Ожидание перед след. циклом")
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
