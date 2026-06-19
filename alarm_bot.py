import random
import time
import logging
import requests
from win10toast import ToastNotifier
from datetime import datetime
import os
import string


TOPIC_FILE = "topic.txt"
LOG_FILE = "alarms.log"

ALERTS = [
    ("Воздушная тревога", "air_raid"),
    ("Беспилотная опасность", "drone_danger"),
    ("Ракетная опасность", "missile_danger"),
]

INTERVAL_MEAN = 900
INTERVAL_MIN = 300
INTERVAL_MAX = 7200


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def load_or_create_topic():
    path = os.path.join(get_script_dir(), TOPIC_FILE)
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    topic = "rp-alerts-" + "".join(random.choices(string.ascii_lowercase, k=8))
    with open(path, "w") as f:
        f.write(topic)
    return topic


def setup_logging():
    path = os.path.join(get_script_dir(), LOG_FILE)
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def send_windows_toast(title, message):
    try:
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=15, threaded=True)
        return True
    except Exception as e:
        logging.error(f"Windows toast failed: {e}")
        return False


def send_ntfy(topic, title, message, tag):
    url = f"https://ntfy.sh/{topic}"
    try:
        r = requests.post(
            url,
            data=f"{title}\n\n{message}".encode("utf-8"),
            headers={
                "Title": title,
                "Tags": tag,
                "Priority": "max",
            },
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        logging.error(f"ntfy.sh error: {e}")
        return False


def random_interval():
    t = random.expovariate(1.0 / INTERVAL_MEAN) * 1.5 + random.uniform(-600, 600)
    return max(INTERVAL_MIN, min(INTERVAL_MAX, t))


def main():
    topic = load_or_create_topic()
    setup_logging()

    logging.info("=== СКРИПТ ТРЕВОГ ЗАПУЩЕН ===")
    logging.info(f"ntfy.sh топик: {topic}")

    print("=" * 50)
    print("  СКРИПТ РАНДОМАЙЗЕР ТРЕВОГ ЗАПУЩЕН")
    print(f"  Топик ntfy.sh: {topic}")
    print("  Подпишись в приложении ntfy на телефоне!")
    print("  Для остановки нажми Ctrl+C")
    print("=" * 50)

    send_windows_toast("Скрипт тревог запущен", f"Топик: {topic}")
    send_ntfy(topic, "Скрипт тревог запущен", "Рандомайзер начал работу", "rocket")

    while True:
        interval = random_interval()
        next_time = datetime.fromtimestamp(time.time() + interval)

        msg = f"Следующая тревога через {interval/60:.1f} мин (~{next_time.strftime('%H:%M')})"
        print(msg)
        logging.info(f"Интервал: {interval/60:.1f} мин")

        time.sleep(interval)

        alert_name, alert_tag = random.choice(ALERTS)
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        print(f"[{timestamp}] {alert_name}")
        logging.info(f"ТРЕВОГА: {alert_name}")

        win_ok = send_windows_toast(alert_name, f"Время: {timestamp}")
        ntfy_ok = send_ntfy(topic, alert_name, f"Время: {timestamp}", alert_tag)

        status_w = "OK" if win_ok else "FAIL"
        status_n = "OK" if ntfy_ok else "FAIL"
        logging.info(f"Windows: {status_w} | ntfy: {status_n}")

        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nСкрипт остановлен.")
        logging.info("=== СКРИПТ ОСТАНОВЛЕН ===")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        logging.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        input("Нажми Enter для выхода...")
