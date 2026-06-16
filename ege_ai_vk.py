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

if os.path.exists(LOCK_FILE):
    if time.time() - os.path.getmtime(LOCK_FILE) > 1800:
        os.remove(LOCK_FILE)
    else:
        log("⛔ Скрипт уже запущен, выхожу.")
        sys.exit()

with open(LOCK_FILE, "w") as f: f.write("work")

def attempt_upload():
    # Ждем отмашку от MacroDroid
    if not os.path.exists(READY_FLAG) or not os.path.exists(FILE_PATH): 
        return "not_ready"
    
    try:
        # Убираем флаг, чтобы не начать отправлять дважды
        os.remove(READY_FLAG)
        log(f"📦 Получена отмашка от MacroDroid! Отправляю...")
        
        api_url = "https://api.vk.com/method/"
        srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}, timeout=30).json()
        
        with open(FILE_PATH, 'rb') as f:
            upload_resp = requests.post(srv['response']['upload_url'], files={'file': f}, timeout=600).json()
        
        if 'error' in upload_resp or 'file' not in upload_resp:
            log(f"❌ Ошибка ВК при загрузке: {upload_resp}")
            return "error"

        doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload_resp['file']}, timeout=30).json()
        
        attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
        requests.get(api_url + "wall.post", params={
            "access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, 
            "attachments": attachment, "message": "📹 Новое видео."
        }, timeout=30)
        
        log("✅ Успешно отправлено!")
        with open(SUCCESS_FLAG, "w") as f: f.write("ok")
        os.remove(FILE_PATH)
        return "success"
        
    except Exception as e:
        log(f"❌ Сбой сети: {e}")
        # Если сеть отвалилась, возвращаем флаг на место, чтобы скрипт попробовал этот же файл снова
        with open(READY_FLAG, "w") as f: f.write("ok")
        return "error"

try:
    max_retries = 5
    attempts = 0
    
    log("▶️ Запуск, жду команду от MacroDroid...")
    while attempts < max_retries:
        status = attempt_upload()
        
        if status == "success":
            break
        elif status == "error":
            attempts += 1
            log(f"⚠️ Попытка сети {attempts}/{max_retries} не удалась. Жду 30 сек...")
            time.sleep(30)
        elif status == "not_ready":
            time.sleep(3) # Просто тихо спим, пока MacroDroid не создаст файл

    if attempts >= max_retries:
        log("🚨 Лимит попыток исчерпан. Создаю сигнал ошибки.")
        with open(ERROR_FLAG, "w") as f: f.write("error")

finally:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
