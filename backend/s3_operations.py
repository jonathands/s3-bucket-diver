#!/usr/bin/env python3
"""
S3 backend operations module
Handles all S3-related API calls and data processing
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
from botocore.client import Config
from typing import List, Dict, Any, Optional
import os


class S3Client:
    """S3 client wrapper for handling S3-compatible storage operations"""
    
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self._client = None
    
    def _get_client(self):
        """Get or create S3 client"""
        if not self._client:
            session = boto3.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
            
            self._client = session.client(
                's3',
                endpoint_url=self.endpoint_url,
                config=Config(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'path'
                    }
                )
            )
        return self._client
    
    def list_files(self) -> List[Dict[str, Any]]:
        """List all files in the bucket"""
        try:
            client = self._get_client()
            paginator = client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket_name)
            
            files = []
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        file_info = {
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].strftime('%Y-%m-%d %H:%M:%S'),
                            'etag': obj['ETag'].strip('"'),
                            'storage_class': obj.get('StorageClass', 'STANDARD')
                        }
                        files.append(file_info)
            
            return files
            
        except NoCredentialsError:
            raise Exception("Invalid credentials. Please check your access key and secret key.")
        except EndpointConnectionError:
            raise Exception("Cannot connect to the endpoint. Please check the URL.")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise Exception(f"Bucket '{self.bucket_name}' does not exist.")
            elif error_code == 'AccessDenied':
                raise Exception("Access denied. Please check your credentials and permissions.")
            else:
                raise Exception(f"AWS Error: {e.response['Error']['Message']}")
    
    def download_file(self, file_key: str, local_path: str) -> None:
        """Download a single file"""
        client = self._get_client()
        client.download_file(self.bucket_name, file_key, local_path)
    
    def upload_file(self, local_path: str, s3_key: str) -> None:
        """Upload a single file"""
        client = self._get_client()
        client.upload_file(local_path, self.bucket_name, s3_key)
    
    def delete_file(self, file_key: str) -> None:
        """Delete a single file"""
        client = self._get_client()
        client.delete_object(Bucket=self.bucket_name, Key=file_key)


class FileProcessor:
    """Handles file processing and virtual directory operations"""
    
    @staticmethod
    def format_size(size: int) -> str:
        """Format file size in human readable format"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    
    @staticmethod
    def organize_files_by_folders(files: List[Dict[str, Any]]) -> tuple:
        """Organize files into virtual folder structure"""
        folders = {}
        root_files = []
        
        for file_info in files:
            key = file_info['key']
            if '/' in key:
                # File is in a folder
                folder = key.split('/')[0]
                if folder not in folders:
                    folders[folder] = []
                folders[folder].append(file_info)
            else:
                # File is in root
                root_files.append(file_info)
        
        return folders, root_files
    
    @staticmethod
    def get_folder_contents(files: List[Dict[str, Any]], folder_path: str) -> tuple:
        """Get contents of a specific folder path"""
        folder_prefix = f"{folder_path}/"
        matching_files = []
        
        for file_info in files:
            key = file_info['key']
            if key.startswith(folder_prefix):
                relative_path = key[len(folder_prefix):]
                if relative_path:  # Make sure it's not empty
                    matching_files.append((file_info, relative_path))
        
        # Group files by immediate subdirectories and direct files
        subdirectories = {}
        direct_files = []
        
        for file_info, relative_path in matching_files:
            if '/' in relative_path:
                # This file is in a subdirectory
                subdirectory = relative_path.split('/')[0]
                if subdirectory not in subdirectories:
                    subdirectories[subdirectory] = []
                subdirectories[subdirectory].append(file_info)
            else:
                # This file is directly in the current folder
                direct_files.append((file_info, relative_path))
        
        return subdirectories, direct_files


class DownloadManager:
    """Handles downloading multiple files with progress tracking"""
    
    def __init__(self, s3_client: S3Client, download_dir: str):
        self.s3_client = s3_client
        self.download_dir = download_dir
    
    def download_files(self, files_to_download: List[Dict], progress_callback=None, complete_callback=None):
        """Download multiple files with progress reporting"""
        successful_downloads = 0
        failed_downloads = 0
        
        for i, file_info in enumerate(files_to_download, 1):
            file_key = file_info['key']
            # Clean filename for local storage
            filename = os.path.basename(file_key) if os.path.basename(file_key) else file_key.replace('/', '_')
            local_path = os.path.join(self.download_dir, filename)
            
            # Handle duplicate filenames
            counter = 1
            original_path = local_path
            while os.path.exists(local_path):
                name, ext = os.path.splitext(original_path)
                local_path = f"{name}_{counter}{ext}"
                counter += 1
            
            try:
                if progress_callback:
                    progress_callback(filename, i, len(files_to_download))
                
                self.s3_client.download_file(file_key, local_path)
                
                if complete_callback:
                    complete_callback(filename, True)
                successful_downloads += 1
                
            except Exception as e:
                if complete_callback:
                    complete_callback(f"{filename} (Error: {str(e)})", False)
                failed_downloads += 1
        
        return successful_downloads, failed_downloads


class UploadManager:
    """Handles uploading multiple files with progress tracking"""
    
    def __init__(self, s3_client: S3Client, s3_prefix: str = ""):
        self.s3_client = s3_client
        self.s3_prefix = s3_prefix
    
    def upload_files(self, files_to_upload: List[str], progress_callback=None, complete_callback=None):
        """Upload multiple files with progress reporting"""
        successful_uploads = 0
        failed_uploads = 0
        
        for i, file_path in enumerate(files_to_upload, 1):
            filename = os.path.basename(file_path)
            # Create S3 key with prefix if provided
            s3_key = f"{self.s3_prefix}/{filename}" if self.s3_prefix else filename
            
            try:
                if progress_callback:
                    progress_callback(filename, i, len(files_to_upload))
                
                self.s3_client.upload_file(file_path, s3_key)
                
                if complete_callback:
                    complete_callback(filename, True)
                successful_uploads += 1
                
            except Exception as e:
                if complete_callback:
                    complete_callback(f"{filename} (Error: {str(e)})", False)
                failed_uploads += 1
        
        return successful_uploads, failed_uploads


class DeleteManager:
    """Handles deleting multiple files with progress tracking"""
    
    def __init__(self, s3_client: S3Client):
        self.s3_client = s3_client
    
    def delete_files(self, files_to_delete: List[str], progress_callback=None, complete_callback=None):
        """Delete multiple files with progress reporting"""
        successful_deletes = 0
        failed_deletes = 0
        
        for i, file_key in enumerate(files_to_delete, 1):
            filename = os.path.basename(file_key) if os.path.basename(file_key) else file_key
            
            try:
                if progress_callback:
                    progress_callback(filename, i, len(files_to_delete))
                
                self.s3_client.delete_file(file_key)
                
                if complete_callback:
                    complete_callback(filename, True)
                successful_deletes += 1
                
            except Exception as e:
                if complete_callback:
                    complete_callback(f"{filename} (Error: {str(e)})", False)
                failed_deletes += 1
        
        return successful_deletes, failed_deletes
