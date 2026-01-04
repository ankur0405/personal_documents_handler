import lancedb
import pandas as pd
from src.config.loader import config
from datetime import datetime

def show_dashboard():
    db = lancedb.connect(config.db_path)
    
    if "system_audit_log" not in db.list_tables():
        print("❌ No audit data found. System hasn't processed any files yet.")
        return

    table = db.open_table("system_audit_log")
    df = table.to_pandas()
    
    # 1. Pipeline Summary
    total_events = len(df)
    successes = len(df[df['status'] == 'SUCCESS'])
    failures = len(df[df['status'] == 'FAILED'])
    
    print(f"\n--- 🚀 PDH ENTERPRISE DASHBOARD | {datetime.now().strftime('%Y-%m-%d %H:%M')} ---")
    print(f"📊 Total Tasks Processed: {total_events}")
    print(f"✅ Success Rate: {(successes/total_events)*100:.1f}%")
    print(f"❌ Current Failures in DLQ: {failures}")
    
    # 2. Top Error Breakdown
    if failures > 0:
        print("\n🔎 TOP FAILURE REASONS:")
        error_summary = df[df['status'] == 'FAILED']['error_msg'].value_counts()
        print(error_summary.head(5).to_string())
        
        print("\n📋 PENDING ACTIONS:")
        print(f"👉 To retry {failures} failed tasks, run: python3 scripts/retry_failed_tasks.py")

if __name__ == "__main__":
    show_dashboard()