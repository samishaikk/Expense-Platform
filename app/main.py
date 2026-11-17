from fastapi import FastAPI
from app import models  
from app.db import Base, engine
from app.routers import employees

app = FastAPI(title="expense Reimbursement API")
Base.metadata.create_all(bind=engine)
app.include_router(employees.router)

@app.get('/health')
def health():
    return {'status':'ok'}