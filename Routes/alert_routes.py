from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel

from Services.alert_service import AlertService

router = APIRouter(tags=["alerts"])
alert_service = AlertService()

class AlertCreate(BaseModel):
    message: str
    level: str = "info"
    category: Optional[str] = None

class AlertResponse(BaseModel):
    message: str
    level: str
    category: Optional[str]
    timestamp: datetime
    read: bool

@router.post("/alerts", response_model=AlertResponse)
async def create_alert(alert: AlertCreate):
    """
    Create a new alert
    """
    return alert_service.add_alert(
        message=alert.message,
        level=alert.level,
        category=alert.category
    )

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
        level: Optional[str] = Query(None, description="Filter by alert level (info, warning, error)"),
        category: Optional[str] = Query(None, description="Filter by alert category"),
        include_read: bool = Query(False, description="Include read alerts in response")
):
    """
    Get alerts with optional filters
    """
    return alert_service.get_alerts(level, category, include_read)

@router.get("/alerts/categories")
async def get_alert_categories():
    """
    Get all unique alert categories with their unread counts
    """
    alerts = alert_service.get_alerts(include_read=True)
    categories: Dict[str, int] = {}

    for alert in alerts:
        category = alert["category"] or "uncategorized"
        if not alert["read"]:
            categories[category] = categories.get(category, 0) + 1

    return categories

@router.get("/alerts/unread/count")
async def get_unread_count(
        category: Optional[str] = Query(None, description="Get unread count for specific category")
):
    """
    Get count of unread alerts
    """
    return {
        "count": alert_service.get_unread_count(category),
        "category": category or "all"
    }

@router.post("/alerts/{timestamp}/read")
async def mark_alert_read(timestamp: str):
    """
    Mark specific alert as read
    """
    try:
        dt = datetime.fromisoformat(timestamp)
        alert_service.mark_as_read(dt)
        return {"message": "Alert marked as read", "timestamp": timestamp}
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS.mmmmmm)"
        )

@router.post("/alerts/mark-all-read")
async def mark_all_read(
        category: Optional[str] = Query(None, description="Mark all alerts in specific category as read")
):
    """
    Mark all alerts as read
    """
    alert_service.mark_all_as_read(category)
    return {
        "message": f"All alerts marked as read",
        "category": category or "all"
    }

@router.delete("/alerts")
async def clear_alerts(
        category: Optional[str] = Query(None, description="Clear alerts in specific category")
):
    """
    Clear alerts
    """
    alert_service.clear_alerts(category)
    return {
        "message": "Alerts cleared",
        "category": category or "all"
    }

@router.get("/alerts/summary")
async def get_alerts_summary():
    """
    Get summary of alerts by level and category
    """
    alerts = alert_service.get_alerts(include_read=True)
    summary = {
        "total": len(alerts),
        "unread": alert_service.get_unread_count(),
        "by_level": {},
        "by_category": {}
    }

    for alert in alerts:
        # Count by level
        level = alert["level"]
        if level not in summary["by_level"]:
            summary["by_level"][level] = {"total": 0, "unread": 0}
        summary["by_level"][level]["total"] += 1
        if not alert["read"]:
            summary["by_level"][level]["unread"] += 1

        # Count by category
        category = alert["category"] or "uncategorized"
        if category not in summary["by_category"]:
            summary["by_category"][category] = {"total": 0, "unread": 0}
        summary["by_category"][category]["total"] += 1
        if not alert["read"]:
            summary["by_category"][category]["unread"] += 1

    return summary
