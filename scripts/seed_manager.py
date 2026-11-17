from getpass import getpass
from sqlalchemy import select

from app.db import Base,SessionLocal,engine
from app.models import Employee,Role
from app.security import hash_password


def main():
    Base.metadata.create_all(bind=engine)

    name = input('Manager name: ').strip()
    email = input('Manager email: ').strip()
    password = getpass('Password(min-8-characters): ')

    if not name or not email or not 8 <= len(password.encode('utf-8')) <= 72:
        print('Invalid input. Nothing created.')
        return

    with SessionLocal() as db:
        if db.scalar(select(Employee).where(Employee.email == email)):
            print('That email already exists. Nothing created.')
            return
        db.add(
            Employee(
                name=name,
                email=email,
                password_hash=hash_password(password),
                role=Role.manager,
            )
        )
        db.commit()
        print(f'Manager {email} created.')


if __name__ == '__main__':
    main()