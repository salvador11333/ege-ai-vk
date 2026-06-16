import os
import requests
import time
import sys
import subprocess

FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
OPT_FILE = "/storage/emulated/0/MacroDroid/ege_opt.mp4"
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

# --- УМНАЯ ЗАЩИТА ОТ ПОВТОРНОГО ЗАПУСКА ---
if os.path.exists(LOCK_FILE):
    if time.time() - os.path.getmtime(LOCK_FILE) < 15:
        print("⛔ Скрипт уже запущен и работает в фоне. Выхожу.")
        sys.exit()
    else:
        os.remove(LOCK_FILE)

with open(LOCK_FILE, "w") as f: f.write("work")

def upload_video(target_file):
    try:
        log(f"📦 Отправляю файл в ВК ({os.path.getsize(target_file)} байт)...")
        api_url = "https://api.vk.com/method/"
        
        srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}, timeout=30).json()
        
        # ЖЕСТКО ЗАДАЕМ ИМЯ И ФОРМАТ, чтобы избежать ошибки 'not saved'
        with open(target_file, 'rb') as f:
            upload_resp = requests.post(srv['response']['upload_url'], files={'file': ('video.mp4', f, 'video/mp4')}, timeout=600).json()
        
        if 'error' in upload_resp or 'file' not in upload_resp:
            log(f"❌ Ошибка ВК при загрузке: {upload_resp}")
            return False

        doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload_resp['file']}, timeout=30).json()
        
        attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
        requests.get(api_url + "wall.post", params={
            "access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, 
            "attachments": attachment, "message": "📹 Новое видео."
        }, timeout=30)
        
        log("✅ Успешно отправлено!")
        with open(SUCCESS_FLAG, "w") as f: f.write("ok")
        
        # Удаляем мусор
        if os.path.exists(FILE_PATH): os.remove(FILE_PATH)
        if os.path.exists(OPT_FILE): os.remove(OPT_FILE)
        return True
        
    except Exception as e:
        log(f"❌ Сбой сети: {e}")
        return False

try:
    log("▶️ Скрипт активен. Жду ready.flag от MacroDroid...")
    
    while True:
        try:
            with open(LOCK_FILE, "w") as f: f.write("work")
        except:
            pass

        if os.path.exists(READY_FLAG):
            if not os.path.exists(FILE_PATH):
                log("⚠️ Флаг есть, а видео нет! Сброс.")
                os.remove(READY_FLAG)
                continue

            log("🔥 Обнаружен ready.flag! Приступаю к работе.")
            os.remove(READY_FLAG) 
            
            # --- 1. ЭТАП СЖАТИЯ (ВЫПОЛНЯЕТСЯ ТОЛЬКО 1 РАЗ) ---
            target_file = FILE_PATH
            log("🗜️ Начинаю турбо-сжатие (ultrafast)...")
            
            # loglevel error убирает системный спам с экрана
            cmd = f"ffmpeg -y -i {FILE_PATH} -vcodec libx264 -crf 22 -preset ultrafast -loglevel error {OPT_FILE}"
            subprocess.run(cmd, shell=True)
            
            if os.path.exists(OPT_FILE) and os.path.getsize(OPT_FILE) > 0:
                target_file = OPT_FILE
                log(f"✅ Сжатие завершено! Новый размер: {os.path.getsize(OPT_FILE)} байт.")
            else:
                log("⚠️ Ошибка сжатия, буду отправлять тяжелый оригинал.")

            # --- 2. ЭТАП ОТПРАВКИ (5 ПОПЫТОК) ---
            attempts = 0
            max_retries = 5
            success = False
            
            while attempts < max_retries:
                if upload_video(target_file):
                    success = True
                    break
                attempts += 1
                log(f"⚠️ Попытка отправки {attempts}/{max_retries} не удалась. Повтор через 30 сек...")
                time.sleep(30)
            
            if not success:
                log("🚨 Сеть мертва (5/5 провалов). Сигнал ошибки.")
                with open(ERROR_FLAG, "w") as f: f.write("error")
            else:
                log("💤 Видео на стене. Снова жду команду...")
                
        time.sleep(2) 

finally:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
    log("🏁 Скрипт остановлен.")
