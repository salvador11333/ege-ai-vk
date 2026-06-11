import os
import requests
import time

FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
VK_TOKEN = "vk1.a.xs8rpIjm3x8xYvUJ4ztgeujy6XZ7BF2r5NuE47Dmdpo6TMz02yfTQAJyJkKlsL4BwK4auSZBIF5EqnU1vTojxriqtvdKvpKrgoILBWWKvC4xJ5sl5TlUNkVQk902EcHyY_CJa9oSLriZk3uCVqIpzC_lR3mJd2sB53j0upiWi7n91Z3jYfW4QiXZFJKEEsoJ4Ckz0iPU6Rv_18F9M9aU7A"
GEMINI_API_KEY = "AQ.Ab8RN6ILZzS9PHhgxmwrbw_pgnHgTaZRyDPKg2AheAA-sxlaqw"
GROUP_ID = 239501197
SUBJECT = "it" 
MODEL_NAME = "gemini-3.5-flash"

def safe_json(response):
    data = response.json()
    if 'error' in data:
        print(f"❌ ОШИБКА API ВК: {data['error'].get('error_msg', 'Неизвестная ошибка')}")
        raise Exception("VK API Error")
    return data

def upload_to_vk():
    print("📦 Загрузка видео в ВК...")
    api_url = "https://api.vk.com/method/"
    
    # Получаем сервер
    srv = safe_json(requests.get(api_url + "docs.getWallUploadServer", 
                       params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}))
    
    # Загружаем файл
    with open(FILE_PATH, 'rb') as f:
        upload = requests.post(srv['response']['upload_url'], files={'file': f}).json()
    
    # Сохраняем
    doc = safe_json(requests.get(api_url + "docs.save", 
                       params={"access_token": VK_TOKEN, "v": "5.131", "file": upload['file']}))
    
    doc_data = doc['response']['doc']
    attachment = f"doc{doc_data['owner_id']}_{doc_data['id']}"
    
    post = safe_json(requests.get(api_url + "wall.post", 
                        params={"access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, 
                                "from_group": 1, "attachments": attachment, 
                                "message": "🤖 ИИ проводит глубокий анализ видео, ожидайте разбор..."}))
    return post['response']['post_id']

def ai_process():
    print("🧠 Обработка через Gemini 1.5-flash...")
    prompt_file = f"{SUBJECT}_prompt.txt"
    system_prompt = open(prompt_file, "r", encoding="utf-8").read() if os.path.exists(prompt_file) else "Реши задачу с видео."
    
    file_size = os.path.getsize(FILE_PATH)
    
    # Инициализация
    init = requests.post(f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={GEMINI_API_KEY}", 
                         headers={"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start", 
                                  "X-Goog-Upload-Header-Content-Length": str(file_size), 
                                  "X-Goog-Upload-Header-Content-Type": "video/mp4"}).headers
    
    with open(FILE_PATH, "rb") as f:
        requests.post(init["X-Goog-Upload-URL"], 
                      headers={"X-Goog-Upload-Command": "upload, finalize", "X-Goog-Upload-Offset": "0"}, 
                      data=f.read())
    
    file_name = init["X-Goog-Upload-URL"].split('/')[-1]
    
    # Ожидание готовности
    print("⏳ Ожидаем готовности видео на сервере Google...")
    for i in range(10): # Ждем до 50 секунд
        status = requests.get(f"https://generativelanguage.googleapis.com/v1beta/files/{file_name}?key={GEMINI_API_KEY}").json()
        if status.get("state") == "ACTIVE": break
        time.sleep(5)
    
    # ЗАПРОС К МОДЕЛИ С ОТКЛЮЧЕНИЕМ ФИЛЬТРОВ
    print("🚀 Отправляю запрос...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": system_prompt}, {"file_data": {"mime_type": "video/mp4", "file_uri": f"files/{file_name}"}}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    }
    
    response = requests.post(url, json=payload, timeout=120)
    
    # ПРОВЕРКА ОТВЕТА
    if response.status_code != 200:
        print(f"❌ ОШИБКА HTTP {response.status_code}: {response.text}")
        raise Exception("Ошибка сервера Gemini")
        
    res = response.json()
    
    if "candidates" not in res or not res["candidates"][0].get("content"):
        print("❌ ИИ НЕ ВЕРНУЛ ОТВЕТ. Полный ответ сервера:")
        print(res)
        raise Exception("Пустой ответ от ИИ (возможно, фильтр безопасности)")
    
    return res["candidates"][0]["content"]["parts"][0]["text"]

def add_comment(post_id, text):
    print("📝 Комментирую в ВК...")
    requests.get("https://api.vk.com/method/wall.createComment", 
                 params={"access_token": VK_TOKEN, "v": "5.131", "owner_id": -GROUP_ID, 
                         "post_id": post_id, "message": f"✅ ИИ-РАЗБОР:\n\n{text}"})

if __name__ == "__main__":
    try:
        p_id = upload_to_vk()
        solution = ai_process()
        add_comment(p_id, solution)
        print("🚀 ГОТОВО!")
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
