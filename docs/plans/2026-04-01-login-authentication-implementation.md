# Login Authentication Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add JWT-based login authentication with a modal UI, protecting card management and spider routes while keeping scan/upload open.

**Architecture:** Backend auth service validates credentials from `.env`, issues JWT tokens (7-day expiry). Frontend uses `ProtectedRoute` wrapper + `LoginModal` component. Token stored in localStorage, attached via axios interceptor, 401 triggers re-login.

**Tech Stack:** FastAPI + python-jose + passlib (backend), React + antd-mobile + axios (frontend)

---

### Task 1: Backend — Auth service and login endpoint

**Files:**
- Modify: `backend/requirements.txt` — add `python-jose[cryptography]`, `passlib[bcrypt]`
- Modify: `backend/core/config.py` — add AUTH env vars
- Create: `backend/services/auth_service.py` — JWT create/verify logic
- Create: `backend/api/v1/auth.py` — login endpoint
- Modify: `main.py:66-75` — register auth router

**Step 1: Add dependencies to requirements.txt**

Add these two lines to `backend/requirements.txt`:
```
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

Then run: `pip install -r backend/requirements.txt`

**Step 2: Add auth config vars to `backend/core/config.py`**

After the OCR batch settings (line 88), add:
```python
# 認證設定
AUTH_USERNAME = os.getenv('AUTH_USERNAME', 'admin')
AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', 'changeme')
AUTH_SECRET_KEY = os.getenv('AUTH_SECRET_KEY', 'dev-secret-key-change-in-production')
AUTH_TOKEN_EXPIRE_DAYS = get_env_int('AUTH_TOKEN_EXPIRE_DAYS', 7)
```

Also add to the `Settings` class:
```python
AUTH_USERNAME = AUTH_USERNAME
AUTH_PASSWORD = AUTH_PASSWORD
AUTH_SECRET_KEY = AUTH_SECRET_KEY
AUTH_TOKEN_EXPIRE_DAYS = AUTH_TOKEN_EXPIRE_DAYS
```

**Step 3: Create `backend/services/auth_service.py`**

```python
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
```

**Step 4: Create `backend/api/v1/auth.py`**

```python
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
```

**Step 5: Register auth router in `main.py`**

After the existing `include_router` calls (after line 75), add:

```python
from backend.api.v1 import auth

app.include_router(
    auth.router,
    prefix=f"{API_V1_PREFIX}/auth",
    tags=["Authentication"]
)
```

Also add `auth` to the import on line 9: `from backend.api.v1 import card, ocr, auth`

**Step 6: Install deps and verify**

Run: `pip install -r backend/requirements.txt`
Run: `cd /data1/165/ocr_v2/manage_card && python -c "from backend.api.v1.auth import router; print('auth router OK')"`
Run: `cd /data1/165/ocr_v2/manage_card && python -c "from backend.services.auth_service import verify_credentials, create_access_token, verify_token; print('auth service OK')"`

Expected: Both print OK without errors.

**Step 7: Commit**

```bash
git add backend/requirements.txt backend/core/config.py backend/services/auth_service.py backend/api/v1/auth.py main.py
git commit -m "feat: add backend auth service with JWT login endpoint"
```

---

### Task 2: Backend — Protect card API endpoints with auth dependency

**Files:**
- Create: `backend/dependencies/__init__.py` (empty)
- Create: `backend/dependencies/auth.py` — `get_current_user` dependency
- Modify: `backend/api/v1/card.py` — add auth to protected endpoints (all except `crop-preview`)

**Step 1: Create `backend/dependencies/auth.py`**

```python
"""認證依賴項"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.services.auth_service import verify_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """驗證 JWT token，回傳 username"""
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效或過期的認證令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username
```

Create empty `backend/dependencies/__init__.py`:
```python
```

**Step 2: Add auth dependency to card router**

In `backend/api/v1/card.py`, add this import at the top:
```python
from backend.dependencies.auth import get_current_user
```

Then add `current_user: str = Depends(get_current_user)` parameter to ALL card endpoints EXCEPT `crop_preview` (line 252).

The endpoints to protect (add the dependency parameter):
- `GET /` (line 107) — list cards
- `GET /stats` (line 153) — statistics
- `PUT /{card_id}/crop` (line 327) — save crop
- `GET /{card_id}` (line 380) — get card detail
- `POST /` (line 413) — create card
- `PUT /{card_id}` (line 557) — update card
- `DELETE /all` (line 735) — delete all
- `DELETE /{card_id}` (line 773) — delete card
- `GET /export/download` (line 801) — export
- `POST /batch-import` (line 1015) — batch import
- `POST /text-import` (line 1168) — text import
- `POST /wcxf-import` (line 1427) — wcxf import
- `POST /classify-batch` (line 1504) — batch classify
- `POST /{card_id}/classify` (line 1607) — classify single
- `GET /tasks/{task_id}` (line 1652) — get task
- `POST /tasks/{task_id}/cancel` (line 1674) — cancel task

The endpoint to leave UNPROTECTED:
- `POST /crop-preview` (line 252) — used by scan flow

For each protected endpoint, add `current_user: str = Depends(get_current_user)` as the LAST parameter in the function signature. The `Depends` import should already exist from FastAPI.

**Step 3: Verify import works**

Run: `cd /data1/165/ocr_v2/manage_card && python -c "from backend.api.v1.card import router; print('card router with auth OK')"`

Expected: Prints OK.

**Step 4: Commit**

```bash
git add backend/dependencies/ backend/api/v1/card.py
git commit -m "feat: protect card API endpoints with JWT auth dependency"
```

---

### Task 3: Frontend — Auth utilities and API

**Files:**
- Create: `frontend/src/utils/auth.js` — token storage, expiry check
- Create: `frontend/src/api/auth.js` — login API call
- Modify: `frontend/src/utils/apiClient.js:15-35` — enable token interceptor, add 401 handling

**Step 1: Create `frontend/src/utils/auth.js`**

```javascript
const TOKEN_KEY = 'auth_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated() {
  const token = getToken();
  if (!token) return false;
  
  try {
    // JWT payload is the second part, base64 encoded
    const payload = JSON.parse(atob(token.split('.')[1]));
    // exp is in seconds, Date.now() is in milliseconds
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}
```

**Step 2: Create `frontend/src/api/auth.js`**

```javascript
import { api } from '../utils/apiClient';

export const login = (username, password) =>
  api.post('/auth/login', { username, password });
```

**Step 3: Update `frontend/src/utils/apiClient.js`**

Replace the commented-out token code in the request interceptor (lines 17-21) with:

```javascript
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
```

In the response error interceptor, update the 401 case (lines 77-79) to:

```javascript
        case 401:
          errorMessage = data?.detail || '未授權，請重新登入';
          localStorage.removeItem('auth_token');
          window.dispatchEvent(new Event('auth:logout'));
          break;
```

The `window.dispatchEvent` line lets the ProtectedRoute component listen for forced logouts globally.

**Step 4: Verify no syntax errors**

Run: `cd /data1/165/ocr_v2/manage_card/frontend && npx --yes acorn --ecma2020 --module src/utils/auth.js src/api/auth.js`

If acorn is not available, just visually verify the files.

**Step 5: Commit**

```bash
git add frontend/src/utils/auth.js frontend/src/api/auth.js frontend/src/utils/apiClient.js
git commit -m "feat: add frontend auth utilities, login API, and token interceptor"
```

---

### Task 4: Frontend — LoginModal component

**Files:**
- Create: `frontend/src/components/LoginModal.js`
- Create: `frontend/src/components/LoginModal.css`

**Step 1: Create `frontend/src/components/LoginModal.css`**

```css
.login-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.login-modal-card {
  width: 90%;
  max-width: 360px;
  border-radius: 12px;
  padding: 32px 24px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.login-modal-title {
  text-align: center;
  margin: 0 0 24px 0;
  font-size: 20px;
  color: #333;
}

.login-modal-error {
  color: #ff4d4f;
  text-align: center;
  margin-bottom: 16px;
  font-size: 14px;
}

.login-modal-input {
  margin-bottom: 16px;
}

.login-modal-button {
  margin-top: 8px;
}
```

**Step 2: Create `frontend/src/components/LoginModal.js`**

```javascript
import React, { useState } from 'react';
import { Input, Button } from 'antd-mobile';
import { login } from '../api/auth';
import { setToken } from '../utils/auth';
import './LoginModal.css';

const LoginModal = ({ visible, onSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!visible) return null;

  const handleLogin = async () => {
    if (!username || !password) {
      setError('請輸入帳號和密碼');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const data = await login(username, password);
      setToken(data.access_token);
      setUsername('');
      setPassword('');
      onSuccess();
    } catch (err) {
      setError(err.response?.data?.detail || '登入失敗，請確認帳號密碼');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleLogin();
  };

  return (
    <div className="login-modal-overlay">
      <div className="login-modal-card">
        <h3 className="login-modal-title">登入</h3>
        {error && <div className="login-modal-error">{error}</div>}
        <div className="login-modal-input">
          <Input
            placeholder="帳號"
            value={username}
            onChange={setUsername}
            onKeyDown={handleKeyDown}
            clearable
          />
        </div>
        <div className="login-modal-input">
          <Input
            type="password"
            placeholder="密碼"
            value={password}
            onChange={setPassword}
            onKeyDown={handleKeyDown}
            clearable
          />
        </div>
        <Button
          block
          color="primary"
          size="large"
          loading={loading}
          onClick={handleLogin}
          className="login-modal-button"
        >
          登入
        </Button>
      </div>
    </div>
  );
};

export default LoginModal;
```

**Step 3: Commit**

```bash
git add frontend/src/components/LoginModal.js frontend/src/components/LoginModal.css
git commit -m "feat: add LoginModal component"
```

---

### Task 5: Frontend — ProtectedRoute component and App.js integration

**Files:**
- Create: `frontend/src/components/ProtectedRoute.js`
- Modify: `frontend/src/App.js` — wrap protected routes, add login check to Home buttons

**Step 1: Create `frontend/src/components/ProtectedRoute.js`**

```javascript
import React, { useState, useEffect, useCallback } from 'react';
import { isAuthenticated } from '../utils/auth';
import LoginModal from './LoginModal';

const ProtectedRoute = ({ children }) => {
  const [authed, setAuthed] = useState(isAuthenticated());

  const handleLogout = useCallback(() => {
    setAuthed(false);
  }, []);

  useEffect(() => {
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, [handleLogout]);

  const handleLoginSuccess = () => {
    setAuthed(true);
  };

  return (
    <>
      <LoginModal visible={!authed} onSuccess={handleLoginSuccess} />
      {authed && children}
    </>
  );
};

export default ProtectedRoute;
```

**Step 2: Update `frontend/src/App.js`**

Replace the entire file content with:

```javascript
import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { Button, Space, Card } from 'antd-mobile';
import 'antd-mobile/es/global';
import './App.css';
import ScanUploadPage from './pages/ScanUploadPage';
import CardManagerPage from './pages/CardManagerPage';
import AddCardPage from './pages/AddCardPage';
import CardDetailPage from './pages/CardDetailPage';
import SpiderPage from './pages/SpiderPage';
import ProtectedRoute from './components/ProtectedRoute';
import LoginModal from './components/LoginModal';
import { isAuthenticated } from './utils/auth';

const Home = () => { 
  const navigate = useNavigate();
  const [showLogin, setShowLogin] = useState(false);
  const [pendingPath, setPendingPath] = useState(null);

  const handleProtectedClick = (path) => {
    if (isAuthenticated()) {
      navigate(path);
    } else {
      setPendingPath(path);
      setShowLogin(true);
    }
  };

  const handleLoginSuccess = () => {
    setShowLogin(false);
    if (pendingPath) {
      navigate(pendingPath);
      setPendingPath(null);
    }
  };

  return (
    <div className="App" style={{ minHeight: '100vh', background: '#f5f5f5', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
      <Card style={{ width: '90%', maxWidth: 400, margin: '0 auto', boxShadow: '0 2px 8px #eee' }}>
        <h2 style={{ marginBottom: 32 }}>名片 OCR 應用</h2>
        <Space direction="vertical" block style={{ width: '100%' }}>
          <Button color="primary" size="large" block style={{ fontSize: 18 }} onClick={() => navigate('/scan')}>
            開始掃描 / 上傳
          </Button>
          <Button color="default" size="large" block style={{ fontSize: 18 }} onClick={() => handleProtectedClick('/cards')}>
            名片管理
          </Button>
          <Button color="success" size="large" block style={{ fontSize: 18 }} onClick={() => handleProtectedClick('/spider')}>
            商機爬蟲
          </Button>
        </Space>
      </Card>
      <LoginModal visible={showLogin} onSuccess={handleLoginSuccess} />
    </div>
  );
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/scan" element={<ScanUploadPage />} />
        <Route path="/cards" element={<ProtectedRoute><CardManagerPage /></ProtectedRoute>} />
        <Route path="/add-card" element={<ProtectedRoute><AddCardPage /></ProtectedRoute>} />
        <Route path="/cards/:id" element={<ProtectedRoute><CardDetailPage /></ProtectedRoute>} />
        <Route path="/spider" element={<ProtectedRoute><SpiderPage /></ProtectedRoute>} />
      </Routes>
    </Router>
  );
}

export default App;
```

**Step 3: Verify frontend compiles**

Run: `cd /data1/165/ocr_v2/manage_card/frontend && npx react-scripts build 2>&1 | tail -5`

Expected: "Compiled successfully" or similar.

**Step 4: Commit**

```bash
git add frontend/src/components/ProtectedRoute.js frontend/src/App.js
git commit -m "feat: integrate ProtectedRoute and LoginModal into app routing"
```

---

### Task 6: Add `.env` auth variables and final verification

**Files:**
- Modify: `.env` — add AUTH variables (placeholder password)

**Step 1: Add auth variables to `.env`**

Append to `.env`:
```
# 認證設定
AUTH_USERNAME=admin
AUTH_PASSWORD=changeme
AUTH_SECRET_KEY=<generate-random-64-char-hex>
AUTH_TOKEN_EXPIRE_DAYS=7
```

Generate the secret key with: `python -c "import secrets; print(secrets.token_hex(32))"`

**Step 2: Manual end-to-end verification**

1. Start backend: `python main.py`
2. Test login API: `curl -X POST http://localhost:8006/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"changeme"}'`
   - Expected: `{"access_token":"eyJ...","token_type":"bearer"}`
3. Test protected endpoint without token: `curl http://localhost:8006/api/v1/cards/`
   - Expected: 401/403 error
4. Test protected endpoint with token: `curl http://localhost:8006/api/v1/cards/ -H "Authorization: Bearer <token-from-step-2>"`
   - Expected: card list response
5. Test unprotected endpoint: `curl -X POST http://localhost:8006/api/v1/cards/crop-preview ...`
   - Expected: works without token
6. Start frontend, verify:
   - Home page loads without login
   - `/scan` loads without login
   - Clicking "名片管理" shows login modal
   - After login, navigates to `/cards`
   - Direct visit to `/cards/123` shows login modal
   - After login, page content appears

**Step 3: Commit**

```bash
git add .env
git commit -m "feat: add auth environment variables"
```

**Step 4: Ask user for final username/password**

Prompt user to set their actual `AUTH_USERNAME` and `AUTH_PASSWORD` in `.env`.
