import os
import requests
import time
import sys
import glob
import threading
import subprocess

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

# --- 1. ШУСТРЫЙ НАБЛЮДАТЕЛЬ (ФОНОВЫЙ ПОТОК) ---
def watch_for_flags():
    """Мгновенно лечит структуру файла и ставит в очередь без тайм-аутов"""
    while True:
        if os.path.exists(READY_FLAG):
            if os.path.exists(FILE_PATH):
                timestamp = time.strftime("%H%M%S")
                queue_file = os.path.join(QUEUE_DIR, f"ege_queue_{timestamp}.mp4")
                
                try:
                    log("🛠️ Нормализация структуры файла (Fast Start)...")
                    # Переносим индексное оглавление видео (moov atom) в начало файла.
                    # Кодек '-c copy' копирует поток без перекодирования. Это занимает 0.2 секунды.
                    cmd = f"ffmpeg -y -i {FILE_PATH} -c copy -movflags +faststart -loglevel error {queue_file}"
                    subprocess.run(cmd, shell=True)
                    
                    if os.path.exists(queue_file):
                        # Как только копия создана — оригинал можно удалять, MacroDroid свободен для новой записи
                        if os.path.exists(FILE_PATH):
                            os.remove(FILE_PATH)
                        log(f"📥 Файл успешно нормализован и отправлен в очередь: {queue_file}")
                except Exception as e:
                    log(f"⚠️ Ошибка обработки файла: {e}")
            else:
                log("⚠️ Флаг есть, а оригинала видео нет. Игнорирую.")
            
            # Всегда сносим флаг, чтобы MacroDroid не зацикливался
            try:
                os.remove(READY_FLAG)
            except:
                pass
                
        time.sleep(1)

# --- 2. АГРЕССИВНЫЙ ГРУЗЧИК (ОСНОВНОЙ ПОТОК) ---
def upload_file(target_file):
    """Пытается пропихнуть один файл в ВК до 5 раз без долгих пауз"""
    api_url = "https://api.vk.com/method/"
    attempts = 0
    max_retries = 5
    
    while attempts < max_retries:
        try:
            log(f"📦 Загрузка {target_file} (попытка {attempts+1}/{max_retries})...")
            srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}, timeout=30).json()
            
            with open(target_file, 'rb') as f:
                # Передаем жесткий MIME-тип видео и режем сетевой тайм-аут до 3 минут вместо 20.
                upload_resp = requests.post(
                    srv['response']['upload_url'], 
                    files={'file': ('video.mp4', f, 'video/mp4')}, 
                    timeout=180
                ).json()
            
            if 'error' in upload_resp or 'file' not in upload_resp:
                log(f"❌ Ошибка ВК (not saved или сбой парсинга): {upload_resp}")
                attempts += 1
                time.sleep(3) # Быстрый перезапуск попытки через 3 секунды
                continue

            doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload_resp['file']}, timeout=30).json()
            attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
            
            requests.get(api_url + "wall.post", params={
                "access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, 
                "attachments": attachment, "message": "📹 Видео из очереди."
            }, timeout=30)
            
            log(f"✅ Успешно отправлено на стену: {target_file}")
            return True
            
        except Exception as e:
            log(f"❌ Сбой сети/Таймаут соединения: {e}")
            attempts += 1
            time.sleep(3) # Быстрый перезапуск попытки через 3 секунды
            
    return False

# --- ТОЧКА ВХОДА ---
try:
    # Запускаем фонового наблюдателя в отдельном изолированном потоке
    t = threading.Thread(target=watch_for_flags, daemon=True)
    t.start()
    
    log("▶️ Скрипт активен (Режим: ОЧЕРЕДЬ + FASTSTART). Ожидаю файлы...")
    
    while True:
        # Продлеваем жизнь замку активности
        with open(LOCK_FILE, "w") as f: f.write("work")
        
        # Сканируем папку на наличие файлов очереди и сортируем их от старых к новым
        queue_files = sorted(glob.glob(os.path.join(QUEUE_DIR, "ege_queue_*.mp4")))
        
        if queue_files:
            current_file = queue_files[0]
            log(f"📋 В очереди обнаружено файлов: {len(queue_files)}. Запускаю отправку первого.")
            
            if upload_file(current_file):
                with open(SUCCESS_FLAG, "w") as f: f.write("ok")
                if os.path.exists(current_file):
                    os.remove(current_file)
            else:
                with open(ERROR_FLAG, "w") as f: f.write("error")
                # Если файл тотально битый и не ушел за 5 попыток — 
                # маркируем его ошибкой, чтобы он не забивал конвейер
                error_file = current_file + ".error"
                os.rename(current_file, error_file)
                log(f"🚨 Файл {current_file} заблокирован после 5 провалов. Перехожу к следующему.")
        else:
            time.sleep(2)

finally:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
    log("🏁 Скрипт остановлен.")
