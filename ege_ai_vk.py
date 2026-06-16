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
    # Если замок обновлялся меньше 15 секунд назад — значит, скрипт РЕАЛЬНО работает в фоне
    if time.time() - os.path.getmtime(LOCK_FILE) < 15:
        print("⛔ Скрипт уже запущен и работает в фоне. Выхожу.")
        sys.exit()
    else:
        # Если замок старый (скрипт упал или телефон перезагрузился) — сносим его
        os.remove(LOCK_FILE)

# Создаем свежий замок
with open(LOCK_FILE, "w") as f: f.write("work")

def compress_video():
    log("🗜️ Начинаю умное сжатие (сохранение качества текста)...")
    cmd = f"ffmpeg -y -i {FILE_PATH} -vcodec libx264 -crf 20 -preset fast {OPT_FILE}"
    subprocess.run(cmd, shell=True)
    return os.path.exists(OPT_FILE)

def upload_video():
    try:
        target_file = FILE_PATH
        if os.path.exists(FILE_PATH):
            if compress_video():
                target_file = OPT_FILE
                log(f"✅ Сжатие завершено! Размер: {os.path.getsize(OPT_FILE)} байт.")
            else:
                log("⚠️ Ошибка сжатия, отправляю оригинал.")

        log("📦 Начинаю загрузку файла в ВК...")
        api_url = "https://api.vk.com/method/"
        
        srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}, timeout=30).json()
        
        with open(target_file, 'rb') as f:
            upload_resp = requests.post(srv['response']['upload_url'], files={'file': f}, timeout=600).json()
        
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
        
        if os.path.exists(FILE_PATH): os.remove(FILE_PATH)
        if os.path.exists(OPT_FILE): os.remove(OPT_FILE)
        return True
        
    except Exception as e:
        log(f"❌ Сбой сети: {e}")
        return False

try:
    log("▶️ Скрипт активен. Вхожу в режим вечного ожидания ready.flag...")
    
    while True:
        # Каждые 2 секунды обновляем время изменения лок-файла ("пульс" скрипта)
        try:
            with open(LOCK_FILE, "w") as f: f.write("work")
        except:
            pass

        if os.path.exists(READY_FLAG):
            if not os.path.exists(FILE_PATH):
                log("⚠️ Флаг готовности получен, но файл видео отсутствует. Сброс.")
                os.remove(READY_FLAG)
                continue

            log("🔥 Обнаружен ready.flag! Начинаю обработку.")
            os.remove(READY_FLAG) 
            
            attempts = 0
            max_retries = 5
            success = False
            
            while attempts < max_retries:
                if upload_video():
                    success = True
                    break
                attempts += 1
                log(f"⚠️ Попытка {attempts}/{max_retries} не удалась. Повтор через 30 сек...")
                time.sleep(30)
            
            if not success:
                log("🚨 Не удалось отправить видео за 5 попыток. Создаю файл ошибки.")
                with open(ERROR_FLAG, "w") as f: f.write("error")
            else:
                log("💤 Видео обработано. Возврат в режим ожидания флага...")
                
        time.sleep(2) 

finally:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
    log("🏁 Скрипт завершил работу.")
