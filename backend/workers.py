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
    page_loaded = pyqtSignal(dict)  # New signal for progressive loading
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    retry_attempt = pyqtSignal(int, int, str)  # current_attempt, max_attempts, error_msg
    max_retries_exceeded = pyqtSignal(int, str)  # total_attempts, final_error
    
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str, verbose: bool = False, max_retries: int = 3, max_pages: int = 10):
        super().__init__()
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.verbose = verbose
        self.max_retries = max_retries
        self.max_pages = max_pages
        self._stop_requested = False
        
    def stop_operation(self):
        """Request the worker to stop its operation"""
        self._stop_requested = True
        
    def run(self):
        attempt = 0
        last_error = None
        
        while attempt < self.max_retries and not self._stop_requested:
            attempt += 1
            
            try:
                if self.verbose:
                    print(f"[VERBOSE] S3Worker thread started (attempt {attempt}/{self.max_retries})")
                    print(f"[VERBOSE] Creating S3 client for endpoint: {self.endpoint_url}")
                
                if attempt == 1:
                    self.progress_update.emit("Connecting to S3...")
                else:
                    self.progress_update.emit(f"Retrying connection... (attempt {attempt}/{self.max_retries})")
                
                s3_client = S3Client(
                    self.endpoint_url, 
                    self.access_key, 
                    self.secret_key, 
                    self.bucket_name,
                    self.verbose
                )
                
                if self.verbose:
                    print(f"[VERBOSE] S3 client created, attempting to list bucket contents progressively...")
                    
                self.progress_update.emit("Listing bucket contents...")
                
                # Use progressive loading
                all_files = []
                
                def on_page_loaded(page_info):
                    if self._stop_requested:
                        return
                        
                    all_files.extend(page_info['files'])
                    
                    # Emit the page for immediate UI update
                    self.page_loaded.emit(page_info)
                    
                    self.progress_update.emit(f"Loaded page {page_info['page_number']} ({page_info['total_files_so_far']} files total)")
                    
                    if self.verbose:
                        print(f"[VERBOSE] Page {page_info['page_number']} loaded: {page_info['files_in_page']} files")
                
                result = s3_client.list_files_progressive(max_pages=self.max_pages, page_callback=on_page_loaded)
                
                if self._stop_requested:
                    return
                
                if self.verbose:
                    print(f"[VERBOSE] Progressive loading completed: {result['pages_processed']} pages, {result['total_files_found']} files")
                    
                self.progress_update.emit(f"Loaded {result['total_files_found']} files ({result['pages_processed']} pages)")
                
                # Still emit the complete list for compatibility
                self.files_loaded.emit(all_files)
                return  # Success - exit the retry loop
                
            except Exception as e:
                last_error = str(e)
                
                if self.verbose:
                    print(f"[VERBOSE] S3Worker attempt {attempt} failed: {last_error}")
                
                if attempt < self.max_retries:
                    # Not the last attempt - emit retry signal
                    self.retry_attempt.emit(attempt, self.max_retries, last_error)
                    
                    if self.verbose:
                        print(f"[VERBOSE] Will retry in 2 seconds... ({attempt}/{self.max_retries})")
                    
                    # Wait 2 seconds before retry (check for stop request every 100ms)
                    for i in range(20):
                        if self._stop_requested:
                            return
                        self.msleep(100)
                else:
                    # Last attempt failed - emit max retries exceeded
                    if self.verbose:
                        print(f"[VERBOSE] All {self.max_retries} connection attempts failed")
                    
                    self.max_retries_exceeded.emit(self.max_retries, last_error)
                    return


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
