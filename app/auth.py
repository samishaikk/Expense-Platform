import jwt
from fastapi import Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Employee,Role
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Employee:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Invalid or expired token',
        headers={'WWW-Authenticate": "Bearer'},
    )
    try:
        payload = decode_access_token(token)
        employee_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise credentials_error

    employee = db.get(Employee, employee_id)
    if employee is None:
        raise credentials_error
    return employee

def require_manager(current_user: Employee = Depends(get_current_user)) -> Employee:
    if current_user.role != Role.manager:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Manager role required")
    return current_user