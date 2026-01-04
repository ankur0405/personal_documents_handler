import os
from src.config.loader import config
from src.common.db import DatabaseManager
from src.common.utils import get_logger

logger = get_logger(__name__)


def remove_orphans_and_duplicates():
    """
    Synchronizes the database with the physical disk by removing records
    of files that have been deleted or moved.
    """
    print("--- 🧹 AGGRESSIVE DATABASE RECONCILIATION ---")

    # Initialize DB using centralized config
    db_manager = DatabaseManager(db_path=config.db_path)
    table = db_manager.initialize_table()
    df = table.to_pandas()

    if df.empty:
        print("⚠️ Database is empty. Nothing to clean.")
        return

    total_start = len(df)

    # 1. ORPHAN DETECTION: Check if file still exists on disk
    # We create a mask for rows where the file_path is no longer valid
    df['exists'] = df['file_path'].apply(lambda x: os.path.exists(x))
    df_orphans = df[df['exists'] == False]

    # 2. DUPLICATE DETECTION: Check for identical content hashes
    # Keep the first occurrence of each unique ID
    df_valid = df[df['exists'] == True].drop_duplicates(subset=['id'], keep='first')

    orphans_count = len(df_orphans)
    duplicates_count = (total_start - orphans_count) - len(df_valid)

    if orphans_count == 0 and duplicates_count == 0:
        print("✅ Database is perfectly synchronized with disk.")
        return

    print(f"🔥 Found {orphans_count} Orphaned records (Files deleted from disk).")
    print(f"🔥 Found {duplicates_count} Duplicate records (Identical content hashes).")

    # 3. RE-INSERTION (The Nuclear Reset)
    # We wipe and re-insert to ensure index integrity
    try:
        table.delete("true")  # Clear all records
        # Remove the temporary 'exists' column before saving
        final_df = df_valid.drop(columns=['exists'])
        table.add(final_df.to_dict('records'))
        print(f"✅ Success! Database now contains {len(final_df)} verified records.")
        logger.info(f"Cleanup complete: Removed {orphans_count} orphans and {duplicates_count} duplicates.")

    except Exception as e:
        print(f"❌ Critical Error during database reconciliation: {e}")
        logger.error(f"Database cleanup failed: {e}")

if __name__ == "__main__":
    remove_orphans_and_duplicates()
