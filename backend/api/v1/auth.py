"""認證 API 端點"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.auth_service import verify_credentials, create_access_token

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """登入端點"""
    if not verify_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = create_access_token(request.username)
    return LoginResponse(access_token=token)
