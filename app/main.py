from fastapi import FastAPI
from app import  models
from app.db import Base,engine

app = FastAPI(title="expense Reimbursement API")
Base.metadata.create_all(bind=engine)

@app.get('/health')
def health():
    return {'status':'ok'}