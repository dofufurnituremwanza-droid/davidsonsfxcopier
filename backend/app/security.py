import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Any
from jose import jwt
from cryptography.fernet import Fernet
import base64
import hashlib
from app.config import settings

# Derive valid 32-byte urlsafe Fernet key from secret if necessary
def get_fernet() -> Fernet:
    try:
        return Fernet(settings.ENCRYPTION_KEY.encode())
    except Exception:
        # Fallback derive deterministic 32-byte urlsafe base64 key
        digest = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
        urlsafe_key = base64.urlsafe_b64encode(digest)
        return Fernet(urlsafe_key)

fernet = get_fernet()

def encrypt_credential(plain_text: str) -> str:
    """Encrypt MT5 credentials before storing in the database."""
    if not plain_text:
        return ""
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_credential(cipher_text: str) -> str:
    """Decrypt MT5 credentials for terminal login."""
    if not cipher_text:
        return ""
    try:
        return fernet.decrypt(cipher_text.encode()).decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        return ""

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    # Truncate password to 72 bytes if needed (bcrypt spec)
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

