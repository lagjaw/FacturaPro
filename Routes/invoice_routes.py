from fastapi import APIRouter, HTTPException, Body, Path, Depends, Query
from typing import List, Optional
from pydantic import BaseModel, Field, constr
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session


from Services.invoice_service import InvoiceService
from Models.Invoice import Invoice
from database import get_db_connection

router = APIRouter(tags=["invoices"])

# Pydantic models
class InvoiceItemCreate(BaseModel):
    product_id: str = Field(..., description="ID of the product")
    quantity: int = Field(..., gt=0, description="Quantity of the product")

    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": "123e4567-e89b-12d3-a456-426614174000",
                "quantity": 5
            }
        }
    }

class InvoiceCreate(BaseModel):
    client_id: str = Field(..., description="ID of the client")
    items: List[InvoiceItemCreate] = Field(..., description="List of items to include in the invoice")
    due_date: date = Field(..., description="Due date for the invoice")

    model_config = {
        "json_schema_extra": {
            "example": {
                "client_id": "123e4567-e89b-12d3-a456-426614174000",
                "items": [
                    {
                        "product_id": "123e4567-e89b-12d3-a456-426614174000",
                        "quantity": 5
                    }
                ],
                "due_date": "2025-02-01"
            }
        }
    }

class InvoiceItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal

class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    date: datetime
    due_date: datetime
    bill_to: str
    total: Decimal
    subtotal: Decimal
    tax: Decimal
    status: str
    items: List[InvoiceItem]

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "invoice_number": "INV-20250201-123456",
                "date": "2025-02-01T12:00:00",
                "due_date": "2025-03-01T12:00:00",
                "bill_to": "Client Name",
                "total": 1200.00,
                "subtotal": 1000.00,
                "tax": 200.00,
                "status": "draft",
                "items": [
                    {
                        "product_id": "123e4567-e89b-12d3-a456-426614174000",
                        "product_name": "Product Name",
                        "quantity": 5,
                        "unit_price": 200.00,
                        "total_price": 1000.00
                    }
                ]
            }
        }
    }

def get_invoice_service(db: Session = Depends(get_db_connection)) -> InvoiceService:
    return InvoiceService(db)

@router.post(
    "/invoices",
    response_model=InvoiceResponse,
    summary="Create Invoice",
    description="Create a new invoice with items"
)
async def create_invoice(
    invoice_data: InvoiceCreate,
    service: InvoiceService = Depends(get_invoice_service)
):
    """
    Create a new invoice.

    - Creates invoice with specified items
    - Updates product stock levels
    - Generates stock alerts if needed
    - Returns the created invoice details
    """
    try:
        invoice = service.create_invoice(
            client_id=invoice_data.client_id,
            items=[item.model_dump() for item in invoice_data.items],
            due_date=invoice_data.due_date
        )

        return {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "date": invoice.date,
            "due_date": invoice.due_date,
            "bill_to": invoice.bill_to,
            "total": invoice.total,
            "subtotal": invoice.subtotal,
            "tax": invoice.tax,
            "status": invoice.status,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                }
                for item in invoice.invoice_products
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create invoice: {str(e)}"
        )

@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get Invoice",
    description="Get details of a specific invoice"
)
async def get_invoice(
    invoice_id: str = Path(..., description="ID of the invoice to retrieve"),
    db: Session = Depends(get_db_connection)
):
    """
    Get details of a specific invoice.

    - Returns complete invoice information
    - Includes all invoice items and their details
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "date": invoice.date,
        "due_date": invoice.due_date,
        "bill_to": invoice.bill_to,
        "total": invoice.total,
        "subtotal": invoice.subtotal,
        "tax": invoice.tax,
        "status": invoice.status,
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price
            }
            for item in invoice.invoice_products
        ]
    }

@router.get(
    "/invoices",
    response_model=List[InvoiceResponse],
    summary="List Invoices",
    description="List invoices with optional filtering"
)
async def list_invoices(
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    status: Optional[str] = Query(None, description="Filter by invoice status"),
    from_date: Optional[date] = Query(None, description="Filter by start date"),
    to_date: Optional[date] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_db_connection)
):
    """
    List invoices with optional filtering.

    - Can filter by client, status, and date range
    - Returns list of matching invoices
    """
    query = db.query(Invoice)

    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    if status:
        query = query.filter(Invoice.status == status)
    if from_date:
        query = query.filter(Invoice.date >= from_date)
    if to_date:
        query = query.filter(Invoice.date <= to_date)

    invoices = query.all()

    return [
        {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "date": invoice.date,
            "due_date": invoice.due_date,
            "bill_to": invoice.bill_to,
            "total": invoice.total,
            "subtotal": invoice.subtotal,
            "tax": invoice.tax,
            "status": invoice.status,
            "items": [
                {
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                }
                for item in invoice.invoice_products
            ]
        }
        for invoice in invoices
    ]

@router.put(
    "/invoices/{invoice_id}/status",
    summary="Update Invoice Status",
    description="Update the status of an invoice"
)
async def update_invoice_status(
    invoice_id: str = Path(..., description="ID of the invoice to update"),
    status: str = Body(..., embed=True, description="New status for the invoice"),
    db: Session = Depends(get_db_connection)
):
    """
    Update the status of an invoice.

    - Updates invoice status
    - Returns updated invoice details
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.status = status
    db.commit()

    return {"message": f"Invoice status updated to {status}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(router, host="0.0.0.0", port=8000)
