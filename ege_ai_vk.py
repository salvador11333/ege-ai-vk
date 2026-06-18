import os
import requests
import time
import sys
import glob
import threading

FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
QUEUE_DIR = "/storage/emulated/0/MacroDroid/"
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

# --- ЗАЩИТА ОТ ДВОЙНОГО ЗАПУСКА ---
if os.path.exists(LOCK_FILE):
    if time.time() - os.path.getmtime(LOCK_FILE) < 15:
        print("⛔ Скрипт уже работает в фоне.")
        sys.exit()
    else:
        os.remove(LOCK_FILE)

with open(LOCK_FILE, "w") as f: f.write("work")

# --- 1. ШУСТРЫЙ НАБЛЮДАТЕЛЬ (РАБОТАЕТ В ФОНЕ) ---
def watch_for_flags():
    """Мгновенно хватает новые файлы и ставит в очередь"""
    while True:
        if os.path.exists(READY_FLAG):
            if os.path.exists(FILE_PATH):
                # Создаем уникальное имя
                timestamp = time.strftime("%H%M%S")
                queue_file = os.path.join(QUEUE_DIR, f"ege_queue_{timestamp}.mp4")
                
                try:
                    # Переименование работает мгновенно и освобождает ege.mp4 для макроса
                    os.rename(FILE_PATH, queue_file)
                    log(f"📥 Файл схвачен в очередь: {queue_file}")
                except Exception as e:
                    log(f"⚠️ Ошибка захвата файла: {e}")
            else:
                log("⚠️ Флаг есть, а оригинала видео нет. Игнорирую.")
            
            # Всегда сносим флаг, чтобы MacroDroid мог работать дальше
            try:
                os.remove(READY_FLAG)
            except:
                pass
                
        time.sleep(1) # Проверяет флаг каждую секунду

# --- 2. НЕСПЕШНЫЙ ГРУЗЧИК ---
def upload_file(target_file):
    """Пытается пропихнуть один файл в ВК до 5 раз"""
    api_url = "https://api.vk.com/method/"
    attempts = 0
    max_retries = 5
    
    while attempts < max_retries:
        try:
            log(f"📦 Загрузка {target_file} (попытка {attempts+1}/{max_retries})...")
            srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}, timeout=30).json()
            
            with open(target_file, 'rb') as f:
                upload_resp = requests.post(srv['response']['upload_url'], files={'file': ('video.mp4', f, 'video/mp4')}, timeout=1200).json()
            
            if 'error' in upload_resp or 'file' not in upload_resp:
                log(f"❌ Ошибка ВК: {upload_resp}")
                attempts += 1
                time.sleep(30)
                continue

            doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload_resp['file']}, timeout=30).json()
            attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
            
            requests.get(api_url + "wall.post", params={
                "access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, 
                "attachments": attachment, "message": "📹 Видео из очереди."
            }, timeout=30)
            
            log(f"✅ Успешно отправлено: {target_file}")
            return True
            
        except Exception as e:
            log(f"❌ Сбой сети: {e}")
            attempts += 1
            time.sleep(30)
            
    return False

# --- ОСНОВНОЙ ЦИКЛ СКРИПТА ---
try:
    # Запускаем наблюдателя параллельно
    t = threading.Thread(target=watch_for_flags, daemon=True)
    t.start()
    
    log("▶️ Скрипт активен (Режим: ОЧЕРЕДЬ). Жду файлы...")
    
    while True:
        # Пульс для замка, чтобы система знала, что мы живы
        with open(LOCK_FILE, "w") as f: f.write("work")
        
        # Ищем все файлы очереди и сортируем их по времени создания (сначала старые)
        queue_files = sorted(glob.glob(os.path.join(QUEUE_DIR, "ege_queue_*.mp4")))
        
        if queue_files:
            current_file = queue_files[0]
            log(f"📋 В очереди файлов: {len(queue_files)}. Беру в работу самый старый.")
            
            if upload_file(current_file):
                with open(SUCCESS_FLAG, "w") as f: f.write("ok")
                os.remove(current_file) # Удаляем файл из очереди после успеха
            else:
                with open(ERROR_FLAG, "w") as f: f.write("error")
                # Если файл полностью битый и не отправляется 5 раз, 
                # переименовываем его, чтобы он не заблокировал всю очередь навечно
                error_file = current_file + ".error"
                os.rename(current_file, error_file)
                log(f"🚨 Файл пропущен из-за мертвой сети. Перехожу к следующему.")
        else:
            # Если очередь пуста, просто спим и ждем
            time.sleep(2)

finally:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
    log("🏁 Скрипт остановлен.")
