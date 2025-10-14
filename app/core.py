from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext


# Security config: no .env per spec
JWT_SECRET = "SUPER_SECRET_JWT_BAAPMEET_2025"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Use bcrypt_sha256 to avoid bcrypt's 72-byte password limit while
# still leveraging bcrypt for secure storage. Keep plain bcrypt for
# backward compatibility with any existing hashes.
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(data: Dict[str, Any], expires_minutes: int | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None

