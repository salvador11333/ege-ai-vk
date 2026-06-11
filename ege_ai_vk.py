import os
import requests
import time
from secrets import GEMINI_API_KEY

# --- НАСТРОЙКИ ---
FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
VK_TOKEN = "vk1.a.xs8rpIjm3x8xYvUJ4ztgeujy6XZ7BF2r5NuE47Dmdpo6TMz02yfTQAJyJkKlsL4BwK4auSZBIF5EqnU1vTojxriqtvdKvpKrgoILBWWKvC4xJ5sl5TlUNkVQk902EcHyY_CJa9oSLriZk3uCVqIpzC_lR3mJd2sB53j0upiWi7n91Z3jYfW4QiXZFJKEEsoJ4Ckz0iPU6Rv_18F9M9aU7A"
GROUP_ID = 239501197
SUBJECT = "it"
MODEL_NAME = "gemini-3.5-flash"

def upload_to_vk():
    print("📦 Загрузка видео в ВК...")
    api_url = "https://api.vk.com/method/"
    
    # Получаем сервер для загрузки
    srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}).json()
    
    # Загружаем файл
    with open(FILE_PATH, 'rb') as f:
        upload = requests.post(srv['response']['upload_url'], files={'file': f}).json()
    
    # Сохраняем документ
    doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload['file']}).json()
    attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
    
    # Публикуем пост
    post = requests.get(api_url + "wall.post", params={"access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, "attachments": attachment, "message": "🤖 ИИ проводит разбор задачи..."}).json()
    return post['response']['post_id']

def ai_process():
    print("🧠 Обработка через Gemini...")
    file_size = os.path.getsize(FILE_PATH)
    
    # Запрос на начало загрузки
    init_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={GEMINI_API_KEY}"
    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(file_size),
        "X-Goog-Upload-Header-Content-Type": "video/mp4"
    }
    
    print("🔗 Подключаюсь к Gemini API...")
    response = requests.post(init_url, headers=headers, timeout=30)
    
    if "X-Goog-Upload-URL" not in response.headers:
        raise Exception(f"Не удалось получить URL для загрузки. Ответ: {response.text}")
        
    upload_url = response.headers["X-Goog-Upload-URL"]
    
    # Загрузка файла
    print(f"📤 Загружаю видео ({file_size} байт)...")
    with open(FILE_PATH, "rb") as f:
        # Добавили timeout, чтобы не висело вечно
        requests.post(upload_url, headers={"X-Goog-Upload-Command": "upload, finalize", "X-Goog-Upload-Offset": "0"}, data=f.read(), timeout=60)
    
    file_id = upload_url.split('/')[-1]
    
    # Ожидание обработки
    print("⏳ Файл загружен. Жду готовности (обработки) на сервере...")
    while True:
        status = requests.get(f"https://generativelanguage.googleapis.com/v1beta/files/{file_id}?key={GEMINI_API_KEY}", timeout=30).json()
        
        state = status.get("state")
        if state == "ACTIVE":
            print("✅ Видео готово к анализу!")
            file_uri = status["name"]
            break
        elif state == "FAILED":
            raise Exception("Ошибка обработки видео на стороне Google")
        else:
            print(f"⌛ Статус: {state}...") # Будет видно, что скрипт живой
        time.sleep(5)
    
    # Генерация контента
    print("🤖 Запрашиваю анализ у ИИ...")
    prompt_file = f"{SUBJECT}_prompt.txt"
    system_prompt = open(prompt_file, "r", encoding="utf-8").read() if os.path.exists(prompt_file) else "Реши задачу."
    
    url = f"https://generativelanguage.googleapis.com/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    res = requests.post(url, json={"contents": [{"parts": [{"text": system_prompt}, {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}}]}]}, timeout=60).json()
    
    return res["candidates"][0]["content"]["parts"][0]["text"]

def add_comment(post_id, text):
    requests.get("https://api.vk.com/method/wall.createComment", params={"access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "post_id": post_id, "message": f"✅ ИИ-РАЗБОР:\n\n{text}"})

if __name__ == "__main__":
    try:
        p_id = upload_to_vk()
        solution = ai_process()
        add_comment(p_id, solution)
        print("🚀 ГОТОВО!")
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
