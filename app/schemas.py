from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,ConfigDict,EmailStr,Field,model_validator
from app.models import Category,ExpenseStatus,Role


class EmployeeCreate(BaseModel):
    name:str = Field(min_length=1,max_length=100)
    email:EmailStr
    password:str = Field(min_length=8,max_length=72)
    role:Role = Role.employee
    manager_id:int | None=None
    
class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:int
    name:str
    email:EmailStr
    role:Role
    manager_id:int | None
    
class Token(BaseModel):
    access_token:str
    token_type:str = 'bearer'
    
class ExpenseCreate(BaseModel):
    amount:Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category:Category
    description:str = Field(default="", max_length=500)


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    amount: Decimal
    category: Category
    description: str
    status: ExpenseStatus
    created_at: datetime

class DecisionIn(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def comment_required_for_rejection(self):
        if self.decision == "rejected" and not (self.comment and self.comment.strip()):
            raise ValueError("A comment is required when rejecting an expense")
        return self
    
class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    expense_id: int
    actor_id: int
    actor_role: str
    action: str
    old_status: str | None
    new_status: str | None
    comment: str | None
    created_at: datetime