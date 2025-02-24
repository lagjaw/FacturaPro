from fastapi import APIRouter, HTTPException, Path, Query, Depends
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from pydantic import BaseModel

from Services.ReportService import ReportService
from database import get_db_connection

router = APIRouter(tags=["reports"])


def get_report_service(db: Session = Depends(get_db_connection)) -> ReportService:
    return ReportService(db)


@router.get("/reports/clients/{client_id}/statement", response_model=Dict)
async def get_client_statement(
        client_id: str = Path(..., description="ID of the client to generate statement for"),
        service: ReportService = Depends(get_report_service)
):
    """
    Generate a detailed statement for a client.

    Returns:
    - Client information
    - Summary of financial status
    - List of invoices
    - List of transactions
    - Current balance
    """
    try:
        statement = await service.generate_client_statement(client_id)
        return statement
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate client statement: {str(e)}"
        )


@router.get("/reports/suppliers/{supplier_id}/report", response_model=Dict)
async def get_supplier_report(
        supplier_id: str = Path(..., description="ID of the supplier to generate report for"),
        service: ReportService = Depends(get_report_service)
):
    """
    Generate a detailed report for a supplier.

    Returns:
    - Supplier information
    - Product inventory summary
    - List of products with stock levels
    - Stock alerts (low stock and expired products)
    - Total stock value
    """
    try:
        report = await service.generate_supplier_report(supplier_id)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate supplier report: {str(e)}"
        )


@router.get("/reports/financial-summary", response_model=Dict)
async def get_financial_summary(
        start_date: Optional[datetime] = Query(
            None,
            description="Start date for the report period (YYYY-MM-DD)"
        ),
        end_date: Optional[datetime] = Query(
            None,
            description="End date for the report period (YYYY-MM-DD)"
        ),
        service: ReportService = Depends(get_report_service)
):
    """
    Generate a financial summary report.

    Returns:
    - Period information
    - Invoice statistics
        - Total count and amount
        - Breakdown by status
    - Payment statistics
        - Total count and amount
        - Breakdown by payment method
    """
    try:
        if end_date and start_date and end_date < start_date:
            raise HTTPException(
                status_code=400,
                detail="End date cannot be earlier than start date"
            )

        summary = await service.generate_financial_summary(
            start_date=start_date,
            end_date=end_date
        )
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate financial summary: {str(e)}"
        )


@router.get("/reports/clients/{client_id}/dashboard", response_model=Dict)
async def get_client_dashboard(
        client_id: str = Path(..., description="ID of the client"),
        period: Optional[int] = Query(
            30,
            description="Period in days to analyze",
            ge=1,
            le=365
        ),
        service: ReportService = Depends(get_report_service)
):
    """
    Generate a client dashboard with key metrics.

    Returns:
    - Recent activity
    - Payment trends
    - Outstanding invoices
    - Key performance indicators
    """
    # Note: This would require adding a new method to ReportService
    raise HTTPException(
        status_code=501,
        detail="This endpoint is not yet implemented"
    )


@router.get("/reports/stock/analysis", response_model=Dict)
async def get_stock_analysis(
        category_id: Optional[str] = Query(None, description="Filter by category"),
        supplier_id: Optional[str] = Query(None, description="Filter by supplier"),
        service: ReportService = Depends(get_report_service)
):
    """
    Generate a stock analysis report.

    Returns:
    - Stock value by category
    - Low stock alerts
    - Expiration alerts
    - Stock turnover metrics
    """
    # Note: This would require adding a new method to ReportService
    raise HTTPException(
        status_code=501,
        detail="This endpoint is not yet implemented"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(router, host="0.0.0.0", port=8000)
