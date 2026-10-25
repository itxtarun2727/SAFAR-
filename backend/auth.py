"""
auth.py — JWT Authentication, Demo User Roster, and Role / Institution Guards.
"""

from typing import Dict, Any, List, Optional
from datetime import timedelta
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from clock import Clock

JWT_SECRET = os.getenv("JWT_SECRET", "safar-super-secret-key-min-32-chars-long-change-in-prod!!")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class AuthUser(BaseModel):
    user_id: str
    role: str
    name: str
    institution_ids: List[str] = []


# ── Demo Users Roster for SIH Evaluation ──────────────────────────────────────

DEMO_USERS: Dict[str, Dict[str, Any]] = {
    "priya": {
        "user_id": "u-aicte-01",
        "role": "aicte_officer",
        "name": "Priya Sharma",
        "institution_ids": [],
    },
    "rajan": {
        "user_id": "u-aicte-02",
        "role": "aicte_officer",
        "name": "Rajan Mehta",
        "institution_ids": [],
    },
    "anita": {
        "user_id": "u-aicte-sr-01",
        "role": "aicte_senior",
        "name": "Dr. Anita Rao",
        "institution_ids": [],
    },
    "bank_maker": {
        "user_id": "u-bank-01",
        "role": "bank_officer",
        "name": "Bank Maker [SIMULATED]",
        "institution_ids": [],
    },
    "bank_checker": {
        "user_id": "u-bank-02",
        "role": "bank_checker",
        "name": "Bank Checker [SIMULATED]",
        "institution_ids": [],
    },
    "inst_user": {
        "user_id": "u-inst-01",
        "role": "institution",
        "name": "Greenfield Tech User",
        "institution_ids": ["inst-001"],
    },
    "auditor": {
        "user_id": "u-auditor-01",
        "role": "auditor",
        "name": "Audit Observer",
        "institution_ids": [],
    },
    "admin": {
        "user_id": "u-admin-01",
        "role": "admin",
        "name": "Portal Admin",
        "institution_ids": [],
    },
}

DEMO_PASSWORD = "demo1234"


def authenticate_user(username: str, password: str) -> Optional[AuthUser]:
    """Verify demo user credentials."""
    user_data = DEMO_USERS.get(username.lower())
    if user_data and password == DEMO_PASSWORD:
        return AuthUser(**user_data)
    return None


def create_access_token(user: AuthUser, expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token."""
    expire = Clock.now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user.user_id,
        "name": user.name,
        "role": user.role,
        "institution_ids": user.institution_ids,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> AuthUser:
    """FastAPI dependency to extract and validate authenticated user."""
    # Allow a fallback default for unauthenticated local browser preview
    if not token:
        # Default to AICTE Officer for demo convenience if no token provided
        return AuthUser(
            user_id="u-aicte-01",
            role="aicte_officer",
            name="Priya Sharma (Auto-login)",
            institution_ids=[]
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return AuthUser(
            user_id=payload["sub"],
            name=payload["name"],
            role=payload["role"],
            institution_ids=payload.get("institution_ids", []),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(*roles: str):
    """Dependency factory enforcing role permissions."""
    def _checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: User role '{user.role}' not in required {roles}."
            )
        return user
    return _checker


def check_institution_access(user: AuthUser, institution_id: str) -> None:
    """Ensure institution role user only accesses their own institution."""
    if user.role == "institution" and institution_id not in user.institution_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Institution account scope violation."
        )
