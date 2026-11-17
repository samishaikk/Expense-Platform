from fastapi import FastAPI
from app import models  
from app.db import Base, engine
from app.logging_config import setup_logging
from app.middleware import log_requests
from app.routers import auth, employees, expenses, ops

setup_logging()

app = FastAPI(title="Expense Reimbursement API")
app.middleware("http")(log_requests)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(expenses.router)
app.include_router(ops.router)