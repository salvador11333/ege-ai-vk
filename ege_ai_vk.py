import os
import requests
import time
from secrets import GEMINI_API_KEY

FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
VK_TOKEN = "vk1.a.xs8rpIjm3x8xYvUJ4ztgeujy6XZ7BF2r5NuE47Dmdpo6TMz02yfTQAJyJkKlsL4BwK4auSZBIF5EqnU1vTojxriqtvdKvpKrgoILBWWKvC4xJ5sl5TlUNkVQk902EcHyY_CJa9oSLriZk3uCVqIpzC_lR3mJd2sB53j0upiWi7n91Z3jYfW4QiXZFJKEEsoJ4Ckz0iPU6Rv_18F9M9aU7A"
GROUP_ID = 239501197
SUBJECT = "it"
MODEL_NAME = "gemini-3.5-flash"

def upload_to_vk():
    print("📦 Загрузка видео в ВК...")
    api_url = "https://api.vk.com/method/"
    srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}).json()
    with open(FILE_PATH, 'rb') as f:
        upload = requests.post(srv['response']['upload_url'], files={'file': f}).json()
    doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload['file']}).json()
    attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
    post = requests.get(api_url + "wall.post", params={"access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "from_group": 1, "attachments": attachment, "message": "🤖 ИИ проводит разбор..."}).json()
    return post['response']['post_id']

def ai_process():
    print("🧠 Обработка через Gemini...")
    file_size = os.path.getsize(FILE_PATH)
    
    # 1. Начало загрузки
    init_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={GEMINI_API_KEY}"
    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(file_size),
        "X-Goog-Upload-Header-Content-Type": "video/mp4"
    }
    
    response = requests.post(init_url, headers=headers)
    if "X-Goog-Upload-URL" not in response.headers:
        print(f"❌ Ошибка инициализации: {response.text}")
        return None
        
    upload_url = response.headers["X-Goog-Upload-URL"]
    
    # 2. Загрузка
    print("📤 Загружаю видео...")
    with open(FILE_PATH, "rb") as f:
        requests.post(upload_url, headers={"X-Goog-Upload-Command": "upload, finalize", "X-Goog-Upload-Offset": "0"}, data=f.read())
    
    # 3. Ожидание обработки (API v1beta)
    print("⏳ Ожидаю готовности на сервере...")
    file_uri = None
    while not file_uri:
        time.sleep(5)
        response = requests.get(f"https://generativelanguage.googleapis.com/v1beta/files?key={GEMINI_API_KEY}")
        data = response.json()
        files = data.get("files", [])
        if not files: continue
            
        latest_file = files[-1]
        state = latest_file.get("state")
        
        if state == "ACTIVE":
            file_uri = latest_file.get("uri")
            print(f"✅ Файл готов: {file_uri}")
        elif state == "FAILED":
            print(f"❌ Ошибка обработки: {latest_file.get('error')}")
            return None

    # 4. Запрос к модели (ВАЖНО: CamelCase в JSON)
    print("🤖 Запрашиваю анализ...")
    prompt_text = open(f"{SUBJECT}_prompt.txt", "r", encoding="utf-8").read() if os.path.exists(f"{SUBJECT}_prompt.txt") else "Реши задачу."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    
    # ИСПОЛЬЗУЕМ КЛЮЧИ CamelCase (fileData, mimeType, fileUri)
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt_text},
                {
                    "fileData": {
                        "mimeType": "video/mp4",
                        "fileUri": file_uri
                    }
                }
            ]
        }]
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        print(f"❌ ОШИБКА API {response.status_code}: {response.text}")
        return None
    
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
        return None

def add_comment(post_id, text):
    requests.get("https://api.vk.com/method/wall.createComment", params={"access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, "post_id": post_id, "message": f"✅ ИИ-РАЗБОР:\n\n{text}"})

if __name__ == "__main__":
    try:
        p_id = upload_to_vk()
        solution = ai_process()
        if solution:
            add_comment(p_id, solution)
            print("🚀 ГОТОВО!")
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
