from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class Supplier(BaseModel):
    name: Optional[str] = None
    gstin: str

    @field_validator('gstin')
    @classmethod
    def gstin_15_chars(cls, v):
        v =v.strip().upper()    
        if len(v) != 15:
            raise ValueError('GSTIN must be 15 characters ')
        return v

class LineItem(BaseModel):
    description: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(gt=0)

class Invoice(BaseModel):
    invoice_number: str
    invoice_date: date
    supplier: Supplier
    line_items: list[LineItem]
    subtotal: float
    tax: float
    total: float 
    

    @field_validator("invoice_date")
    @classmethod
    def not_in_future(cls, v):
        if v > date.today():
            raise ValueError("Invoice date cannot be in the future")
        return v
    @model_validator(mode="after")
    def total_match(self):
        if abs((self.subtotal + self.tax) - self.total) > 1:
            raise ValueError("Total does not match subtotal + tax")
        return self