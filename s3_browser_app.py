#!/usr/bin/env python3
"""
S3-compatible storage browser using Qt6
Modular version with separated UI components and backend
"""

import sys
import os
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QProgressBar, QSplitter, QStatusBar, QMessageBox, QFileDialog,
    QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtSvg import QSvgRenderer

# Import backend and UI components
from backend import S3Worker, DownloadWorker, UploadWorker, DeleteWorker, FileProcessor
from ui import ConnectionWidget, FileListWidget, DetailsWidget


class S3BrowserMainWindow(QMainWindow):
    """Main window for the S3 browser application"""
    
    def __init__(self):
        super().__init__()
        
        # State
        self.current_files: List[Dict[str, Any]] = []
        self.s3_worker: Optional[S3Worker] = None
        self.saved_navigation_state: Optional[Dict[str, Any]] = None
        
        self.init_ui()
        self.setup_status_bar()
        self.connect_signals()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("S3 Bucket Diver")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create and add components
        self._create_components(main_layout)
    
    def _create_components(self, main_layout: QVBoxLayout):
        """Create and arrange UI components"""
        # Connection widget with fixed height
        self.connection_widget = ConnectionWidget()
        self.connection_widget.setMaximumHeight(120)  # Fixed height
        from PyQt6.QtWidgets import QSizePolicy
        self.connection_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        main_layout.addWidget(self.connection_widget)
        
        # Progress bar (initially hidden) with fixed height
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(25)  # Fixed height for progress bar
        main_layout.addWidget(self.progress_bar)
        
        # Splitter for file list and details (this will expand to fill remaining space)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # File list widget
        self.file_list_widget = FileListWidget()
        splitter.addWidget(self.file_list_widget)
        
        # Details widget
        self.details_widget = DetailsWidget()
        splitter.addWidget(self.details_widget)
        
        # Set splitter proportions
        splitter.setSizes([600, 400])
        
        # Add splitter with stretch factor so it expands to fill remaining space
        main_layout.addWidget(splitter, 1)  # stretch factor = 1
    
    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready to connect to S3-compatible storage")
    
    def connect_signals(self):
        """Connect signals between components"""
        # Connection widget signals
        self.connection_widget.connection_requested.connect(self.connect_to_s3)
        
        # File list widget signals
        self.file_list_widget.item_double_clicked.connect(self.on_item_double_clicked)
        self.file_list_widget.selection_changed.connect(self.on_selection_changed)
        self.file_list_widget.upload_requested.connect(self.start_upload)
        self.file_list_widget.refresh_requested.connect(self.refresh_file_list)
        
        # Details widget signals
        self.details_widget.download_requested.connect(self.start_download)
        self.details_widget.delete_requested.connect(self.start_delete)
        self.details_widget.copy_url_requested.connect(self.copy_file_url)
        
        # Set up connection data callback for image previews
        self.details_widget.set_connection_data_callback(self._get_connection_data)
    
    def connect_to_s3(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str):
        """Connect to S3 and list files"""
        # Disable UI during connection
        self.connection_widget.set_connect_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.file_list_widget.clear()
        self.details_widget.clear()
        
        # Start worker thread
        self.s3_worker = S3Worker(endpoint_url, access_key, secret_key, bucket_name)
        self.s3_worker.files_loaded.connect(self.on_files_loaded)
        self.s3_worker.error_occurred.connect(self.on_error_occurred)
        self.s3_worker.progress_update.connect(self.on_progress_update)
        self.s3_worker.finished.connect(self.on_worker_finished)
        self.s3_worker.start()
    
    def on_files_loaded(self, files: List[Dict[str, Any]]):
        """Handle successful file loading"""
        self.current_files = files
        self.file_list_widget.set_files(files)
        
        # Restore navigation state if we have one saved
        if self.saved_navigation_state is not None:
            self.file_list_widget.restore_navigation_state(self.saved_navigation_state)
            self.saved_navigation_state = None  # Clear it after use
        
        self.status_bar.showMessage(f"Loaded {len(files)} files successfully")
    
    def on_error_occurred(self, error_message: str):
        """Handle errors from worker threads"""
        QMessageBox.critical(self, "Error", error_message)
        self.status_bar.showMessage("Error occurred")
    
    def on_progress_update(self, message: str):
        """Handle progress updates"""
        self.status_bar.showMessage(message)
    
    def on_worker_finished(self):
        """Handle worker thread completion"""
        self.connection_widget.set_connect_enabled(True)
        self.progress_bar.setVisible(False)
    
    def refresh_file_list(self):
        """Refresh the file list"""
        if self.s3_worker and self.s3_worker.isRunning():
            QMessageBox.information(self, "Please Wait", "A connection is already in progress.")
            return
        
        # Save current navigation state before refreshing
        self.saved_navigation_state = self.file_list_widget.get_current_navigation_state()
        
        # Re-trigger the last successful connection
        self.connection_widget.request_connection()
    
    def on_item_double_clicked(self, item: QListWidgetItem):
        """Handle double-click on list items"""
        item_data = item.data(Qt.ItemDataRole.UserRole)
        
        # Only handle folder navigation if virtual folders are enabled
        if not self.file_list_widget.virtual_dirs_checkbox.isChecked():
            return
        
        # Check if this is a folder
        if item_data.get('is_folder', False):
            # Navigate into the folder using the full path if available
            folder_path = item_data.get('folder_path', item_data['folder_name'])
            self.file_list_widget.navigate_to_folder(folder_path)
    
    def on_selection_changed(self):
        """Handle selection changes in the file list"""
        current_item = self.file_list_widget.get_current_item()
        selected_items = self.file_list_widget.get_selected_items()
        
        self.details_widget.update_selection(current_item, selected_items)
    
    def start_download(self, selected_items: List[QListWidgetItem]):
        """Start downloading selected files"""
        if not selected_items:
            return
        
        # Get connection info from connection widget
        connection_data = self.connection_widget.get_current_profile_data()
        if not all([connection_data['endpoint_url'], connection_data['access_key'], 
                   connection_data['secret_key'], connection_data['bucket_name']]):
            QMessageBox.warning(self, "Missing Connection Info", 
                              "Please connect to S3 first before downloading files.")
            return
        
        # Get download directory
        download_dir = QFileDialog.getExistingDirectory(
            self, "Select Download Directory", 
            QApplication.instance().property("last_download_dir") or os.path.expanduser("~/Downloads")
        )
        
        if not download_dir:
            return
        
        # Remember last download directory
        QApplication.instance().setProperty("last_download_dir", download_dir)
        
        # Prepare files for download - expand folders to individual files
        files_to_download = []
        for item in selected_items:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data.get('is_folder', False):
                # It's a folder, add all files in the folder
                files_to_download.extend(item_data['files'])
            else:
                # It's a regular file
                files_to_download.append(item_data)
        
        # Calculate total size and ask for confirmation if large
        total_size = sum(f['size'] for f in files_to_download)
        if total_size > 100 * 1024 * 1024:  # 100MB
            size_str = FileProcessor.format_size(total_size)
            reply = QMessageBox.question(
                self, "Large Download", 
                f"You're about to download {len(files_to_download)} files ({size_str}). Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Start download
        self._execute_download(files_to_download, download_dir, connection_data)
    
    def _execute_download(self, files_to_download: List[Dict], download_dir: str, connection_data: Dict[str, str]):
        """Execute the download operation"""
        # Disable UI during download
        self.details_widget.set_buttons_enabled(False)
        self.connection_widget.set_connect_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(files_to_download))
        self.progress_bar.setValue(0)
        
        # Start download worker
        self.download_worker = DownloadWorker(
            connection_data['endpoint_url'],
            connection_data['access_key'],
            connection_data['secret_key'],
            connection_data['bucket_name'],
            files_to_download,
            download_dir
        )
        
        self.download_worker.download_progress.connect(self.on_download_progress)
        self.download_worker.download_complete.connect(self.on_download_complete)
        self.download_worker.all_downloads_complete.connect(self.on_all_downloads_complete)
        self.download_worker.error_occurred.connect(self.on_error_occurred)
        self.download_worker.finished.connect(self.on_download_finished)
        
        self.download_worker.start()
        self.status_bar.showMessage(f"Starting download of {len(files_to_download)} files...")
    
    def on_download_progress(self, filename: str, current: int, total: int):
        """Handle download progress updates"""
        self.progress_bar.setValue(current - 1)  # current is 1-based
        self.status_bar.showMessage(f"Downloading {current}/{total}: {filename}")
    
    def on_download_complete(self, filename: str, success: bool):
        """Handle individual download completion"""
        if success:
            print(f"Downloaded: {filename}")
        else:
            print(f"Failed: {filename}")
    
    def on_all_downloads_complete(self, successful: int, failed: int):
        """Handle completion of all downloads"""
        total = successful + failed
        if failed == 0:
            QMessageBox.information(
                self, "Download Complete", 
                f"Successfully downloaded all {successful} files!"
            )
        else:
            QMessageBox.warning(
                self, "Download Complete with Errors", 
                f"Downloaded {successful}/{total} files successfully.\\n{failed} files failed to download."
            )
    
    def on_download_finished(self):
        """Handle download worker completion"""
        self.details_widget.set_buttons_enabled(True)
        self.connection_widget.set_connect_enabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Download completed")
    
    def start_upload(self, files_to_upload: List[str], s3_prefix: str):
        """Start uploading files"""
        if not files_to_upload:
            return
        
        # Get connection info
        connection_data = self.connection_widget.get_current_profile_data()
        if not all([connection_data['endpoint_url'], connection_data['access_key'], 
                   connection_data['secret_key'], connection_data['bucket_name']]):
            QMessageBox.warning(self, "Missing Connection Info", 
                              "Please connect to S3 first before uploading files.")
            return
        
        # Start upload
        self._execute_upload(files_to_upload, s3_prefix, connection_data)
    
    def _execute_upload(self, files_to_upload: List[str], s3_prefix: str, connection_data: Dict[str, str]):
        """Execute the upload operation"""
        # Disable UI during upload
        self.connection_widget.set_connect_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(files_to_upload))
        self.progress_bar.setValue(0)
        
        # Start upload worker
        self.upload_worker = UploadWorker(
            connection_data['endpoint_url'],
            connection_data['access_key'],
            connection_data['secret_key'],
            connection_data['bucket_name'],
            files_to_upload,
            s3_prefix
        )
        
        self.upload_worker.upload_progress.connect(self.on_upload_progress)
        self.upload_worker.upload_complete.connect(self.on_upload_complete)
        self.upload_worker.all_uploads_complete.connect(self.on_all_uploads_complete)
        self.upload_worker.error_occurred.connect(self.on_error_occurred)
        self.upload_worker.finished.connect(self.on_upload_finished)
        
        self.upload_worker.start()
        
        prefix_text = f" to '{s3_prefix}/'" if s3_prefix else ""
        self.status_bar.showMessage(f"Starting upload of {len(files_to_upload)} files{prefix_text}...")
    
    def on_upload_progress(self, filename: str, current: int, total: int):
        """Handle upload progress updates"""
        self.progress_bar.setValue(current - 1)
        self.status_bar.showMessage(f"Uploading {current}/{total}: {filename}")
    
    def on_upload_complete(self, filename: str, success: bool):
        """Handle individual upload completion"""
        if success:
            print(f"Uploaded: {filename}")
        else:
            print(f"Upload failed: {filename}")
    
    def on_all_uploads_complete(self, successful: int, failed: int):
        """Handle completion of all uploads"""
        total = successful + failed
        if failed == 0:
            QMessageBox.information(
                self, "Upload Complete", 
                f"Successfully uploaded all {successful} files!"
            )
        else:
            QMessageBox.warning(
                self, "Upload Complete with Errors", 
                f"Uploaded {successful}/{total} files successfully.\\n{failed} files failed to upload."
            )
        
        # Save navigation state and refresh file list to show new files
        self.saved_navigation_state = self.file_list_widget.get_current_navigation_state()
        QTimer.singleShot(1000, self.refresh_file_list)  # Delay to allow S3 consistency
    
    def on_upload_finished(self):
        """Handle upload worker completion"""
        self.connection_widget.set_connect_enabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Upload completed")
    
    def start_delete(self, selected_items: List[QListWidgetItem]):
        """Start deleting selected files"""
        if not selected_items:
            return
        
        # Get connection info
        connection_data = self.connection_widget.get_current_profile_data()
        if not all([connection_data['endpoint_url'], connection_data['access_key'], 
                   connection_data['secret_key'], connection_data['bucket_name']]):
            QMessageBox.warning(self, "Missing Connection Info", 
                              "Please connect to S3 first before deleting files.")
            return
        
        # Get files to delete - expand folders to individual files
        files_to_delete = []
        for item in selected_items:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data.get('is_folder', False):
                # It's a folder, add all files in the folder
                for file_info in item_data['files']:
                    files_to_delete.append(file_info['key'])
            else:
                # It's a regular file
                files_to_delete.append(item_data['key'])
        
        # Show warning and get confirmation
        file_list_text = "\\n".join([f"• {key}" for key in files_to_delete[:10]])
        if len(files_to_delete) > 10:
            file_list_text += f"\\n... and {len(files_to_delete) - 10} more files"
        
        reply = QMessageBox.warning(
            self, "⚠️ Delete Files", 
            f"Are you sure you want to permanently delete {len(files_to_delete)} file(s)?\\n\\n"
            f"This action cannot be undone!\\n\\nFiles to delete:\\n{file_list_text}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # Default to No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Start delete operation
        self._execute_delete(files_to_delete, connection_data)
    
    def _execute_delete(self, files_to_delete: List[str], connection_data: Dict[str, str]):
        """Execute the delete operation"""
        # Disable UI during delete
        self.connection_widget.set_connect_enabled(False)
        self.details_widget.set_buttons_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(files_to_delete))
        self.progress_bar.setValue(0)
        
        # Start delete worker
        self.delete_worker = DeleteWorker(
            connection_data['endpoint_url'],
            connection_data['access_key'],
            connection_data['secret_key'],
            connection_data['bucket_name'],
            files_to_delete
        )
        
        self.delete_worker.delete_progress.connect(self.on_delete_progress)
        self.delete_worker.delete_complete.connect(self.on_delete_complete)
        self.delete_worker.all_deletes_complete.connect(self.on_all_deletes_complete)
        self.delete_worker.error_occurred.connect(self.on_error_occurred)
        self.delete_worker.finished.connect(self.on_delete_finished)
        
        self.delete_worker.start()
        self.status_bar.showMessage(f"Starting deletion of {len(files_to_delete)} files...")
    
    def on_delete_progress(self, filename: str, current: int, total: int):
        """Handle delete progress updates"""
        self.progress_bar.setValue(current - 1)
        self.status_bar.showMessage(f"Deleting {current}/{total}: {filename}")
    
    def on_delete_complete(self, filename: str, success: bool):
        """Handle individual delete completion"""
        if success:
            print(f"Deleted: {filename}")
        else:
            print(f"Delete failed: {filename}")
    
    def on_all_deletes_complete(self, successful: int, failed: int):
        """Handle completion of all deletes"""
        total = successful + failed
        if failed == 0:
            QMessageBox.information(
                self, "Delete Complete", 
                f"Successfully deleted all {successful} files!"
            )
        else:
            QMessageBox.warning(
                self, "Delete Complete with Errors", 
                f"Deleted {successful}/{total} files successfully.\\n{failed} files failed to delete."
            )
        
        # Save navigation state and refresh file list to show updated state
        self.saved_navigation_state = self.file_list_widget.get_current_navigation_state()
        QTimer.singleShot(1000, self.refresh_file_list)  # Delay to allow S3 consistency
    
    def on_delete_finished(self):
        """Handle delete worker completion"""
        self.connection_widget.set_connect_enabled(True)
        self.details_widget.set_buttons_enabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Delete operation completed")
    
    def copy_file_url(self, item: QListWidgetItem):
        """Copy the file URL to clipboard"""
        file_info = item.data(Qt.ItemDataRole.UserRole)
        connection_data = self.connection_widget.get_current_profile_data()
        
        # Construct URL (simplified - would need proper URL signing for private buckets)
        endpoint_url = connection_data['endpoint_url']
        bucket_name = connection_data['bucket_name']
        file_key = file_info['key']
        
        if endpoint_url.endswith('/'):
            endpoint_url = endpoint_url[:-1]
            
        url = f"{endpoint_url}/{bucket_name}/{file_key}"
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(url)
        
        self.status_bar.showMessage(f"URL copied to clipboard: {url}")
    
    def _get_connection_data(self) -> Dict[str, str]:
        """Get current connection data for URL generation"""
        return self.connection_widget.get_current_profile_data()


def load_app_icon() -> QIcon:
    """Load the application icon from SVG"""
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.svg")
    
    if os.path.exists(icon_path):
        try:
            # Create QIcon from SVG - simplified approach
            icon = QIcon(icon_path)
            if not icon.isNull():
                return icon
        except Exception as e:
            print(f"Warning: Could not load icon from {icon_path}: {e}")
    
    # Return empty icon if loading fails
    return QIcon()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("S3 Bucket Diver")
    app.setApplicationVersion("2.0.0")
    
    # Set application icon
    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    
    window = S3BrowserMainWindow()
    
    # Also set the window icon
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
