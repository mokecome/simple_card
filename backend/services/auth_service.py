"""認證服務 — JWT token 產生與驗證"""
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from backend.core.config import AUTH_USERNAME, AUTH_PASSWORD, AUTH_SECRET_KEY, AUTH_TOKEN_EXPIRE_DAYS

ALGORITHM = "HS256"


def verify_credentials(username: str, password: str) -> bool:
    """驗證帳號密碼"""
    return username == AUTH_USERNAME and password == AUTH_PASSWORD


def create_access_token(username: str) -> str:
    """產生 JWT token"""
    expire = datetime.now(timezone.utc) + timedelta(days=AUTH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, AUTH_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str | None:
    """驗證 token，回傳 username 或 None"""
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
