#!/usr/bin/env python3
"""
Worker threads for S3 operations
Handles background operations without blocking the UI
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Dict, Any
from .s3_operations import S3Client, DownloadManager, UploadManager, DeleteManager


class S3Worker(QThread):
    """Worker thread for S3 file listing operations"""
    
    files_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str):
        super().__init__()
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        
    def run(self):
        try:
            self.progress_update.emit("Connecting to S3...")
            
            s3_client = S3Client(
                self.endpoint_url, 
                self.access_key, 
                self.secret_key, 
                self.bucket_name
            )
            
            self.progress_update.emit("Listing bucket contents...")
            files = s3_client.list_files()
            
            self.progress_update.emit(f"Found {len(files)} objects")
            self.files_loaded.emit(files)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloadWorker(QThread):
    """Worker thread for downloading files from S3"""
    
    download_progress = pyqtSignal(str, int, int)  # filename, current, total
    download_complete = pyqtSignal(str, bool)  # filename, success
    all_downloads_complete = pyqtSignal(int, int)  # successful, failed
    error_occurred = pyqtSignal(str)
    
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, 
                 bucket_name: str, files_to_download: List[Dict], download_dir: str):
        super().__init__()
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.files_to_download = files_to_download
        self.download_dir = download_dir
        
    def run(self):
        try:
            s3_client = S3Client(
                self.endpoint_url, 
                self.access_key, 
                self.secret_key, 
                self.bucket_name
            )
            
            download_manager = DownloadManager(s3_client, self.download_dir)
            
            successful, failed = download_manager.download_files(
                self.files_to_download,
                progress_callback=self.download_progress.emit,
                complete_callback=self.download_complete.emit
            )
            
            self.all_downloads_complete.emit(successful, failed)
            
        except Exception as e:
            self.error_occurred.emit(f"Download error: {str(e)}")


class UploadWorker(QThread):
    """Worker thread for uploading files to S3"""
    
    upload_progress = pyqtSignal(str, int, int)  # filename, current, total
    upload_complete = pyqtSignal(str, bool)  # filename, success
    all_uploads_complete = pyqtSignal(int, int)  # successful, failed
    error_occurred = pyqtSignal(str)
    
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, 
                 bucket_name: str, files_to_upload: List[str], s3_prefix: str = ""):
        super().__init__()
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.files_to_upload = files_to_upload
        self.s3_prefix = s3_prefix
        
    def run(self):
        try:
            s3_client = S3Client(
                self.endpoint_url, 
                self.access_key, 
                self.secret_key, 
                self.bucket_name
            )
            
            upload_manager = UploadManager(s3_client, self.s3_prefix)
            
            successful, failed = upload_manager.upload_files(
                self.files_to_upload,
                progress_callback=self.upload_progress.emit,
                complete_callback=self.upload_complete.emit
            )
            
            self.all_uploads_complete.emit(successful, failed)
            
        except Exception as e:
            self.error_occurred.emit(f"Upload error: {str(e)}")


class DeleteWorker(QThread):
    """Worker thread for deleting files from S3"""
    
    delete_progress = pyqtSignal(str, int, int)  # filename, current, total
    delete_complete = pyqtSignal(str, bool)  # filename, success
    all_deletes_complete = pyqtSignal(int, int)  # successful, failed
    error_occurred = pyqtSignal(str)
    
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, 
                 bucket_name: str, files_to_delete: List[str]):
        super().__init__()
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.files_to_delete = files_to_delete
        
    def run(self):
        try:
            s3_client = S3Client(
                self.endpoint_url, 
                self.access_key, 
                self.secret_key, 
                self.bucket_name
            )
            
            delete_manager = DeleteManager(s3_client)
            
            successful, failed = delete_manager.delete_files(
                self.files_to_delete,
                progress_callback=self.delete_progress.emit,
                complete_callback=self.delete_complete.emit
            )
            
            self.all_deletes_complete.emit(successful, failed)
            
        except Exception as e:
            self.error_occurred.emit(f"Delete error: {str(e)}")
