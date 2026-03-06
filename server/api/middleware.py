"""Authentication middleware — Bearer token verification."""

from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_security = HTTPBearer()
_auth_token: str = ""


def set_auth_token(token: str):
    global _auth_token
    _auth_token = token


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(_security),
) -> str:
    if not _auth_token:
        return "anonymous"
    if credentials.credentials != _auth_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials
