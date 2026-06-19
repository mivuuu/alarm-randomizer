import random
import time
import logging
import requests
from datetime import datetime
import os
import string
import sys


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

    logging.info("=== СКРИПТ ТРЕВОГ ЗАПУЩЕН (СЕРВЕР) ===")
    logging.info(f"ntfy.sh топик: {topic}")

    msg = f"СКРИПТ РАНДОМАЙЗЕР ТРЕВОГ ЗАПУЩЕН | Топик: {topic}"
    print(msg, flush=True)

    send_ntfy(topic, "Скрипт тревог запущен", "Рандомайзер начал работу", "rocket")

    while True:
        interval = random_interval()
        next_time = datetime.fromtimestamp(time.time() + interval)

        msg = f"[{datetime.now().strftime('%H:%M:%S')}] Следующая тревога через {interval/60:.1f} мин (~{next_time.strftime('%H:%M')})"
        print(msg, flush=True)
        logging.info(f"Интервал: {interval/60:.1f} мин")

        time.sleep(interval)

        alert_name, alert_tag = random.choice(ALERTS)
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        msg = f"[{timestamp}] {alert_name}"
        print(msg, flush=True)
        logging.info(f"ТРЕВОГА: {alert_name}")

        ntfy_ok = send_ntfy(topic, alert_name, f"Время: {timestamp}", alert_tag)
        status_n = "OK" if ntfy_ok else "FAIL"
        logging.info(f"ntfy: {status_n}")

        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nСкрипт остановлен.", flush=True)
        logging.info("=== СКРИПТ ОСТАНОВЛЕН ===")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}", flush=True)
        logging.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
