from pydantic import BaseModel,ConfigDict,EmailStr,Field
from app.models import Role

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