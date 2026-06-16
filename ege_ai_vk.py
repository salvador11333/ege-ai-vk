import os
import time
import vk_api
import subprocess

FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
SMALL_FILE = "/storage/emulated/0/MacroDroid/ege_opt.mp4"
LOG_FILE = "/data/data/com.termux/files/home/bot_log.txt"

VK_TOKEN = "vk1.a.lsRykF02XWyz7uuaOpLUZpneg0twi5dgZhUE40c0nwiJ7JSVYnis2mTbXT6XVgNRYhy6eWZIp_Hc2hO8P2Fw9aDiHuukrw2bd7xD-UL8AF6haARKltenqLCpiBLejcmKU6E-t1_MEu--E24WtAt2ckTymp8wbdrGrZyOscNWbaV_KkIFMf5AteYwgBy9to40IDG1maSGz9JHC4b0LoGpMQ" # Вставь свой токен
GROUP_ID = 239501197

def log(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.ctime()} - {text}\n")
    print(text)

def optimize_video():
    # CRF 20 — это «почти без потерь». Текст будет четким, размер упадет.
    # Preset medium — баланс скорости и сжатия.
    cmd = f"ffmpeg -y -i {FILE_PATH} -vcodec libx264 -crf 20 -preset medium {SMALL_FILE}"
    subprocess.run(cmd, shell=True)
    return os.path.exists(SMALL_FILE)

def upload():
    try:
        if not os.path.exists(FILE_PATH): return False
        
        log("Оптимизация...")
        if not optimize_video(): return False
        
        log("Авторизация в ВК...")
        vk_session = vk_api.VkApi(token=VK_TOKEN)
        upload = vk_api.VkUpload(vk_session)
        
        log("Загрузка в ВК (vk_api)...")
        # Загружаем как документ (быстрее и надежнее)
        doc = upload.document(SMALL_FILE, title="Задание")
        
        # Публикуем
        vk = vk_session.get_api()
        attachment = f"doc{doc['owner_id']}_{doc['id']}"
        vk.wall.post(
            owner_id=-GROUP_ID,
            from_group=1,
            attachments=attachment,
            message="Видео."
        )
        
        log("Успешно!")
        with open("/storage/emulated/0/MacroDroid/success.flag", "w") as f: f.write("ok")
        os.remove(FILE_PATH)
        os.remove(SMALL_FILE)
        return True
        
    except Exception as e:
        log(f"Ошибка: {e}")
        return False

while True:
    if upload(): break
    time.sleep(20)
