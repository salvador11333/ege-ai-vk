import os
import requests
import time
import sys

FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
LOG_FILE = "/data/data/com.termux/files/home/bot_log.txt"
LOCK_FILE = "/data/data/com.termux/files/home/script.lock"

# --- ФЛАГИ УПРАВЛЕНИЯ ---
READY_FLAG = "/storage/emulated/0/MacroDroid/ready.flag"
SUCCESS_FLAG = "/storage/emulated/0/MacroDroid/success.flag"
ERROR_FLAG = "/storage/emulated/0/MacroDroid/error.flag"

VK_TOKEN = "vk1.a.lsRykF02XWyz7uuaOpLUZpneg0twi5dgZhUE40c0nwiJ7JSVYnis2mTbXT6XVgNRYhy6eWZIp_Hc2hO8P2Fw9aDiHuukrw2bd7xD-UL8AF6haARKltenqLCpiBLejcmKU6E-t1_MEu--E24WtAt2ckTymp8wbdrGrZyOscNWbaV_KkIFMf5AteYwgBy9to40IDG1maSGz9JHC4b0LoGpMQ"
GROUP_ID = 239501197

def log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.ctime()} - {text}\n")
    print(text)

# Защита от дублей
if os.path.exists(LOCK_FILE):
    if time.time() - os.path.getmtime(LOCK_FILE) < 15:
        print("⛔ Скрипт уже запущен.")
        sys.exit()
    else:
        os.remove(LOCK_FILE)

with open(LOCK_FILE, "w") as f: f.write("work")

def upload_raw_video():
    try:
        if not os.path.exists(FILE_PATH):
            log("❌ Файл для отправки не найден!")
            return False
            
        log(f"📦 Начинаю прямую отправку оригинала ({os.path.getsize(FILE_PATH)} байт)...")
        api_url = "https://api.vk.com/method/"
        
        # 1. Получаем сервер
        srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}, timeout=30).json()
        
        # 2. Шлем файл (тайм-аут 20 минут)
        with open(FILE_PATH, 'rb') as f:
            upload_resp = requests.post(srv['response']['upload_url'], files={'file': ('video.mp4', f, 'video/mp4')}, timeout=1200).json()
        
        if 'error' in upload_resp or 'file' not in upload_resp:
            log(f"❌ Ошибка ВК: {upload_resp}")
            return False

        # 3. Сохраняем
        doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload_resp['file']}, timeout=30).json()
        
        # 4. Постим
        attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
        requests.get(api_url + "wall.post", params={
            "access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, 
            "attachments": attachment, "message": "📹 Видео без сжатия."
        }, timeout=30)
        
        log("✅ Успешно отправлено!")
        return True
        
    except Exception as e:
        log(f"❌ Сбой сети/сервера: {e}")
        return False

try:
    log("▶️ Скрипт активен (Без сжатия). Ожидаю ready.flag...")
    while True:
        with open(LOCK_FILE, "w") as f: f.write("work")
        
        if os.path.exists(READY_FLAG):
            log("🔥 Обнаружен ready.flag! Начинаю отправку оригинала.")
            os.remove(READY_FLAG)
            
            if upload_raw_video():
                with open(SUCCESS_FLAG, "w") as f: f.write("ok")
                if os.path.exists(FILE_PATH): os.remove(FILE_PATH)
            else:
                with open(ERROR_FLAG, "w") as f: f.write("error")
                
        time.sleep(2)
finally:
    if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
    log("🏁 Скрипт остановлен.")
