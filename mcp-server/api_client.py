"""HTTP client for the business card backend API with automatic JWT management."""

from __future__ import annotations

import time
from typing import Any

import httpx

from config import BACKEND_URL, BACKEND_USERNAME, BACKEND_PASSWORD


class BackendClient:
    """Wraps all HTTP calls to the FastAPI backend.

    - Automatically logs in and caches the JWT token.
    - Refreshes the token when it expires (every 2.5 days to stay safe).
    - Provides ``get`` / ``post`` / ``post_form`` helpers.
    """

    TOKEN_REFRESH_SECONDS = 2.5 * 24 * 3600  # refresh before 3-day expiry

    def __init__(
        self,
        base_url: str = BACKEND_URL,
        username: str = BACKEND_USERNAME,
        password: str = BACKEND_PASSWORD,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._token: str | None = None
        self._token_obtained_at: float = 0

    # ------------------------------------------------------------------ auth

    async def _login(self) -> str:
        """POST /api/v1/auth/login and return the access_token."""
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                f"{self._base_url}/api/v1/auth/login",
                json={"username": self._username, "password": self._password},
            )
            resp.raise_for_status()
            data = resp.json()
            # Login endpoint may return {access_token} directly or wrapped in {data: {access_token}}
            if "data" in data and isinstance(data["data"], dict):
                return data["data"]["access_token"]
            return data["access_token"]

    async def _ensure_token(self) -> str:
        """Return a valid token, refreshing if needed."""
        now = time.time()
        if self._token and (now - self._token_obtained_at) < self.TOKEN_REFRESH_SECONDS:
            return self._token
        self._token = await self._login()
        self._token_obtained_at = now
        return self._token

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------ HTTP helpers

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """Authenticated GET request. Returns parsed JSON body."""
        token = await self._ensure_token()
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as http:
            resp = await http.get(
                f"{self._base_url}{path}",
                params=params,
                headers=self._auth_headers(token),
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, json: dict[str, Any] | None = None) -> dict:
        """Authenticated POST with JSON body."""
        token = await self._ensure_token()
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http:
            resp = await http.post(
                f"{self._base_url}{path}",
                json=json,
                headers=self._auth_headers(token),
            )
            resp.raise_for_status()
            return resp.json()

    async def post_form(
        self,
        path: str,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict:
        """Authenticated POST with multipart form-data (for file uploads)."""
        token = await self._ensure_token()
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as http:
            resp = await http.post(
                f"{self._base_url}{path}",
                data=data,
                files=files,
                headers=self._auth_headers(token),
            )
            resp.raise_for_status()
            return resp.json()

    async def post_file(self, path: str, file_bytes: bytes, filename: str) -> dict:
        """Authenticated POST uploading a single file as 'file' field."""
        token = await self._ensure_token()
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as http:
            resp = await http.post(
                f"{self._base_url}{path}",
                files={"file": (filename, file_bytes, "image/jpeg")},
                headers=self._auth_headers(token),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_no_auth(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """GET without authentication (for public endpoints like /health, /spider/api/*)."""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as http:
            resp = await http.get(
                f"{self._base_url}{path}",
                params=params,
            )
            resp.raise_for_status()
            return resp.json()


# Module-level singleton
client = BackendClient()
