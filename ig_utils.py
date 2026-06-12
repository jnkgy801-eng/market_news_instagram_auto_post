"""
📸 Instagram 投稿共通ユーティリティ
main.py（市場ニュース投稿）と fortune_post.py（ラッキー星座・雑学ランキング投稿）
の両方から利用される共通関数をまとめたモジュールです。
"""

import os
import io
import json
import time
import base64
import requests
from PIL import Image

BASE_URL = 'https://graph.facebook.com/v19.0'

ACCESS_TOKEN  = os.environ.get('META_ACCESS_TOKEN', '')
IG_USER_ID    = os.environ.get('INSTAGRAM_ACCOUNT_ID', '')
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY', '')


def check_credentials():
    """必須の認証情報が設定されているか確認する。"""
    if not ACCESS_TOKEN or not IG_USER_ID:
        print('❌ 環境変数 META_ACCESS_TOKEN / INSTAGRAM_ACCOUNT_ID が設定されていません。')
        return False
    print('✅ 認証情報を読み込みました。')
    return True


def upload_to_imgbb(pil_img, api_key=None):
    """PillowのImageをimgbbにアップロードして公開URLを返す。"""
    api_key = api_key or IMGBB_API_KEY
    if not api_key:
        return None
    buf = io.BytesIO()
    pil_img.save(buf, format='JPEG', quality=92)
    b64 = base64.b64encode(buf.getvalue()).decode()
    try:
        resp = requests.post(
            'https://api.imgbb.com/1/upload',
            data={'key': api_key, 'image': b64}, timeout=30,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get('data', {}).get('url'):
            return data['data']['url']
        print('  ❌ imgbbアップロード失敗:')
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f'  ❌ imgbbアップロードエラー: {e}')
    return None


def download_image_as_pil(url, timeout=90):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
        if resp.status_code == 200 and 'image' in resp.headers.get('Content-Type', ''):
            return Image.open(io.BytesIO(resp.content)).convert('RGB')
    except Exception as e:
        print(f'    ⚠️ ダウンロードエラー: {e}')
    return None


def create_media_container(image_url, caption):
    resp = requests.post(
        f'{BASE_URL}/{IG_USER_ID}/media',
        data={'image_url': image_url, 'caption': caption,
              'media_type': 'IMAGE', 'access_token': ACCESS_TOKEN}
    )
    data = resp.json()
    if resp.status_code == 200 and 'id' in data:
        print(f'  ✅ メディアコンテナ作成: ID={data["id"]}')
        print('  ⏳ 処理待機中（10秒）...')
        time.sleep(10)
        return data['id']
    print('  ❌ コンテナ作成失敗:')
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return None


def publish_media(container_id):
    resp = requests.post(
        f'{BASE_URL}/{IG_USER_ID}/media_publish',
        data={'creation_id': container_id, 'access_token': ACCESS_TOKEN}
    )
    data = resp.json()
    if resp.status_code == 200 and 'id' in data:
        print(f'  🎉 投稿成功！ 投稿ID={data["id"]}')
        return data['id']
    print('  ❌ 投稿失敗:')
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return None


def post_to_instagram(image_url, caption):
    print('=' * 55)
    print('📤 Instagram投稿開始...')
    print(f'  画像URL: {image_url[:70]}...')
    print(f'  キャプション: {caption[:50]}...')
    print('=' * 55)
    if not image_url or not image_url.startswith('http'):
        print('❌ 有効な画像URLがありません。')
        return None
    cid = create_media_container(image_url, caption)
    if not cid:
        return None
    pid = publish_media(cid)
    if pid:
        print('\n✨ 投稿完了！Instagramアプリで確認してください。')
    return pid
