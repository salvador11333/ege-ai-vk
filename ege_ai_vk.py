import os
import requests
import time
import sys
import shutil
import threading

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

def upload_worker(target_file):
    """Эта функция работает в фоне, параллельно основному скрипту"""
    attempts = 0
    max_retries = 5
    success = False
    api_url = "https://api.vk.com/method/"
    
    while attempts < max_retries:
        try:
            log(f"🚀 Поток запущен. Отправляю {target_file} (Попытка {attempts+1}/{max_retries})")
            
            srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}, timeout=30).json()
            
            with open(target_file, 'rb') as f:
                upload_resp = requests.post(srv['response']['upload_url'], files={'file': ('video.mp4', f, 'video/mp4')}, timeout=1200).json()
            
            if 'error' in upload_resp or 'file' not in upload_resp:
                log(f"❌ Ошибка ВК для {target_file}: {upload_resp}")
                attempts += 1
                time.sleep(30)
                continue

            doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload_resp['file']}, timeout=30).json()
            
            attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
            requests.get(api_url + "wall.post", params={
                "access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, 
                "attachments": attachment, "message": "📹 Видео из параллельного потока."
            }, timeout=30)
            
            log(f"✅ Успешно отправлено: {target_file}")
            with open(SUCCESS_FLAG, "w") as f: f.write("ok")
            success = True
            break
            
        except Exception as e:
            log(f"❌ Сбой сети в потоке {target_file}: {e}")
            attempts += 1
            time.sleep(30)

    # Удаляем ТОЛЬКО КОПИЮ после успеха или 5 провалов.
    if os.path.exists(target_file):
        os.remove(target_file)
        log(f"🗑️ Временная копия {target_file} удалена.")
        
    if not success:
        with open(ERROR_FLAG, "w") as f: f.write("error")
        log(f"🚨 Файл {target_file} не отправлен. Лимит попыток.")


try:
    log("▶️ Скрипт активен (МНОГОПОТОЧНОСТЬ). Ожидаю ready.flag...")
    while True:
        with open(LOCK_FILE, "w") as f: f.write("work")
        
        if os.path.exists(READY_FLAG):
            if not os.path.exists(FILE_PATH):
                log("⚠️ Флаг есть, а оригинала видео нет! Сброс.")
                os.remove(READY_FLAG)
                continue
            
            log("🔥 Обнаружен ready.flag! Беру видео в работу.")
            
            # 1. Генерируем уникальное имя для копии (по текущему времени)
            timestamp = time.strftime("%H%M%S")
            copy_path = f"/storage/emulated/0/MacroDroid/ege_copy_{timestamp}.mp4"
            
            # 2. Моментально копируем файл
            log(f"🗂️ Делаю дубликат: {copy_path}")
            shutil.copy2(FILE_PATH, copy_path)
            
            # 3. Сразу сносим флаг, чтобы скрипт был готов принять следующее видео
            os.remove(READY_FLAG)
            
            # 4. Запускаем отправку в параллельном потоке
            log("🔄 Передаю дубликат рабочему потоку. Возвращаюсь в засаду...")
            t = threading.Thread(target=upload_worker, args=(copy_path,))
            t.start()
                
        time.sleep(2)
        
finally:
    if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)
    log("🏁 Скрипт остановлен.")
