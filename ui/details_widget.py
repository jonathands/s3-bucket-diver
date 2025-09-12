#!/usr/bin/env python3
"""
Details widget for S3 browser
Displays file/folder details and action buttons
"""

from typing import List, Dict, Any, Optional
import os
import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidgetItem, QApplication, QScrollArea, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QPixmap, QMovie

from backend import FileProcessor


class BucketStatisticsWorker(QThread):
    """Worker thread for calculating bucket statistics"""
    
    statistics_calculated = pyqtSignal(str)  # formatted_statistics_text
    progress_update = pyqtSignal(str)  # progress_message
    
    def __init__(self, all_files: List[Dict[str, Any]]):
        super().__init__()
        self.all_files = all_files
        
    def run(self):
        """Calculate simple bucket statistics in background thread"""
        try:
            import time
            import datetime
            start_time = time.time()
            print(f"[STATS] Starting simple statistics calculation...")
            
            self.progress_update.emit("Calculating basic statistics...")
            
            if not self.all_files:
                self.statistics_calculated.emit("No files loaded yet...")
                return
            
            total_files = len(self.all_files)
            print(f"[STATS] Total files to process: {total_files:,}")
            
            # Simple calculations - just total size and last activity
            total_size = 0
            latest_date = ""
            
            for file_info in self.all_files:
                total_size += file_info.get('size', 0)
                
                # Track latest modification date
                last_modified = file_info.get('last_modified', '')
                if last_modified and (not latest_date or last_modified > latest_date):
                    latest_date = last_modified
            
            # Format simple statistics
            stats_text = f"""📊 BUCKET STATISTICS
            
📁 Basic Summary:
   Total Files: {total_files:,}
   Total Size: {FileProcessor.format_size(total_size)}
   Last Activity: {latest_date if latest_date else 'Unknown'}

🕐 Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            total_time = time.time() - start_time
            print(f"[STATS] Simple statistics completed in {total_time:.2f}s for {total_files:,} files")
            
            self.statistics_calculated.emit(stats_text)
            
        except Exception as e:
            print(f"[STATS] ERROR during statistics calculation: {str(e)}")
            import traceback
            traceback.print_exc()
            self.statistics_calculated.emit(f"Error calculating statistics: {str(e)}")


class ImagePreviewWorker(QThread):
    """Worker thread for downloading and loading image previews"""
    
    image_loaded = pyqtSignal(QPixmap)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, url: str, max_size: int = 2 * 1024 * 1024):  # 2MB limit
        super().__init__()
        self.url = url
        self.max_size = max_size
    
    def run(self):
        try:
            # Download image data with size limit
            response = requests.get(self.url, stream=True, timeout=10)
            response.raise_for_status()
            
            # Check content length
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_size:
                self.error_occurred.emit("Image too large for preview")
                return
            
            # Download data
            data = b''
            for chunk in response.iter_content(chunk_size=8192):
                data += chunk
                if len(data) > self.max_size:
                    self.error_occurred.emit("Image too large for preview")
                    return
            
            # Create pixmap from data
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                # Scale down if too large
                if pixmap.width() > 300 or pixmap.height() > 300:
                    pixmap = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.image_loaded.emit(pixmap)
            else:
                self.error_occurred.emit("Failed to load image data")
                
        except Exception as e:
            self.error_occurred.emit(f"Error loading image: {str(e)}")


class DetailsWidget(QWidget):
    """Widget for displaying file details and action buttons"""
    
    # Signals
    download_requested = pyqtSignal(list)  # selected_items
    delete_requested = pyqtSignal(list)    # selected_items
    copy_url_requested = pyqtSignal(QListWidgetItem)  # current_item
    
    def __init__(self):
        super().__init__()
        self.current_item: Optional[QListWidgetItem] = None
        self.selected_items: List[QListWidgetItem] = []
        self.image_worker: Optional[ImagePreviewWorker] = None
        self.stats_worker: Optional[BucketStatisticsWorker] = None
        self.connection_data_callback = None  # Will be set by main window
        self.all_files: List[Dict[str, Any]] = []  # Store all files for statistics
        self.statistics_calculated = False  # Track if statistics have been calculated
        self.statistics_tab_index = 1  # Index of the statistics tab
        self.init_ui()
    
    def init_ui(self):
        """Initialize the details widget UI with tab interface"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_widget)
        
        # Create File Details tab
        self.file_details_tab = self._create_file_details_tab()
        self.tab_widget.addTab(self.file_details_tab, "File Details")
        
        # Create Bucket Statistics tab
        self.bucket_stats_tab = self._create_bucket_statistics_tab()
        self.tab_widget.addTab(self.bucket_stats_tab, "Bucket Statistics")
        
        # Action buttons at the bottom (outside of tabs)
        button_layout = self._create_action_buttons()
        layout.addLayout(button_layout)
    
    def _create_file_details_tab(self) -> QWidget:
        """Create the File Details tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        layout.addWidget(self.details_text)
        
        # Image preview section
        self.image_preview_label = QLabel("Image Preview:")
        self.image_preview_label.setVisible(False)
        layout.addWidget(self.image_preview_label)
        
        # Scrollable image container
        self.image_scroll_area = QScrollArea()
        self.image_scroll_area.setMaximumHeight(400)
        self.image_scroll_area.setWidgetResizable(True)
        self.image_scroll_area.setVisible(False)
        
        self.image_display = QLabel()
        self.image_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_display.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.image_display.setText("Loading image...")
        self.image_scroll_area.setWidget(self.image_display)
        
        layout.addWidget(self.image_scroll_area)
        layout.addStretch()
        
        return tab
    
    def _create_bucket_statistics_tab(self) -> QWidget:
        """Create the Bucket Statistics tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Progress label
        self.stats_progress_label = QLabel("")
        controls_layout.addWidget(self.stats_progress_label)
        
        controls_layout.addStretch()
        
        # Reload button
        self.reload_stats_button = QPushButton("🔄 Reload Statistics")
        self.reload_stats_button.setEnabled(False)  # Disabled initially
        self.reload_stats_button.clicked.connect(self._reload_statistics)
        self.reload_stats_button.setMaximumWidth(150)
        controls_layout.addWidget(self.reload_stats_button)
        
        layout.addLayout(controls_layout)
        
        # Statistics text
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)
        
        # Initial message
        self.stats_text.setText("Connect to an S3 bucket to view statistics...")
        
        return tab
    
    def _create_action_buttons(self) -> QHBoxLayout:
        """Create the action buttons layout"""
        button_layout = QHBoxLayout()
        
        self.download_button = QPushButton("Download")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self._handle_download)
        button_layout.addWidget(self.download_button)
        
        self.copy_url_button = QPushButton("Copy URL")
        self.copy_url_button.setEnabled(False)
        self.copy_url_button.clicked.connect(self._handle_copy_url)
        button_layout.addWidget(self.copy_url_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self._handle_delete)
        self.delete_button.setStyleSheet("QPushButton { background-color: #ff6b6b; color: white; }")
        button_layout.addWidget(self.delete_button)
        
        button_layout.addStretch()
        return button_layout
    
    def update_selection(self, current_item: Optional[QListWidgetItem], selected_items: List[QListWidgetItem]):
        """Update the widget with new selection"""
        self.current_item = current_item
        self.selected_items = selected_items
        
        self._update_details_display()
        self._update_button_states()
    
    def _update_details_display(self):
        """Update the details text display"""
        if not self.selected_items:
            self.details_text.clear()
            return
        
        if len(self.selected_items) == 1:
            self._display_single_item_details(self.selected_items[0])
        else:
            self._display_multiple_items_summary()
    
    def _display_single_item_details(self, item: QListWidgetItem):
        """Display details for a single selected item"""
        item_data = item.data(Qt.ItemDataRole.UserRole)
        
        if item_data.get('is_folder', False):
            # Display folder details
            folder_info = item_data
            details = f"""Folder: {folder_info['folder_name']}/
Files: {folder_info['file_count']}
Total Size: {FileProcessor.format_size(folder_info['total_size'])}

Contents:
"""
            
            # Show first few files in the folder
            for i, file_info in enumerate(folder_info['files'][:5]):
                details += f"• {file_info['key']}\n"
            if len(folder_info['files']) > 5:
                details += f"... and {len(folder_info['files']) - 5} more files"
            
        else:
            # Display file details
            file_info = item_data
            details = f"""File: {file_info['key']}
Size: {file_info['size']:,} bytes
Last Modified: {file_info['last_modified']}
ETag: {file_info['etag']}
Storage Class: {file_info['storage_class']}"""
        
        self.details_text.setText(details)
        
        # Check if it's an image file and show preview (only for single files)
        if not item_data.get('is_folder', False):
            self._update_image_preview(item_data)
        else:
            self._hide_image_preview()
    
    def _display_multiple_items_summary(self):
        """Display summary for multiple selected items"""
        total_size = 0
        file_count = 0
        folder_count = 0
        
        for item in self.selected_items:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data.get('is_folder', False):
                # It's a folder
                total_size += item_data['total_size']
                file_count += item_data['file_count']
                folder_count += 1
            else:
                # It's a file
                total_size += item_data['size']
                file_count += 1
        
        # Format total size
        size_str = FileProcessor.format_size(total_size)
        
        # Create details text
        if folder_count > 0:
            details = f"""Selected Items: {len(self.selected_items)} ({folder_count} folders, {len(self.selected_items) - folder_count} files)
Total Files: {file_count}
Total Size: {size_str}

Items:
"""
        else:
            details = f"""Selected Files: {len(self.selected_items)}
Total Size: {size_str}

Files:
"""
        
        # Show first 10 items
        for item in self.selected_items[:10]:
            item_data = item.data(Qt.ItemDataRole.UserRole)
            if item_data.get('is_folder', False):
                details += f"📁 {item_data['folder_name']}/\n"
            else:
                details += f"📄 {item_data['key']}\n"
        if len(self.selected_items) > 10:
            details += f"... and {len(self.selected_items) - 10} more items"
            
        self.details_text.setText(details)
        
        # Hide image preview for multiple selections
        self._hide_image_preview()
    
    def _update_button_states(self):
        """Update the state and text of action buttons"""
        if not self.selected_items:
            self.download_button.setEnabled(False)
            self.copy_url_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        
        if len(self.selected_items) == 1:
            # Single selection
            item_data = self.selected_items[0].data(Qt.ItemDataRole.UserRole)
            is_folder = item_data.get('is_folder', False)
            
            self.download_button.setEnabled(True)
            self.copy_url_button.setEnabled(not is_folder)  # Only files have URLs
            self.delete_button.setEnabled(True)
            
            # Update button text
            self.download_button.setText("Download")
            self.delete_button.setText("Delete")
            
        else:
            # Multiple selection
            has_folders = any(item.data(Qt.ItemDataRole.UserRole).get('is_folder', False) 
                            for item in self.selected_items)
            
            self.download_button.setEnabled(True)
            self.copy_url_button.setEnabled(not has_folders)  # Mixed selection can't copy URLs
            self.delete_button.setEnabled(True)
            
            # Update button text for multiple items
            self.download_button.setText(f"Download {len(self.selected_items)} Items")
            self.delete_button.setText(f"Delete {len(self.selected_items)} Items")
    
    def _handle_download(self):
        """Handle download button click"""
        if self.selected_items:
            self.download_requested.emit(self.selected_items)
    
    def _handle_delete(self):
        """Handle delete button click"""
        if self.selected_items:
            self.delete_requested.emit(self.selected_items)
    
    def _handle_copy_url(self):
        """Handle copy URL button click"""
        if self.current_item:
            self.copy_url_requested.emit(self.current_item)
    
    def clear(self):
        """Clear the details display"""
        self.details_text.clear()
        self.current_item = None
        self.selected_items = []
        self._update_button_states()
    
    def update_bucket_statistics(self, all_files: List[Dict[str, Any]]):
        """Update bucket statistics with all files data"""
        self.all_files = all_files
        self.reload_stats_button.setEnabled(bool(all_files))  # Enable button if we have files
        
        # For very large buckets, show a message instead of auto-calculating
        if len(all_files) > 50000:  # 50K+ files
            self.stats_text.setText(f"""📊 LARGE BUCKET DETECTED
            
This bucket contains {len(all_files):,} files.

To avoid performance issues, statistics calculation is not performed automatically.

Click the "🔄 Reload Statistics" button above to manually calculate comprehensive statistics.

⚠️  Note: Statistics calculation for buckets with {len(all_files):,} files may take several seconds to complete.""")
            print(f"[STATS] Large bucket detected ({len(all_files):,} files) - skipping auto-calculation")
        else:
            self._calculate_and_display_statistics()
    
    def _calculate_and_display_statistics(self):
        """Calculate and display bucket statistics using worker thread"""
        if not self.all_files:
            self.stats_text.setText("No files loaded yet...")
            self.reload_stats_button.setEnabled(False)
            return
        
        # Cancel any existing statistics calculation
        if self.stats_worker and self.stats_worker.isRunning():
            self.stats_worker.quit()
            self.stats_worker.wait()
        
        # Disable reload button during calculation
        self.reload_stats_button.setEnabled(False)
        self.reload_stats_button.setText("Calculating...")
        
        print(f"[STATS] Starting statistics calculation for {len(self.all_files):,} files")
        
        # Start statistics calculation in worker thread
        self.stats_worker = BucketStatisticsWorker(self.all_files)
        self.stats_worker.statistics_calculated.connect(self._on_statistics_calculated)
        self.stats_worker.progress_update.connect(self._on_statistics_progress)
        self.stats_worker.finished.connect(self._on_statistics_finished)
        self.stats_worker.start()
    
    def _reload_statistics(self):
        """Reload statistics calculation"""
        if self.all_files:
            self._calculate_and_display_statistics()
    
    def _on_statistics_calculated(self, stats_text: str):
        """Handle completion of statistics calculation"""
        self.stats_text.setText(stats_text)
        self.stats_progress_label.setText("Statistics updated successfully")
        self.statistics_calculated = True  # Mark as calculated
    
    def _on_statistics_progress(self, progress_message: str):
        """Handle progress updates from statistics calculation"""
        self.stats_progress_label.setText(progress_message)
    
    def _on_statistics_finished(self):
        """Handle statistics worker completion"""
        self.reload_stats_button.setEnabled(True)
        self.reload_stats_button.setText("🔄 Reload Statistics")
        
        # Clear progress after a delay
        QTimer.singleShot(3000, lambda: self.stats_progress_label.setText(""))
    
    def _on_tab_changed(self, index: int):
        """Handle tab change - calculate statistics when statistics tab is opened"""
        if index == self.statistics_tab_index and not self.statistics_calculated and self.all_files:
            print(f"[STATS] Statistics tab opened - triggering calculation for {len(self.all_files):,} files")
            self._calculate_and_display_statistics()
    
    def store_files_for_statistics(self, all_files: List[Dict[str, Any]]):
        """Store files for statistics calculation but don't calculate yet"""
        self.all_files = all_files
        self.statistics_calculated = False  # Reset calculation flag
        self.reload_stats_button.setEnabled(bool(all_files))
        
        # Reset statistics display
        if all_files:
            self.stats_text.setText("Statistics will be calculated when you first open this tab.")
        else:
            self.stats_text.setText("No files loaded yet...")
        
        print(f"[STATS] Stored {len(all_files):,} files for statistics - calculation deferred until tab access")
    
    def update_bucket_statistics(self, all_files: List[Dict[str, Any]]):
        """Legacy method - now just stores files without auto-calculating"""
        self.store_files_for_statistics(all_files)
    
    def set_buttons_enabled(self, enabled: bool):
        """Enable or disable all action buttons"""
        self.download_button.setEnabled(enabled and bool(self.selected_items))
        self.copy_url_button.setEnabled(enabled and bool(self.selected_items))
        self.delete_button.setEnabled(enabled and bool(self.selected_items))
    
    def set_connection_data_callback(self, callback):
        """Set callback to get connection data for URL generation"""
        self.connection_data_callback = callback
    
    def _is_image_file(self, filename: str) -> bool:
        """Check if file is an image based on extension"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff', '.ico'}
        _, ext = os.path.splitext(filename.lower())
        return ext in image_extensions
    
    def _update_image_preview(self, file_info: Dict[str, Any]):
        """Update image preview for a file"""
        # Cancel any existing image loading
        if self.image_worker and self.image_worker.isRunning():
            self.image_worker.quit()
            self.image_worker.wait()
        
        # Check if file is an image
        if not self._is_image_file(file_info['key']):
            self._hide_image_preview()
            return
        
        # Get connection data to construct URL
        if not self.connection_data_callback:
            self._hide_image_preview()
            return
        
        connection_data = self.connection_data_callback()
        if not connection_data or not all([connection_data.get('endpoint_url'), 
                                          connection_data.get('bucket_name')]):
            self._hide_image_preview()
            return
        
        # Construct image URL
        endpoint_url = connection_data['endpoint_url']
        bucket_name = connection_data['bucket_name']
        file_key = file_info['key']
        
        if endpoint_url.endswith('/'):
            endpoint_url = endpoint_url[:-1]
        
        image_url = f"{endpoint_url}/{bucket_name}/{file_key}"
        
        # Show preview section
        self.image_preview_label.setVisible(True)
        self.image_scroll_area.setVisible(True)
        self.image_display.setText("Loading image...")
        self.image_display.setPixmap(QPixmap())  # Clear any existing image
        
        # Start loading image
        self.image_worker = ImagePreviewWorker(image_url)
        self.image_worker.image_loaded.connect(self._on_image_loaded)
        self.image_worker.error_occurred.connect(self._on_image_error)
        self.image_worker.start()
    
    def _hide_image_preview(self):
        """Hide the image preview section"""
        # Cancel any existing image loading
        if self.image_worker and self.image_worker.isRunning():
            self.image_worker.quit()
            self.image_worker.wait()
        
        self.image_preview_label.setVisible(False)
        self.image_scroll_area.setVisible(False)
        self.image_display.clear()
    
    def _on_image_loaded(self, pixmap: QPixmap):
        """Handle successful image loading"""
        self.image_display.setPixmap(pixmap)
        self.image_display.setText("")  # Clear loading text
    
    def _on_image_error(self, error_message: str):
        """Handle image loading error"""
        self.image_display.setText(f"Failed to load image:\n{error_message}")
        self.image_display.setPixmap(QPixmap())  # Clear any existing image
