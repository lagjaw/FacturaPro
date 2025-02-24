from datetime import datetime


class AlertService:
    def __init__(self):
        self.alerts = []

    def add_alert(self, message, level="info", category=None):
        """
        Add a new alert
        Args:
            message (str): Alert message
            level (str): Alert level (info, warning, error)
            category (str, optional): Category of alert (stock, payment, invoice, etc)
        """
        alert = {
            "message": message,
            "level": level,
            "category": category,
            "timestamp": datetime.now(),
            "read": False
        }
        self.alerts.append(alert)
        return alert

    def get_alerts(self, level=None, category=None, include_read=False):
        """
        Get alerts, optionally filtered by level and category
        Args:
            level (str, optional): Filter alerts by level
            category (str, optional): Filter alerts by category
            include_read (bool): Include already read alerts
        Returns:
            list: List of alerts
        """
        filtered_alerts = self.alerts

        if not include_read:
            filtered_alerts = [alert for alert in filtered_alerts if not alert["read"]]

        if level:
            filtered_alerts = [alert for alert in filtered_alerts if alert["level"] == level]

        if category:
            filtered_alerts = [alert for alert in filtered_alerts if alert["category"] == category]

        return filtered_alerts

    def mark_as_read(self, timestamp):
        """
        Mark specific alert as read
        Args:
            timestamp: Timestamp of the alert to mark as read
        """
        for alert in self.alerts:
            if alert["timestamp"] == timestamp:
                alert["read"] = True
                break

    def mark_all_as_read(self, category=None):
        """
        Mark all alerts as read, optionally filtered by category
        Args:
            category (str, optional): Category of alerts to mark as read
        """
        for alert in self.alerts:
            if category is None or alert["category"] == category:
                alert["read"] = True

    def clear_alerts(self, category=None):
        """
        Clear alerts, optionally filtered by category
        Args:
            category (str, optional): Category of alerts to clear
        """
        if category:
            self.alerts = [alert for alert in self.alerts if alert["category"] != category]
        else:
            self.alerts = []

    def get_unread_count(self, category=None):
        """
        Get count of unread alerts
        Args:
            category (str, optional): Category to count unread alerts for
        Returns:
            int: Number of unread alerts
        """
        unread = [alert for alert in self.alerts if not alert["read"]]
        if category:
            unread = [alert for alert in unread if alert["category"] == category]
        return len(unread)
