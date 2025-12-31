import os

class StorageProvider:
    """
    Abstracts the File System.
    Today: Local Disk.
    Tomorrow: S3, Azure Blob, Google Drive.
    """
    
    @staticmethod
    def exists(path):
        """Checks if a file exists (locally or in cloud)"""
        return os.path.exists(path)
    
    @staticmethod
    def get_last_modified(path):
        """Gets the timestamp of the file"""
        return os.path.getmtime(path)
    
    @staticmethod
    def get_file_path(path):
        """
        Returns a local path that Python can open.
        
        ON LOCAL: It just returns the path you gave it.
        ON S3 (Future): It would download 's3://bucket/tax.pdf' to a temp folder 
                        like '/tmp/tax.pdf' and return that temp path.
        """
        return path