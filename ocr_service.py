import os
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
import base64
import uvicorn
import sys

os.environ["YANDEX_IAM_TOKEN"] = "токен скрыт"
os.environ["YANDEX_FOLDER_ID"] = "ID скрыт"

YANDEX_IAM_TOKEN = os.environ.get('YANDEX_IAM_TOKEN')
YANDEX_FOLDER_ID = os.environ.get('YANDEX_FOLDER_ID')
YANDEX_VISION_URL = 'https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze'

app = FastAPI()

def recognize_with_yandex(image_bytes, lang_mode='auto'):
    headers = {
        'Authorization': f'Bearer {YANDEX_IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    if lang_mode == 'rus':
        langs = ['ru']
    elif lang_mode == 'eng':
        langs = ['en']
    else:
        langs = ['ru', 'en']
    body = {
        "folderId": YANDEX_FOLDER_ID,
        "analyze_specs": [
            {
                "content": encoded_image,
                "features": [{"type": "TEXT_DETECTION", "text_detection_config": {"language_codes": langs}}]
            }
        ]
    }
    try:
        response = requests.post(YANDEX_VISION_URL, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        result = response.json()
        text = ""
        try:
            if (
                'results' in result and
                result['results'] and
                'results' in result['results'][0] and
                result['results'][0]['results'] and
                'textDetection' in result['results'][0]['results'][0] and
                'pages' in result['results'][0]['results'][0]['textDetection']
            ):
                blocks = result['results'][0]['results'][0]['textDetection']['pages'][0]['blocks']
                lines = []
                for block in blocks:
                    for line in block['lines']:
                        line_text = ' '.join([word['text'] for word in line['words']])
                        lines.append(line_text)
                text = '\n'.join(lines)
            else:
                text = ""
        except Exception:
            text = ""
        return text
    except Exception:
        return ""

@app.post("/recognize")
async def recognize_text(file: UploadFile = File(...), lang_mode: str = Form('auto')):
    if not (YANDEX_IAM_TOKEN and YANDEX_FOLDER_ID):
        raise HTTPException(status_code=500, detail="YANDEX_IAM_TOKEN и/или YANDEX_FOLDER_ID не заданы!")
    contents = await file.read()
    text = recognize_with_yandex(contents, lang_mode)
    if not text.strip():
        return {"text": "Текст не распознан", "status": "empty"}
    return {"text": text, "status": "success"}

@app.get("/health")
async def health_check():
    if not (YANDEX_IAM_TOKEN and YANDEX_FOLDER_ID):
        return {"status": "error", "message": "YANDEX_IAM_TOKEN и/или YANDEX_FOLDER_ID не заданы!"}
    return {"status": "healthy", "engine": "Yandex Vision"}

if __name__ == "__main__":
    try:
        if not YANDEX_IAM_TOKEN or not YANDEX_FOLDER_ID:
            import sys
            sys.exit(1)
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        sys.exit(1) 