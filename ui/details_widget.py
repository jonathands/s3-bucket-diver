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
    QTextEdit, QListWidgetItem, QApplication, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QPixmap, QMovie

from backend import FileProcessor


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
        self.connection_data_callback = None  # Will be set by main window
        self.init_ui()
    
    def init_ui(self):
        """Initialize the details widget UI"""
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("File Details:"))
        
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
        
        # Action buttons
        button_layout = self._create_action_buttons()
        layout.addLayout(button_layout)
        
        layout.addStretch()
    
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
