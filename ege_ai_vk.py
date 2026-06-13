import os
import requests
import time

FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
LOG_FILE = "/data/data/com.termux/files/home/bot_log.txt"

VK_TOKEN = "vk1.a.xs8rpIjm3x8xYvUJ4ztgeujy6XZ7BF2r5NuE47Dmdpo6TMz02yfTQAJyJkKlsL4BwK4auSZBIF5EqnU1vTojxriqtvdKvpKrgoILBWWKvC4xJ5sl5TlUNkVQk902EcHyY_CJa9oSLriZk3uCVqIpzC_lR3mJd2sB53j0upiWi7n91Z3jYfW4QiXZFJKEEsoJ4Ckz0iPU6Rv_18F9M9aU7A"
GROUP_ID = 239501197

def log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.ctime()} - {text}\n")
    print(text)

def attempt_upload():
    # 1. Проверяем, существует ли файл и не пустой ли он
    if not os.path.exists(FILE_PATH) or os.path.getsize(FILE_PATH) < 1024:
        log("Файл не найден или слишком мал (ждет записи)...")
        return False
    
    try:
        log("Начинаю загрузку...")
        api_url = "https://api.vk.com/method/"
        
        # Получаем сервер
        srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}, timeout=15).json()
        
        # Загружаем файл
        with open(FILE_PATH, 'rb') as f:
            upload_resp = requests.post(srv['response']['upload_url'], files={'file': f}, timeout=60).json()
        
        # Сохраняем
        doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload_resp['file']}, timeout=15).json()
        
        # Публикуем
        attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
        requests.get(api_url + "wall.post", params={
            "access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, 
            "attachments": attachment, "message": "📹 Новое видео."
        }, timeout=15)
        
        log("Успешно отправлено!")
        os.remove(FILE_PATH) # Удаляем только если всё прошло успешно
        return True
        
    except Exception as e:
        log(f"Ошибка при отправке: {e}")
        return False

log("Запуск цикла...")
while True:
    if attempt_upload():
        break
    time.sleep(20) # Пауза перед следующей попыткой
