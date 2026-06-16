import os
import requests
import time

FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
LOG_FILE = "/data/data/com.termux/files/home/bot_log.txt"

# Твой рабочий токен, полученный через VK Admin
VK_TOKEN = "vk1.a.lsRykF02XWyz7uuaOpLUZpneg0twi5dgZhUE40c0nwiJ7JSVYnis2mTbXT6XVgNRYhy6eWZIp_Hc2hO8P2Fw9aDiHuukrw2bd7xD-UL8AF6haARKltenqLCpiBLejcmKU6E-t1_MEu--E24WtAt2ckTymp8wbdrGrZyOscNWbaV_KkIFMf5AteYwgBy9to40IDG1maSGz9JHC4b0LoGpMQ"
GROUP_ID = 239501197

def log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.ctime()} - {text}\n")
    print(text)

def is_file_ready():
    # Если файла вообще нет — уходим на следующий круг
    if not os.path.exists(FILE_PATH):
        return False
    
    # Замеряем размер файла сейчас
    size_before = os.path.getsize(FILE_PATH)
    if size_before < 10000: # Если файл меньше 10 КБ, он точно еще не записан
        return False
        
    # Ждем 3 секунды, чтобы проверить, идет ли запись
    time.sleep(3)
    
    # Замеряем размер еще раз
    size_after = os.path.getsize(FILE_PATH)
    
    # Если размер изменился — значит MacroDroid всё еще пишет видео
    if size_before != size_after:
        log("Видео ещё записывается (размер файла растёт), жду...")
        return False
        
    # Если размер остался прежним — файл полностью готов
    return True

def attempt_upload():
    # Скрипт ничего не делает, пока файл не готов полностью
    if not is_file_ready():
        return False
    
    try:
        log(f"Файл полностью записан! Размер: {os.path.getsize(FILE_PATH)} байт. Начинаю отправку...")
        api_url = "https://api.vk.com/method/"
        
        # Получаем сервер для загрузки
        srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}, timeout=30).json()
        
        # Потоковая загрузка тяжелого файла
        with open(FILE_PATH, 'rb') as f:
            upload_resp = requests.post(srv['response']['upload_url'], files={'file': f}, timeout=600).json()
        
        # Сохраняем в документы ВК
        doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload_resp['file']}, timeout=30).json()
        
        # Публикуем на стену группы
        attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
        requests.get(api_url + "wall.post", params={
            "access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, 
            "attachments": attachment, "message": "📹 Новое видео."
        }, timeout=30)
        
        log("Успешно отправлено в ВК!")
        
        # Создаем сигнал успешной отправки для MacroDroid (для вибрации)
        with open("/storage/emulated/0/MacroDroid/success.flag", "w") as f: 
            f.write("ok")
            
        # Удаляем оригинал с телефона только ТЕПЕРЬ, когда всё на 100% загружено
        os.remove(FILE_PATH)
        return True
        
    except Exception as e:
        log(f"Ошибка при отправке: {e}")
        return False

log("Запуск цикла ожидания видео...")
while True:
    if attempt_upload():
        break
    time.sleep(5) # Проверяем файл каждые 5 секунд
