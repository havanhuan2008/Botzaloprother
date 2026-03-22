import hashlib
import hmac
import json
from typing import Any, Optional

import requests
from flask import current_app


class ZaloClient:
    def __init__(self):
        self.access_token = current_app.config['ZALO_ACCESS_TOKEN']
        self.base_url = current_app.config['ZALO_API_BASE'].rstrip('/')

    def send_text_message(self, user_id: str, text: str) -> dict:
        if not self.access_token:
            return {'ok': False, 'error': 'Missing ZALO_ACCESS_TOKEN'}

        url = f'{self.base_url}/v3.0/oa/message/cs'
        headers = {
            'Content-Type': 'application/json',
            'access_token': self.access_token,
        }
        payload = {
            'recipient': {'user_id': user_id},
            'message': {'text': text},
        }

        response = requests.post(url, headers=headers, json=payload, timeout=20)
        try:
            body = response.json()
        except ValueError:
            body = {'raw': response.text}

        ok = response.ok and body.get('error') in (0, '0', None)
        return {
            'ok': ok,
            'status_code': response.status_code,
            'body': body,
        }


def validate_webhook_signature(raw_body: bytes, headers: dict[str, str]) -> bool:
    if not current_app.config['ZALO_VALIDATE_SIGNATURE']:
        return True

    app_id = current_app.config['ZALO_APP_ID']
    oa_secret_key = current_app.config['ZALO_OA_SECRET_KEY']

    if not app_id or not oa_secret_key:
        return False

    signature = headers.get('X-ZEvent-Signature') or headers.get('x-zevent-signature')
    timestamp = headers.get('X-ZEvent-Timestamp') or headers.get('x-zevent-timestamp') or ''

    if not signature:
        return False

    try:
        data_string = raw_body.decode('utf-8')
    except UnicodeDecodeError:
        return False

    mac_source = f'{app_id}{data_string}{timestamp}{oa_secret_key}'.encode('utf-8')
    digest = hashlib.sha256(mac_source).hexdigest()
    expected = f'mac={digest}'
    return hmac.compare_digest(signature.strip(), expected)


def _deep_get(data: Any, keys: list[str]) -> Optional[Any]:
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def extract_message_data(payload: dict) -> dict:
    candidates = [
        ('sender', 'id'),
        ('sender', 'user_id'),
        ('message', 'from_id'),
        ('data', 'sender', 'id'),
        ('data', 'sender', 'user_id'),
    ]
    text_candidates = [
        ('message', 'text'),
        ('data', 'message', 'text'),
        ('text',),
        ('message', 'msg'),
        ('data', 'message', 'msg'),
    ]

    user_id = None
    for path in candidates:
        value = _deep_get(payload, list(path))
        if value:
            user_id = str(value)
            break

    if not user_id:
        for key in ('user_id', 'from_id', 'uid'):
            if payload.get(key):
                user_id = str(payload[key])
                break

    text = None
    for path in text_candidates:
        value = _deep_get(payload, list(path))
        if isinstance(value, str) and value.strip():
            text = value.strip()
            break

    if not text:
        for key in ('content', 'message', 'msg', 'text'):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                text = value.strip()
                break

    event_name = payload.get('event_name') or _deep_get(payload, ['data', 'event_name']) or payload.get('event') or 'unknown'

    return {
        'user_id': user_id,
        'text': text,
        'event_name': event_name,
        'raw': json.dumps(payload, ensure_ascii=False),
    }
