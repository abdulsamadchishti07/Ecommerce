import base64
import hashlib
import json
from cryptography.fernet import Fernet
from django.conf import settings


def _get_cipher():
    """Derive a deterministic 32-byte Fernet key from Django SECRET_KEY."""
    secret_bytes = settings.SECRET_KEY.encode("utf-8")
    key_32bytes = hashlib.sha256(secret_bytes).digest()
    fernet_key = base64.urlsafe_b64encode(key_32bytes)
    return Fernet(fernet_key)


def sanitize_payment_data(data):
    """
    Remove or mask highly sensitive fields like raw credit card numbers, CVC,
    or client secrets before storing provider details.
    """
    if not isinstance(data, dict):
        return data

    sanitized = json.loads(json.dumps(data))  # deep copy
    
    sensitive_keys = ["client_secret", "card_number", "cvc", "cvv", "secret_key", "password"]
    
    def _recursive_sanitize(obj):
        if isinstance(obj, dict):
            for k in list(obj.keys()):
                if any(sens in k.lower() for sens in sensitive_keys):
                    obj[k] = "[ENCRYPTED/REDACTED]"
                else:
                    _recursive_sanitize(obj[k])
        elif isinstance(obj, list):
            for item in obj:
                _recursive_sanitize(item)

    _recursive_sanitize(sanitized)
    return sanitized


def encrypt_payment_data(data):
    """
    Sanitize and encrypt dictionary or string data into an encrypted payload.
    Returns base64 Fernet encrypted string.
    """
    if data is None or data == "" or data == {}:
        return ""

    if isinstance(data, (dict, list)):
        data = sanitize_payment_data(data)
        data_str = json.dumps(data)
    else:
        data_str = str(data)

    cipher = _get_cipher()
    encrypted_bytes = cipher.encrypt(data_str.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_payment_data(encrypted_str):
    """
    Decrypt base64 Fernet encrypted string into original dictionary or string.
    If decryption fails or input is plain unencrypted data (backwards compatibility), returns input.
    """
    if not encrypted_str:
        return {} if isinstance(encrypted_str, dict) else ""

    if isinstance(encrypted_str, (dict, list)):
        return encrypted_str

    try:
        cipher = _get_cipher()
        decrypted_bytes = cipher.decrypt(encrypted_str.encode("utf-8"))
        decrypted_str = decrypted_bytes.decode("utf-8")
        try:
            return json.loads(decrypted_str)
        except json.JSONDecodeError:
            return decrypted_str
    except Exception:
        # Fallback if text was not encrypted or key changed
        try:
            return json.loads(encrypted_str)
        except Exception:
            return encrypted_str
