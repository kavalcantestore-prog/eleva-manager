from fastapi import Request, HTTPException
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from database import get_db, verify_password, hash_password
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "eleva-secret-key-change-in-production")
serializer = URLSafeTimedSerializer(SECRET_KEY)
SESSION_COOKIE = "eleva_session"
MAX_AGE = 60 * 60 * 8  # 8 hours


def create_session(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})


def get_current_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        data = serializer.loads(token, max_age=MAX_AGE)
        user_id = data["user_id"]
    except (BadSignature, SignatureExpired, KeyError):
        return None

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def require_user(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user


def authenticate_user(email: str, password: str):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user
