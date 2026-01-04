import lancedb
import pandas as pd
from datetime import datetime
from src.config.loader import config
from src.common.utils import get_logger

logger = get_logger(__name__)

class EnterpriseMonitor:
    def __init__(self):
        # Connect to the same DB used for document intelligence
        self.db = lancedb.connect(config.db_path)
        self.table_name = "system_audit_log"
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Ensures the audit table is ready for 100-user traffic."""
        if self.table_name not in self.db.list_tables():
            # Initial schema for the audit log
            initial_data = [{
                "task_id": "system_init",
                "filename": "system",
                "status": "READY",
                "error_code": "0",
                "error_msg": "Audit System Online",
                "node_type": "monitor",
                "timestamp": datetime.now().isoformat()
            }]
            self.db.create_table(self.table_name, data=initial_data)
            logger.info(f"📊 Audit table '{self.table_name}' created.")

    def log_event(self, task, status, node_type, error_msg=""):
        """Records a processing event for the Action Dashboard."""
        table = self.db.open_table(self.table_name)
        event = [{
            "task_id": task.get("id", "unknown"),
            "filename": task.get("filename", "unknown"),
            "status": status,  # SUCCESS, FAILED, or RETRY
            "error_code": "500" if status == "FAILED" else "0",
            "error_msg": str(error_msg),
            "node_type": node_type, # enricher or sink
            "timestamp": datetime.now().isoformat()
        }]
        table.add(event)