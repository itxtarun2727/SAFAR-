"""
auth.py — JWT Authentication, Demo User Roster, and Scoped RBAC Guards.
"""

from typing import Dict, Any, List, Optional
from datetime import timedelta
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from clock import Clock

DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    if not DEMO_MODE:
        raise RuntimeError("JWT_SECRET environment variable is strictly required in non-demo mode.")
    JWT_SECRET = "safar-demo-ephemeral-jwt-secret-not-for-production"

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class AuthUser(BaseModel):
    user_id: str
    role: str
    name: str
    institution_id: Optional[str] = None
    university_id: Optional[str] = None
    bank_id: Optional[str] = None
    institution_ids: List[str] = []


# ── Demo Personas Roster for SIH Evaluation ───────────────────────────────────

DEMO_USERS: Dict[str, Dict[str, Any]] = {
    # University Officer 1: Demo University A
    "priya": {
        "user_id": "u-aicte-01",
        "role": "aicte_officer",
        "name": "Priya Sharma (Demo University A Officer)",
        "university_id": "univ-001",
        "institution_id": None,
        "bank_id": None,
        "institution_ids": [],
    },
    # University Officer 2: Demo University B
    "rajan": {
        "user_id": "u-aicte-02",
        "role": "aicte_officer",
        "name": "Rajan Mehta (Demo University B Officer)",
        "university_id": "univ-002",
        "institution_id": None,
        "bank_id": None,
        "institution_ids": [],
    },
    # Senior AICTE Manager: All Universities
    "anita": {
        "user_id": "u-aicte-sr-01",
        "role": "aicte_senior",
        "name": "Dr. Anita Rao (Senior AICTE Director)",
        "university_id": None,
        "institution_id": None,
        "bank_id": None,
        "institution_ids": [],
    },
    # Bank Users: 1 per demo bank [SIMULATED]
    "bank_a": {
        "user_id": "u-bank-01",
        "role": "bank_checker",
        "name": "Demo Bank A Checker [SIMULATED]",
        "university_id": None,
        "institution_id": None,
        "bank_id": "bank-001",
        "institution_ids": [],
    },
    "bank_b": {
        "user_id": "u-bank-02",
        "role": "bank_checker",
        "name": "Demo Bank B Checker [SIMULATED]",
        "university_id": None,
        "institution_id": None,
        "bank_id": "bank-002",
        "institution_ids": [],
    },
    "bank_c": {
        "user_id": "u-bank-03",
        "role": "bank_checker",
        "name": "Demo Bank C Checker [SIMULATED]",
        "university_id": None,
        "institution_id": None,
        "bank_id": "bank-003",
        "institution_ids": [],
    },
    # Backward compatible aliases for previous bank personas
    "bank_maker": {
        "user_id": "u-bank-01-maker",
        "role": "bank_checker",
        "name": "Demo Bank A Maker [SIMULATED]",
        "university_id": None,
        "institution_id": None,
        "bank_id": "bank-001",
        "institution_ids": [],
    },
    "bank_checker": {
        "user_id": "u-bank-01",
        "role": "bank_checker",
        "name": "Demo Bank A Checker [SIMULATED]",
        "university_id": None,
        "institution_id": None,
        "bank_id": "bank-001",
        "institution_ids": [],
    },
    # College Users: 3 colleges across 2 universities
    "inst_user": {
        "user_id": "u-inst-01",
        "role": "institution",
        "name": "Delhi Institute of Technology User",
        "institution_id": "inst-001",
        "university_id": "univ-001",
        "bank_id": None,
        "institution_ids": ["inst-001"],
    },
    "inst_apex": {
        "user_id": "u-inst-02",
        "role": "institution",
        "name": "Apex Engineering College User",
        "institution_id": "inst-002",
        "university_id": "univ-001",
        "bank_id": None,
        "institution_ids": ["inst-002"],
    },
    "inst_sunrise": {
        "user_id": "u-inst-03",
        "role": "institution",
        "name": "Sunrise Institute of Technology User",
        "institution_id": "inst-003",
        "university_id": "univ-002",
        "bank_id": None,
        "institution_ids": ["inst-003"],
    },
    # Auditor: Read-only, everything
    "auditor": {
        "user_id": "u-auditor-01",
        "role": "auditor",
        "name": "CAG & AICTE Audit Observer",
        "university_id": None,
        "institution_id": None,
        "bank_id": None,
        "institution_ids": [],
    },
    # Admin: Rules & demo controls
    "admin": {
        "user_id": "u-admin-01",
        "role": "admin",
        "name": "SAFAR Portal Super Administrator",
        "university_id": None,
        "institution_id": None,
        "bank_id": None,
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
        "institution_id": user.institution_id,
        "university_id": user.university_id,
        "bank_id": user.bank_id,
        "institution_ids": user.institution_ids,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> AuthUser:
    """FastAPI dependency to extract and validate authenticated user."""
    if not token:
        # Default to Anita (Senior AICTE Director) for demo convenience if no token provided
        return AuthUser(
            user_id="u-aicte-sr-01",
            role="aicte_senior",
            name="Dr. Anita Rao (Senior AICTE Director - Default)",
            university_id=None,
            institution_id=None,
            bank_id=None,
            institution_ids=[],
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return AuthUser(
            user_id=payload["sub"],
            name=payload["name"],
            role=payload["role"],
            institution_id=payload.get("institution_id"),
            university_id=payload.get("university_id"),
            bank_id=payload.get("bank_id"),
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
