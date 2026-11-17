from fastapi import APIRouter,Depends,HTTPException,Query,status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_manager
from app.db import get_db
from app.models import AuditLog, Category, Employee, Expense, ExpenseStatus
from app.schemas import AuditOut, DecisionIn, ExpenseCreate, ExpenseOut

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


@router.get("/team", response_model=list[ExpenseOut])
def list_team_expenses(
    status_filter: ExpenseStatus | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_manager),
):
    query = (
        select(Expense)
        .join(Employee, Expense.employee_id == Employee.id)
        .where(Employee.manager_id == current_user.id)
    )
    if status_filter is not None:
        query = query.where(Expense.status == status_filter)
    query = query.order_by(Expense.id.desc()).limit(limit).offset(offset)
    return db.scalars(query).all()


def load_visible_expense(expense_id: int, db: Session, user: Employee) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")

    if expense.employee_id == user.id:
        return expense

    owner = db.get(Employee, expense.employee_id)
    if owner is not None and owner.manager_id == user.id:
        return expense

    raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    return load_visible_expense(expense_id, db, current_user)


@router.get("/{expense_id}/history", response_model=list[AuditOut])
def get_expense_history(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    load_visible_expense(expense_id, db, current_user)
    query = (
        select(AuditLog)
        .where(AuditLog.expense_id == expense_id)
        .order_by(AuditLog.id)
    )
    return db.scalars(query).all()

@router.post("/{expense_id}/decision", response_model=ExpenseOut)
def decide_expense(
    expense_id: int,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_manager),
):
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")

    if expense.employee_id == current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You cannot decide your own expense"
        )

    owner = db.get(Employee, expense.employee_id)
    if owner is None or owner.manager_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")

    new_status = ExpenseStatus(payload.decision)

    result = db.execute(
        update(Expense)
        .where(Expense.id == expense_id, Expense.status == ExpenseStatus.pending)
        .values(status=new_status)
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Expense has already been decided")

    db.add(
        AuditLog(
            expense_id=expense_id,
            actor_id=current_user.id,
            actor_role=current_user.role.value,
            action=payload.decision,
            old_status=ExpenseStatus.pending.value,
            new_status=new_status.value,
            comment=payload.comment,
        )
    )
    db.commit()
    db.refresh(expense)
    return expense