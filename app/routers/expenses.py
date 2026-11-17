from fastapi import APIRouter,Depends,HTTPException,Query,status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import AuditLog, Category, Employee, Expense, ExpenseStatus
from app.schemas import ExpenseCreate, ExpenseOut

router = APIRouter(prefix='/expenses', tags=['expenses'])


@router.post('', response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def submit_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    expense = Expense(
        employee_id=current_user.id,
        amount=payload.amount,
        category=payload.category,
        description=payload.description,
    )
    db.add(expense)
    db.flush()  

    db.add(
        AuditLog(
            expense_id=expense.id,
            actor_id=current_user.id,
            actor_role=current_user.role.value,
            action='submitted',
            old_status=None,
            new_status=ExpenseStatus.pending.value,
        )
    )
    db.commit()  # saves the expense and the audit row together
    db.refresh(expense)
    return expense


@router.get('', response_model=list[ExpenseOut])
def list_my_expenses(
    status_filter: ExpenseStatus | None = Query(None, alias='status'),
    category: Category | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    query = select(Expense).where(Expense.employee_id == current_user.id)
    if status_filter is not None:
        query = query.where(Expense.status == status_filter)
    if category is not None:
        query = query.where(Expense.category == category)
    query = query.order_by(Expense.id.desc()).limit(limit).offset(offset)
    return db.scalars(query).all()


@router.get('/{expense_id}', response_model=ExpenseOut)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Expense not found')

    is_owner = expense.employee_id == current_user.id
    is_their_manager = False
    if not is_owner:
        owner = db.get(Employee, expense.employee_id)
        is_their_manager = owner is not None and owner.manager_id == current_user.id

    if not (is_owner or is_their_manager):
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Expense not found')
    return expense