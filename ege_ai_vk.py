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

# ⚠️ ВСТАВЬ СКОПИРОВАННЫЙ ТОКЕН СЮДА:
YANDEX_TOKEN = "y0__wgBELP10MEBGKjfQyCQi476F27p3yubu9e0ABud6y-7q-ZqAVuv"

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

def compress_video():
    log("🗜️ Начинаю сжатие (Профиль: Съемка монитора)...")
    # Срезаем кадры до 30 FPS и ставим пресет fast для идеального баланса веса и четкости текста
    cmd = f"ffmpeg -y -i {FILE_PATH} -vcodec libx264 -crf 24 -preset fast -r 30 -loglevel error {OPT_FILE}"
    subprocess.run(cmd, shell=True)
    return os.path.exists(OPT_FILE)

def upload_to_yandex(target_file):
    try:
        log(f"📦 Запрашиваю сервер Яндекса для файла ({os.path.getsize(target_file)} байт)...")
        
        # Генерируем уникальное имя файла с текущим временем
        time_str = time.strftime("%H-%M-%S")
        file_name = f"ege_zadanie_{time_str}.mp4"
        
        headers = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
        
        # 1. Запрашиваем у Яндекса ссылку на загрузку в корень Диска
        get_url = f"https://cloud-api.yandex.net/v1/disk/resources/upload?path=disk:/{file_name}&overwrite=true"
        resp = requests.get(get_url, headers=headers, timeout=30).json()
        
        if 'href' not in resp:
            log(f"❌ Ошибка API Яндекса (проверь токен): {resp}")
            return False
            
        upload_link = resp['href']
        
        # 2. Выгружаем файл напрямую на сервера Яндекса
        log(f"🚀 Ссылка получена! Отправляю файл на Яндекс.Диск...")
        with open(target_file, 'rb') as f:
            upload_resp = requests.put(upload_link, data=f, timeout=600)
            
        if upload_resp.status_code in [201, 202]:
            log(f"✅ Успешно загружено на Диск! Файл: {file_name}")
            with open(SUCCESS_FLAG, "w") as f: f.write("ok")
            
            if os.path.exists(FILE_PATH): os.remove(FILE_PATH)
            if os.path.exists(OPT_FILE): os.remove(OPT_FILE)
            return True
        else:
            log(f"❌ Яндекс отклонил файл. Код ответа: {upload_resp.status_code}")
            return False
            
    except Exception as e:
        log(f"❌ Сбой сети: {e}")
        return False

try:
    log("▶️ Скрипт активен. Назначение: ЯНДЕКС.ДИСК. Ожидаю ready.flag...")
    
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
            
            target_file = FILE_PATH
            if compress_video():
                target_file = OPT_FILE
                log(f"✅ Сжатие завершено! Новый вес: {os.path.getsize(OPT_FILE)} байт.")
            else:
                log("⚠️ Ошибка сжатия, отправляю оригинал.")

            attempts = 0
            max_retries = 5
            success = False
            
            while attempts < max_retries:
                if upload_to_yandex(target_file):
                    success = True
                    break
                attempts += 1
                log(f"⚠️ Попытка отправки {attempts}/{max_retries} не удалась. Повтор через 30 сек...")
                time.sleep(30)
            
            if not success:
                log("🚨 Сеть мертва (5/5 провалов). Сигнал ошибки.")
                with open(ERROR_FLAG, "w") as f: f.write("error")
            else:
                log("💤 Видео на Диске. Снова жду команду от MacroDroid...")
                
        time.sleep(2) 

finally:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
    log("🏁 Скрипт остановлен.")
