from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime
import json

from traitementFinal import EnhancedInvoiceProcessor, DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize processor
processor = EnhancedInvoiceProcessor()

@router.post(
    "/process-invoice/",  # Exact match with frontend URL
    summary="Process Invoice Files",
    description="Upload and process invoice files with enhanced validation and error handling"
)
async def process_invoice_endpoint(files: List[UploadFile] = File(...)):
    """Process invoice files with enhanced validation and error handling."""
    try:
        processor = EnhancedInvoiceProcessor()
        results = await processor.process_files(files)
        return {
            "status": "success",
            "processed": len(files),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error processing invoices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing invoices: {str(e)}"
        )

@router.get(
    "/search-invoices/",  # Exact match with frontend URL
    summary="Search Invoices",
    description="Search invoices with various filters"
)
async def search_invoices(
    invoice_number: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    status: Optional[str] = None
):
    """Search invoices with various filters."""
    try:
        with DatabaseManager().get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM invoices WHERE 1=1"
            params = []

            if invoice_number:
                query += " AND invoice_number = ?"
                params.append(invoice_number)

            if date_from:
                query += " AND date >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date <= ?"
                params.append(date_to)

            if min_amount:
                query += " AND total >= ?"
                params.append(min_amount)

            if max_amount:
                query += " AND total <= ?"
                params.append(max_amount)

            if status:
                query += " AND status = ?"
                params.append(status)

            logger.info(f"Search Query: {query}")
            logger.info(f"Search Params: {params}")

            cursor.execute(query, params)
            results = cursor.fetchall()

            columns = [description[0] for description in cursor.description]
            invoices = []

            for row in results:
                invoice = dict(zip(columns, row))
                invoice['items'] = json.loads(invoice['items']) if invoice['items'] else []
                invoices.append(invoice)

            return {
                "invoices": invoices,
                "count": len(invoices)
            }

    except Exception as e:
        logger.error(f"Error searching invoices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching invoices: {str(e)}"
        )

@router.get(
    "/generate_bilan/",  # Exact match with frontend URL
    summary="Generate Financial Report",
    description="Generate comprehensive financial report for invoices within a date range"
)
async def generate_bilan(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Generate financial report for invoices."""
    try:
        with DatabaseManager().get_connection() as conn:
            cursor = conn.cursor()

            # Query for valid invoices statistics
            query = """
            SELECT 
                COUNT(*) as total_invoices,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_invoices,
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_invoices,
                SUM(total) as total_amount,
                SUM(subtotal) as total_subtotal,
                SUM(tax) as total_tax,
                SUM(discount) as total_discount,
                MIN(total) as min_amount,
                MAX(total) as max_amount,
                AVG(total) as avg_amount
            FROM invoices
            WHERE 1=1
            """
            params = []

            if date_from:
                query += " AND date >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date <= ?"
                params.append(date_to)

            cursor.execute(query, params)
            result = cursor.fetchone()

            # Query for invalid invoices statistics
            invalid_query = """
            SELECT COUNT(*) as total_invalid,
                   COUNT(DISTINCT error_message) as unique_errors
            FROM invalid_invoices
            WHERE 1=1
            """
            if date_from:
                invalid_query += " AND date >= ?"
            if date_to:
                invalid_query += " AND date <= ?"

            cursor.execute(invalid_query, params)
            invalid_result = cursor.fetchone()

            # Query for common errors
            error_query = """
            SELECT error_message, COUNT(*) as count
            FROM invalid_invoices
            WHERE 1=1
            """
            if date_from:
                error_query += " AND date >= ?"
            if date_to:
                error_query += " AND date <= ?"
            error_query += " GROUP BY error_message ORDER BY count DESC LIMIT 5"

            cursor.execute(error_query, params)
            common_errors = cursor.fetchall()

            return {
                "période": {
                    "du": date_from if date_from else "début",
                    "au": date_to if date_to else "aujourd'hui"
                },
                "statistiques_factures": {
                    "total_factures": result[0],
                    "factures_en_attente": result[1],
                    "factures_payées": result[2],
                    "montant_total": round(result[3], 2) if result[3] else 0,
                    "total_ht": round(result[4], 2) if result[4] else 0,
                    "total_tva": round(result[5], 2) if result[5] else 0,
                    "total_remises": round(result[6], 2) if result[6] else 0,
                    "montant_minimum": round(result[7], 2) if result[7] else 0,
                    "montant_maximum": round(result[8], 2) if result[8] else 0,
                    "montant_moyen": round(result[9], 2) if result[9] else 0
                },
                "statistiques_erreurs": {
                    "total_factures_invalides": invalid_result[0],
                    "types_erreurs_uniques": invalid_result[1],
                    "erreurs_fréquentes": [
                        {"message": error[0], "occurrences": error[1]}
                        for error in common_errors
                    ]
                }
            }

    except Exception as e:
        logger.error(f"Error generating bilan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating bilan: {str(e)}"
        )
