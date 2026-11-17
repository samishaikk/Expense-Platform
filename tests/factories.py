from app.models import Category, Employee, Expense, Role
from app.security import create_access_token, hash_password

TEST_PASSWORD = 'password123'
_PASSWORD_HASH = hash_password(TEST_PASSWORD)


def make_employee(db, email, role=Role.employee, manager_id=None, name='Test User'):
    employee = Employee(
        name=name,
        email=email,
        password_hash=_PASSWORD_HASH,
        role=role,
        manager_id=manager_id,
    )
    db.add(employee)
    db.flush()
    return employee


def make_expense(db, employee_id, amount='100.00', category=Category.travel):
    expense = Expense(
        employee_id=employee_id,
        amount=amount,
        category=category,
        description='test expense',
    )
    db.add(expense)
    db.flush()
    return expense


def auth_header(employee):
    token = create_access_token(employee.id)
    return {'Authorization': f'Bearer {token}'}