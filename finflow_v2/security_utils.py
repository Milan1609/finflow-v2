import base64
import hashlib
import hmac
import re
import secrets
import struct
import time
from urllib.parse import quote

import qrcode
from qrcode.image.svg import SvgPathImage


def validate_password(password: str) -> str | None:
    """Validate password policy:
    - length between 12 and 128
    - at least one uppercase
    - at least one lowercase
    - at least one digit
    - at least one special character
    Returns None if valid, otherwise returns an error message.
    """
    if not password:
        return 'Password is required.'
    if len(password) < 12 or len(password) > 128:
        return 'Password must be 12–128 characters long.'
    if not re.search(r'[A-Z]', password):
        return 'Password must include at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return 'Password must include at least one lowercase letter.'
    if not re.search(r'\d', password):
        return 'Password must include at least one number.'
    if not re.search(r'[^A-Za-z0-9]', password):
        return 'Password must include at least one special character.'
    return None


def generate_2fa_secret(length: int = 20) -> str:
    return base64.b32encode(secrets.token_bytes(length)).decode('ascii').rstrip('=')


def _normalize_2fa_secret(secret: str) -> str:
    return (secret or '').strip().upper().replace(' ', '')


def generate_totp_code(secret: str, timestamp: int | None = None) -> str:
    current_time = int(timestamp if timestamp is not None else time.time())
    counter = current_time // 30
    secret_bytes = base64.b32decode(_normalize_2fa_secret(secret))
    message = struct.pack('>Q', counter)
    digest = hmac.new(secret_bytes, message, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % 1_000_000).zfill(6)


def verify_totp_code(secret: str, code: str, window: int = 2, timestamp: int | None = None) -> bool:
    if not secret or not code:
        return False
    normalized_code = re.sub(r'\D', '', str(code))
    if len(normalized_code) != 6:
        return False
    current_time = int(timestamp if timestamp is not None else time.time())
    for offset in range(-window, window + 1):
        if generate_totp_code(secret, current_time + (offset * 30)) == normalized_code:
            return True
    return False


def build_otpauth_uri(secret: str, email: str, issuer: str = 'FinFlow') -> str:
    label = quote(f'{issuer}:{email}')
    params = {
        'secret': _normalize_2fa_secret(secret),
        'issuer': issuer,
        'algorithm': 'SHA1',
        'digits': '6',
        'period': '30',
    }
    query = '&'.join(f'{key}={quote(value)}' for key, value in params.items())
    return f'otpauth://totp/{label}?{query}'


def generate_qr_code_data_url(secret: str, email: str, issuer: str = 'FinFlow') -> str:
    uri = build_otpauth_uri(secret, email, issuer)
    try:
        qr_image = qrcode.make(uri)
        import io
        buffer_obj = io.BytesIO()
        qr_image.save(buffer_obj, format='PNG')
        encoded = base64.b64encode(buffer_obj.getvalue()).decode('ascii')
        return f'data:image/png;base64,{encoded}'
    except Exception:
        svg_image = qrcode.make(uri, image_factory=SvgPathImage)
        svg_data = svg_image.to_string(encoding='unicode')
        encoded = base64.b64encode(svg_data.encode('utf-8')).decode('ascii')
        return f'data:image/svg+xml;base64,{encoded}'
