import random
import time
import logging
import requests
from datetime import datetime
import os
import string
import sys
import subprocess


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
    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        return topic
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


def send_termux_notification(title, message):
    try:
        subprocess.run(
            ["termux-notification", "--title", title, "--content", message, "--priority", "high"],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception as e:
        logging.error(f"termux-notification failed: {e}")
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


def wakelock_acquire():
    try:
        subprocess.run(["termux-wake-lock"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def wakelock_release():
    try:
        subprocess.run(["termux-wake-unlock"], capture_output=True, timeout=5)
    except Exception:
        pass


def main():
    topic = load_or_create_topic()
    setup_logging()

    wakelock_acquire()

    logging.info("=== СКРИПТ ТРЕВОГ ЗАПУЩЕН (TERMUX) ===")
    logging.info(f"ntfy.sh топик: {topic}")

    print("=" * 50)
    print("  СКРИПТ РАНДОМАЙЗЕР ТРЕВОГ ЗАПУЩЕН")
    print(f"  Топик ntfy.sh: {topic}")
    print("  Подпишись в приложении ntfy на телефоне!")
    print("  Для остановки нажми Ctrl+C")
    print("=" * 50)

    send_termux_notification("Скрипт тревог запущен", f"Топик ntfy: {topic}")
    send_ntfy(topic, "Скрипт тревог запущен", "Рандомайзер начал работу", "rocket")

    while True:
        interval = random_interval()
        next_time = datetime.fromtimestamp(time.time() + interval)

        line = f"Следующая тревога через {interval/60:.1f} мин (~{next_time.strftime('%H:%M')})"
        print(line)
        logging.info(f"Интервал: {interval/60:.1f} мин")

        time.sleep(interval)

        alert_name, alert_tag = random.choice(ALERTS)
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        line = f"[{timestamp}] {alert_name}"
        print(line)
        logging.info(f"ТРЕВОГА: {alert_name}")

        notify_msg = f"Время: {timestamp}"

        t_ok = send_termux_notification(alert_name, notify_msg)
        n_ok = send_ntfy(topic, alert_name, notify_msg, alert_tag)

        status_t = "OK" if t_ok else "FAIL"
        status_n = "OK" if n_ok else "FAIL"
        logging.info(f"Termux: {status_t} | ntfy: {status_n}")

        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nСкрипт остановлен.")
        logging.info("=== СКРИПТ ОСТАНОВЛЕН ===")
        wakelock_release()
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        logging.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        wakelock_release()
        input("Нажми Enter для выхода...")
