import os
import requests

FILE_PATH = "/storage/emulated/0/MacroDroid/ege.mp4"
VK_TOKEN = "vk1.a.xs8rpIjm3x8xYvUJ4ztgeujy6XZ7BF2r5NuE47Dmdpo6TMz02yfTQAJyJkKlsL4BwK4auSZBIF5EqnU1vTojxriqtvdKvpKrgoILBWWKvC4xJ5sl5TlUNkVQk902EcHyY_CJa9oSLriZk3uCVqIpzC_lR3mJd2sB53j0upiWi7n91Z3jYfW4QiXZFJKEEsoJ4Ckz0iPU6Rv_18F9M9aU7A"
GROUP_ID = 239501197

def upload_to_vk():
    if not os.path.exists(FILE_PATH):
        print("❌ Файл видео не найден!")
        return False

    print("📦 Загрузка видео в ВК...")
    api_url = "https://api.vk.com/method/"
    
    # Получаем сервер для загрузки
    srv = requests.get(api_url + "docs.getWallUploadServer", params={"access_token": VK_TOKEN, "v": "5.131", "group_id": GROUP_ID}).json()
    
    # Отправляем файл на сервер
    with open(FILE_PATH, 'rb') as f:
        upload = requests.post(srv['response']['upload_url'], files={'file': f}).json()
    
    # Сохраняем документ в ВК
    doc = requests.get(api_url + "docs.save", params={"access_token": VK_TOKEN, "v": "5.131", "file": upload['file']}).json()
    
    # Формируем вложение
    attachment = f"doc{doc['response']['doc']['owner_id']}_{doc['response']['doc']['id']}"
    
    # Публикуем на стену группы
    print("📢 Публикация на стену...")
    post = requests.get(api_url + "wall.post", params={
        "access_token": VK_TOKEN, 
        "v": "5.131", 
        "owner_id": -GROUP_ID, 
        "from_group": 1, 
        "attachments": attachment, 
        "message": "📹 Новая видеозапись задания."
    }).json()
    
    if 'response' in post:
        print(f"✅ Успешно опубликовано! ID поста: {post['response']['post_id']}")
        return True
    else:
        print(f"❌ Ошибка публикации ВК: {post}")
        return False

if __name__ == "__main__":
    try:
        # Запускаем загрузку
        if upload_to_vk():
            # Если загрузилось — удаляем оригинал с телефона
            os.remove(FILE_PATH)
            print("🗑️ Локальный файл удален для экономии места.")
            print("🚀 ГОТОВО!")
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
