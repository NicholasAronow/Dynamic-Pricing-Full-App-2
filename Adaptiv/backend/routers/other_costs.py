from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import User, FixedCost, Employee
from auth import get_current_user
from pydantic import BaseModel, Field
from datetime import datetime

# Router definition
other_costs_router = APIRouter()

# Pydantic models for request/response
class FixedCostCreate(BaseModel):
    cost_type: str  # 'rent', 'utilities', etc.
    amount: float
    month: int
    year: int
    notes: Optional[str] = None
    
class FixedCostResponse(BaseModel):
    id: int
    cost_type: str
    amount: float
    month: int
    year: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class EmployeeCreate(BaseModel):
    name: str
    pay_type: str  # 'salary' or 'hourly'
    salary: Optional[float] = None
    hourly_rate: Optional[float] = None
    weekly_hours: Optional[float] = None
    
class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    pay_type: Optional[str] = None
    salary: Optional[float] = None
    hourly_rate: Optional[float] = None
    weekly_hours: Optional[float] = None
    active: Optional[bool] = None
    
class EmployeeResponse(BaseModel):
    id: int
    name: str
    pay_type: str
    salary: Optional[float] = None
    hourly_rate: Optional[float] = None
    weekly_hours: Optional[float] = None
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# Fixed Cost Endpoints
@other_costs_router.post("/fixed-costs", response_model=FixedCostResponse)
def create_fixed_cost(
    fixed_cost: FixedCostCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    db_fixed_cost = FixedCost(
        user_id=current_user.id,
        cost_type=fixed_cost.cost_type,
        amount=fixed_cost.amount,
        month=fixed_cost.month,
        year=fixed_cost.year,
        notes=fixed_cost.notes
    )
    
    db.add(db_fixed_cost)
    db.commit()
    db.refresh(db_fixed_cost)
    
    return db_fixed_cost

@other_costs_router.get("/fixed-costs", response_model=List[FixedCostResponse])
def get_fixed_costs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cost_type: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None
):
    query = db.query(FixedCost).filter(FixedCost.user_id == current_user.id)
    
    if cost_type:
        query = query.filter(FixedCost.cost_type == cost_type)
    if month:
        query = query.filter(FixedCost.month == month)
    if year:
        query = query.filter(FixedCost.year == year)
    
    return query.all()

@other_costs_router.put("/fixed-costs/{fixed_cost_id}", response_model=FixedCostResponse)
def update_fixed_cost(
    fixed_cost_id: int,
    fixed_cost: FixedCostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_fixed_cost = db.query(FixedCost).filter(
        FixedCost.id == fixed_cost_id, 
        FixedCost.user_id == current_user.id
    ).first()
    
    if db_fixed_cost is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fixed cost not found"
        )
    
    db_fixed_cost.cost_type = fixed_cost.cost_type
    db_fixed_cost.amount = fixed_cost.amount
    db_fixed_cost.month = fixed_cost.month
    db_fixed_cost.year = fixed_cost.year
    db_fixed_cost.notes = fixed_cost.notes
    
    db.commit()
    db.refresh(db_fixed_cost)
    
    return db_fixed_cost

@other_costs_router.delete("/fixed-costs/{fixed_cost_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fixed_cost(
    fixed_cost_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_fixed_cost = db.query(FixedCost).filter(
        FixedCost.id == fixed_cost_id, 
        FixedCost.user_id == current_user.id
    ).first()
    
    if db_fixed_cost is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fixed cost not found"
        )
    
    db.delete(db_fixed_cost)
    db.commit()
    
    return None

# Employee Endpoints
@other_costs_router.post("/employees", response_model=EmployeeResponse)
def create_employee(
    employee: EmployeeCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Validate that appropriate fields are provided based on pay_type
    if employee.pay_type == 'salary' and employee.salary is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salary amount is required for salary pay type"
        )
    
    if employee.pay_type == 'hourly' and (employee.hourly_rate is None or employee.weekly_hours is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hourly rate and weekly hours are required for hourly pay type"
        )
    
    db_employee = Employee(
        user_id=current_user.id,
        name=employee.name,
        pay_type=employee.pay_type,
        salary=employee.salary,
        hourly_rate=employee.hourly_rate,
        weekly_hours=employee.weekly_hours,
        active=True
    )
    
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    
    return db_employee

@other_costs_router.get("/employees", response_model=List[EmployeeResponse])
def get_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_only: bool = True
):
    query = db.query(Employee).filter(Employee.user_id == current_user.id)
    
    if active_only:
        query = query.filter(Employee.active == True)
    
    return query.all()

@other_costs_router.get("/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    employee = db.query(Employee).filter(
        Employee.id == employee_id, 
        Employee.user_id == current_user.id
    ).first()
    
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    return employee

@other_costs_router.put("/employees/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_employee = db.query(Employee).filter(
        Employee.id == employee_id, 
        Employee.user_id == current_user.id
    ).first()
    
    if db_employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Update fields if provided
    if employee_update.name is not None:
        db_employee.name = employee_update.name
    
    if employee_update.pay_type is not None:
        db_employee.pay_type = employee_update.pay_type
        
    if employee_update.salary is not None:
        db_employee.salary = employee_update.salary
        
    if employee_update.hourly_rate is not None:
        db_employee.hourly_rate = employee_update.hourly_rate
        
    if employee_update.weekly_hours is not None:
        db_employee.weekly_hours = employee_update.weekly_hours
        
    if employee_update.active is not None:
        db_employee.active = employee_update.active
    
    db.commit()
    db.refresh(db_employee)
    
    return db_employee

@other_costs_router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_employee = db.query(Employee).filter(
        Employee.id == employee_id, 
        Employee.user_id == current_user.id
    ).first()
    
    if db_employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Soft delete - mark as inactive instead of removing from database
    db_employee.active = False
    db.commit()
    
    return None
