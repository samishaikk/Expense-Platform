from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Employee,Role
from app.schemas import EmployeeCreate,EmployeeOut
from app.security import hash_password
from app.auth import require_manager

router = APIRouter(prefix="/employees",tags=["employees"])


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_manager),
):

    existing = db.scalar(select(Employee).where(Employee.email==payload.email))
    
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT,'Email registered already bro, try again')
    
    if payload.manager_id is not None:
        manager = db.get(Employee,payload.manager_id)
        if manager is None or manager.role != Role.manager:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,'manager_id got to refer to an existing manager,thank you')
        
    employee = Employee(
        name = payload.name,
        email = payload.email,
        password_hash = hash_password(payload.password),
        role = payload.role,
        manager_id = payload.manager_id,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("", response_model=list[EmployeeOut])
def list_my_team(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_manager),
):
    query = (
        select(Employee)
        .where(Employee.manager_id == current_user.id)
        .order_by(Employee.id)
    )
    return db.scalars(query).all()