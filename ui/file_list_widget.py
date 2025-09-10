#!/usr/bin/env python3
"""
File list widget for S3 browser
Handles file listing, navigation, and virtual folder display
"""

from typing import List, Dict, Any, Optional
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QCheckBox, QFileDialog,
    QMessageBox, QInputDialog, QApplication, QLineEdit, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent, QDragMoveEvent, QDragLeaveEvent, QPainter, QPen

from backend import FileProcessor


class DragDropListWidget(QListWidget):
    """Custom QListWidget with drag and drop support for file uploads"""
    
    # Signal for drag and drop upload
    files_dropped = pyqtSignal(list, str)  # file_paths, target_prefix
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setAcceptDrops(True)
        self.drag_active = False
        
        # Drag overlay
        self.drag_overlay = None
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            # Check if any URLs are files
            urls = event.mimeData().urls()
            has_files = any(url.isLocalFile() for url in urls)
            
            if has_files:
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
                self.drag_active = True
                self.show_drag_overlay()
                return
        
        event.ignore()
    
    def dragMoveEvent(self, event: QDragMoveEvent):
        """Handle drag move events"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            has_files = any(url.isLocalFile() for url in urls)
            if has_files:
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
                return
        event.ignore()
    
    def dragLeaveEvent(self, event: QDragLeaveEvent):
        """Handle drag leave events"""
        self.drag_active = False
        self.hide_drag_overlay()
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        self.drag_active = False
        self.hide_drag_overlay()
        
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            file_paths = []
            
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if self.is_valid_file_or_directory(file_path):
                        file_paths.append(file_path)
            
            if file_paths:
                # Get current folder as target prefix
                target_prefix = ""
                if self.parent_widget and hasattr(self.parent_widget, 'current_folder'):
                    target_prefix = self.parent_widget.current_folder or ""
                
                # Validate and emit signal
                validation_result = self.validate_dropped_files(file_paths)
                if validation_result['valid']:
                    self.files_dropped.emit(file_paths, target_prefix)
                else:
                    # Show warning dialog
                    self.show_validation_warning(validation_result)
            
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()
    
    def is_valid_file_or_directory(self, path: str) -> bool:
        """Check if the path is a valid file or directory"""
        import os
        return os.path.exists(path) and (os.path.isfile(path) or os.path.isdir(path))
    
    def validate_dropped_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Validate dropped files for size and count limits"""
        import os
        
        total_files = 0
        total_size = 0
        max_files = 1000  # Maximum number of files
        max_size = 10 * 1024 * 1024 * 1024  # 10 GB limit
        
        def count_files_recursive(path: str) -> tuple:
            """Count files and total size recursively"""
            nonlocal total_files, total_size
            
            if os.path.isfile(path):
                total_files += 1
                total_size += os.path.getsize(path)
                return 1, os.path.getsize(path)
            elif os.path.isdir(path):
                dir_files = 0
                dir_size = 0
                try:
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                file_size = os.path.getsize(file_path)
                                dir_files += 1
                                dir_size += file_size
                                total_files += 1
                                total_size += file_size
                                
                                # Early exit if limits exceeded
                                if total_files > max_files or total_size > max_size:
                                    return dir_files, dir_size
                            except (OSError, IOError):
                                # Skip files that can't be accessed
                                continue
                except (OSError, IOError):
                    # Skip directories that can't be accessed
                    pass
                return dir_files, dir_size
            return 0, 0
        
        # Count all files
        for file_path in file_paths:
            count_files_recursive(file_path)
            # Early exit if limits exceeded
            if total_files > max_files or total_size > max_size:
                break
        
        # Check limits
        valid = True
        warnings = []
        
        if total_files > max_files:
            valid = False
            warnings.append(f"Too many files: {total_files} (limit: {max_files})")
        
        if total_size > max_size:
            valid = False
            size_mb = total_size / (1024 * 1024)
            limit_mb = max_size / (1024 * 1024)
            warnings.append(f"Total size too large: {size_mb:.1f} MB (limit: {limit_mb:.1f} MB)")
        
        return {
            'valid': valid,
            'total_files': total_files,
            'total_size': total_size,
            'warnings': warnings
        }
    
    def show_validation_warning(self, validation_result: Dict[str, Any]):
        """Show validation warning dialog"""
        warnings = validation_result['warnings']
        message = "Cannot upload files:\n\n" + "\n".join(warnings)
        
        QMessageBox.warning(self, "Upload Validation Failed", message)
    
    def show_drag_overlay(self):
        """Show drag overlay with upload indication"""
        if not self.drag_overlay:
            self.drag_overlay = DragOverlay(self)
        
        self.drag_overlay.resize(self.size())
        self.drag_overlay.show()
        self.drag_overlay.raise_()
    
    def hide_drag_overlay(self):
        """Hide drag overlay"""
        if self.drag_overlay:
            self.drag_overlay.hide()
    
    def resizeEvent(self, event):
        """Handle resize events to update overlay"""
        super().resizeEvent(event)
        if self.drag_overlay and self.drag_overlay.isVisible():
            self.drag_overlay.resize(self.size())


class DragOverlay(QWidget):
    """Overlay widget shown during drag operations"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 100, 200, 50);")
        
        # Create layout for centered text
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Upload icon and text
        self.label = QLabel("📁 Drop files and folders here to upload")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 100);
                padding: 20px;
                border-radius: 10px;
                border: 2px dashed white;
            }
        """)
        
        layout.addWidget(self.label)


class FileListWidget(QWidget):
    """Widget for displaying and managing S3 file lists"""
    
    # Signals
    item_double_clicked = pyqtSignal(QListWidgetItem)
    selection_changed = pyqtSignal()
    upload_requested = pyqtSignal(list, str)  # files_to_upload, s3_prefix
    download_requested = pyqtSignal(list)  # selected_items
    delete_requested = pyqtSignal(list)  # selected_items
    refresh_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.current_files: List[Dict[str, Any]] = []
        self.filtered_files: List[Dict[str, Any]] = []
        self.current_folder: Optional[str] = None
        self.search_query: str = ""
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        # Pagination settings
        self.page_size = 1000  # Max items per page
        self.current_page = 0
        self.total_pages = 0
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the file list widget UI"""
        layout = QVBoxLayout(self)
        
        # Search bar
        search_layout = self._create_search_controls()
        layout.addLayout(search_layout)
        
        # Title and controls
        title_layout = self._create_title_controls()
        layout.addLayout(title_layout)
        
        # Pagination controls
        pagination_layout = self._create_pagination_controls()
        layout.addLayout(pagination_layout)
        
        # File list with drag and drop support
        self.file_list = DragDropListWidget(self)
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.file_list.currentItemChanged.connect(self.on_file_selected)
        self.file_list.itemSelectionChanged.connect(self.selection_changed.emit)
        self.file_list.itemDoubleClicked.connect(self.item_double_clicked.emit)
        self.file_list.files_dropped.connect(self.on_files_dropped)
        layout.addWidget(self.file_list)
    
    def _create_title_controls(self) -> QHBoxLayout:
        """Create the title and control buttons layout"""
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Files:"))
        
        self.file_count_label = QLabel("0 files")
        self.file_count_label.setStyleSheet("color: gray;")
        title_layout.addWidget(self.file_count_label)
        
        title_layout.addStretch()
        
        # Navigation controls (shown only when in a folder)
        self.back_button = QPushButton("🔙 Back")
        self.back_button.clicked.connect(self.navigate_back)
        self.back_button.setMaximumWidth(60)
        self.back_button.setVisible(False)
        title_layout.addWidget(self.back_button)
        
        # Breadcrumb label
        self.breadcrumb_label = QLabel("")
        self.breadcrumb_label.setStyleSheet("color: blue; font-weight: bold;")
        self.breadcrumb_label.setVisible(False)
        title_layout.addWidget(self.breadcrumb_label)
        
        # Virtual directory toggle
        self.virtual_dirs_checkbox = QCheckBox("Folders")
        self.virtual_dirs_checkbox.setToolTip("Show files organized in virtual folders")
        self.virtual_dirs_checkbox.stateChanged.connect(self.toggle_virtual_directories)
        title_layout.addWidget(self.virtual_dirs_checkbox)
        
        # Upload button
        upload_button = QPushButton("Upload")
        upload_button.clicked.connect(self.upload_files)
        upload_button.setMaximumWidth(60)
        title_layout.addWidget(upload_button)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_requested.emit)
        refresh_button.setMaximumWidth(60)
        title_layout.addWidget(refresh_button)
        
        return title_layout
    
    def _create_search_controls(self) -> QHBoxLayout:
        """Create the search controls layout"""
        search_layout = QHBoxLayout()
        
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by filename...")
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_edit)
        
        self.clear_search_button = QPushButton("Clear")
        self.clear_search_button.clicked.connect(self.clear_search)
        self.clear_search_button.setMaximumWidth(60)
        search_layout.addWidget(self.clear_search_button)
        
        return search_layout
    
    def _create_pagination_controls(self) -> QHBoxLayout:
        """Create the pagination controls layout"""
        pagination_layout = QHBoxLayout()
        
        self.pagination_info_label = QLabel("Page 0 of 0")
        self.pagination_info_label.setStyleSheet("color: gray;")
        pagination_layout.addWidget(self.pagination_info_label)
        
        pagination_layout.addStretch()
        
        self.first_page_button = QPushButton("⏮️")
        self.first_page_button.setToolTip("First page")
        self.first_page_button.clicked.connect(self.go_to_first_page)
        self.first_page_button.setMaximumWidth(35)
        self.first_page_button.setEnabled(False)
        pagination_layout.addWidget(self.first_page_button)
        
        self.prev_page_button = QPushButton("⏪")
        self.prev_page_button.setToolTip("Previous page")
        self.prev_page_button.clicked.connect(self.go_to_prev_page)
        self.prev_page_button.setMaximumWidth(35)
        self.prev_page_button.setEnabled(False)
        pagination_layout.addWidget(self.prev_page_button)
        
        pagination_layout.addWidget(QLabel("Page:"))
        
        self.page_spinbox = QSpinBox()
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setMaximum(1)
        self.page_spinbox.valueChanged.connect(self.go_to_page)
        self.page_spinbox.setMaximumWidth(60)
        pagination_layout.addWidget(self.page_spinbox)
        
        self.next_page_button = QPushButton("⏩")
        self.next_page_button.setToolTip("Next page")
        self.next_page_button.clicked.connect(self.go_to_next_page)
        self.next_page_button.setMaximumWidth(35)
        self.next_page_button.setEnabled(False)
        pagination_layout.addWidget(self.next_page_button)
        
        self.last_page_button = QPushButton("⏭️")
        self.last_page_button.setToolTip("Last page")
        self.last_page_button.clicked.connect(self.go_to_last_page)
        self.last_page_button.setMaximumWidth(35)
        self.last_page_button.setEnabled(False)
        pagination_layout.addWidget(self.last_page_button)
        
        # Initially hide pagination controls
        self.pagination_info_label.setVisible(False)
        self.first_page_button.setVisible(False)
        self.prev_page_button.setVisible(False)
        self.page_spinbox.setVisible(False)
        self.next_page_button.setVisible(False)
        self.last_page_button.setVisible(False)
        
        return pagination_layout
    
    def set_files(self, files: List[Dict[str, Any]]):
        """Set the current files list"""
        self.current_files = files
        self.current_page = 0  # Reset to first page when new files are loaded
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the file display based on current state"""
        if self.current_folder:
            self.populate_folder_contents(self.current_folder)
        else:
            # Use search and pagination for root view
            self.filter_and_paginate_files()
    
    def populate_file_list(self, files: List[Dict[str, Any]]):
        """Populate the file list widget with flat file view"""
        self.file_list.clear()
        
        for file_info in files:
            size_str = FileProcessor.format_size(file_info['size'])
            
            # Create list item
            item_text = f"{file_info['key']} ({size_str})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, file_info)
            self.file_list.addItem(item)
            
        self.file_count_label.setText(f"{len(files)} files")
    
    def populate_file_list_with_folders(self):
        """Populate file list with virtual folder structure"""
        if not self.current_files:
            return
            
        self.file_list.clear()
        
        folders, root_files = FileProcessor.organize_files_by_folders(self.current_files)
        
        # Add folders
        for folder_name in sorted(folders.keys()):
            folder_files = folders[folder_name]
            total_size = sum(f['size'] for f in folder_files)
            size_str = FileProcessor.format_size(total_size)
            
            item_text = f"📁 {folder_name}/ ({len(folder_files)} files, {size_str})"
            item = QListWidgetItem(item_text)
            
            # Store folder info
            folder_info = {
                'is_folder': True,
                'folder_name': folder_name,
                'files': folder_files,
                'file_count': len(folder_files),
                'total_size': total_size
            }
            item.setData(Qt.ItemDataRole.UserRole, folder_info)
            self.file_list.addItem(item)
        
        # Add root files
        for file_info in root_files:
            size_str = FileProcessor.format_size(file_info['size'])
            
            item_text = f"📄 {file_info['key']} ({size_str})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, file_info)
            self.file_list.addItem(item)
        
        folder_count = len(folders)
        file_count = len(root_files)
        self.file_count_label.setText(f"{folder_count} folders, {file_count} files")
    
    def populate_folder_contents(self, folder_path: str):
        """Populate the file list with contents of a specific folder"""
        if not self.current_files:
            return
        
        self.file_list.clear()
        
        subdirectories, direct_files = FileProcessor.get_folder_contents(self.current_files, folder_path)
        
        # Add subdirectories first (sorted)
        for subdirectory_name in sorted(subdirectories.keys()):
            subdir_files = subdirectories[subdirectory_name]
            total_size = sum(f['size'] for f in subdir_files)
            size_str = FileProcessor.format_size(total_size)
            
            item_text = f"📁 {subdirectory_name}/ ({len(subdir_files)} files, {size_str})"
            item = QListWidgetItem(item_text)
            
            # Store folder info with the full path
            folder_info = {
                'is_folder': True,
                'folder_name': subdirectory_name,
                'folder_path': f"{folder_path}/{subdirectory_name}",  # Full path for navigation
                'files': subdir_files,
                'file_count': len(subdir_files),
                'total_size': total_size
            }
            item.setData(Qt.ItemDataRole.UserRole, folder_info)
            self.file_list.addItem(item)
        
        # Add direct files (sorted)
        for file_info, display_name in sorted(direct_files, key=lambda x: x[1]):
            size_str = FileProcessor.format_size(file_info['size'])
            
            item_text = f"📄 {display_name} ({size_str})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, file_info)
            self.file_list.addItem(item)
        
        if len(subdirectories) > 0:
            self.file_count_label.setText(f"{len(subdirectories)} folders, {len(direct_files)} files in {folder_path}/")
        else:
            self.file_count_label.setText(f"{len(direct_files)} files in {folder_path}/")
    
    def navigate_to_folder(self, folder_path: str):
        """Navigate into a virtual folder"""
        self.current_folder = folder_path
        self.update_navigation_controls()
        self.populate_folder_contents(folder_path)
    
    def navigate_back(self):
        """Navigate back to the root directory"""
        self.current_folder = None
        self.update_navigation_controls()
        self.refresh_display()
    
    def update_navigation_controls(self):
        """Update visibility and state of navigation controls"""
        is_in_folder = self.current_folder is not None
        
        self.back_button.setVisible(is_in_folder)
        self.breadcrumb_label.setVisible(is_in_folder)
        
        if is_in_folder:
            self.breadcrumb_label.setText(f"📁 {self.current_folder}/")
        else:
            self.breadcrumb_label.setText("")
    
    def toggle_virtual_directories(self, state):
        """Toggle virtual directory view"""
        self.current_page = 0  # Reset to first page when toggling view
        self.refresh_display()
    
    def get_selected_items(self) -> List[QListWidgetItem]:
        """Get currently selected items"""
        return self.file_list.selectedItems()
    
    def get_current_item(self) -> Optional[QListWidgetItem]:
        """Get currently selected item"""
        return self.file_list.currentItem()
    
    def clear(self):
        """Clear the file list"""
        self.file_list.clear()
        self.file_count_label.setText("0 files")
        self.current_folder = None
        self.current_page = 0
        self.search_query = ""
        self.search_edit.clear()
        self.hide_pagination_controls()
        self.update_navigation_controls()
    
    def on_file_selected(self, current_item: Optional[QListWidgetItem], previous_item: Optional[QListWidgetItem]):
        """Handle file selection - this can be overridden by parent"""
        pass
    
    def upload_files(self):
        """Handle upload request"""
        # Get files to upload
        files_to_upload, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Upload", QApplication.instance().property("last_directory") or ""
        )
        
        if not files_to_upload:
            return
        
        # Remember last directory
        if files_to_upload:
            import os
            last_dir = os.path.dirname(files_to_upload[0])
            QApplication.instance().setProperty("last_directory", last_dir)
        
        # Ask for S3 prefix (virtual directory)
        default_prefix = self.current_folder if self.current_folder else ""
        s3_prefix, ok = QInputDialog.getText(
            self, "Upload Directory", 
            "Enter folder path (leave empty for root):",
            text=default_prefix
        )
        
        if not ok:
            return
            
        s3_prefix = s3_prefix.strip().strip('/')
        
        self.upload_requested.emit(files_to_upload, s3_prefix)
    
    def get_current_navigation_state(self) -> Dict[str, Any]:
        """Get the current navigation state to restore later"""
        return {
            'current_folder': self.current_folder,
            'virtual_dirs_enabled': self.virtual_dirs_checkbox.isChecked()
        }
    
    def restore_navigation_state(self, state: Dict[str, Any]):
        """Restore a previous navigation state"""
        if state is None:
            return
        
        # Restore virtual directories setting
        virtual_dirs_enabled = state.get('virtual_dirs_enabled', False)
        self.virtual_dirs_checkbox.setChecked(virtual_dirs_enabled)
        
        # Restore folder navigation
        current_folder = state.get('current_folder')
        if current_folder and virtual_dirs_enabled:
            self.current_folder = current_folder
            self.update_navigation_controls()
        else:
            self.current_folder = None
            self.update_navigation_controls()
        
        # Refresh display with restored state
        self.refresh_display()
    
    # Search functionality
    def on_search_text_changed(self, text: str):
        """Handle search text changes with debouncing"""
        self.search_query = text.strip()
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms delay
    
    def perform_search(self):
        """Perform the actual search and update display"""
        self.current_page = 0
        self.filter_and_paginate_files()
    
    def clear_search(self):
        """Clear the search query and show all files"""
        self.search_edit.clear()
        self.search_query = ""
        self.current_page = 0
        self.filter_and_paginate_files()
    
    def filter_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter files based on search query"""
        if not self.search_query:
            return files
        
        filtered = []
        # Create case-insensitive regex pattern
        try:
            pattern = re.compile(re.escape(self.search_query), re.IGNORECASE)
        except re.error:
            # If regex fails, fall back to simple string matching
            pattern = None
        
        for file_info in files:
            filename = file_info['key']
            
            # Search in filename
            if pattern:
                if pattern.search(filename):
                    filtered.append(file_info)
            else:
                if self.search_query.lower() in filename.lower():
                    filtered.append(file_info)
        
        return filtered
    
    def filter_and_paginate_files(self):
        """Apply search filter and pagination to current files"""
        # Get the base files list
        if self.current_folder:
            # When in a folder, we need to handle differently
            self.populate_folder_contents(self.current_folder)
            return
        elif self.virtual_dirs_checkbox.isChecked():
            # For folder view, search within all files but still organize
            self.filtered_files = self.filter_files(self.current_files)
            self.populate_file_list_with_folders_filtered()
            return
        else:
            # Flat file view
            self.filtered_files = self.filter_files(self.current_files)
        
        # Calculate pagination
        total_items = len(self.filtered_files)
        self.total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        
        # Update pagination controls
        self.update_pagination_controls(total_items)
        
        # Get current page items
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, total_items)
        page_files = self.filtered_files[start_idx:end_idx]
        
        # Populate the list
        self.populate_file_list_paginated(page_files, start_idx, total_items)
    
    def populate_file_list_with_folders_filtered(self):
        """Populate file list with virtual folder structure (filtered)"""
        if not self.filtered_files:
            self.file_list.clear()
            if self.search_query:
                self.file_count_label.setText(f"0 files match '{self.search_query}'")
            else:
                self.file_count_label.setText("0 files")
            self.hide_pagination_controls()
            return
        
        folders, root_files = FileProcessor.organize_files_by_folders(self.filtered_files)
        
        # Calculate total items for pagination
        total_items = len(folders) + len(root_files)
        self.total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
        
        # Update pagination controls
        self.update_pagination_controls(total_items)
        
        # Get items for current page
        all_items = []
        
        # Add folders first
        for folder_name in sorted(folders.keys()):
            folder_files = folders[folder_name]
            total_size = sum(f['size'] for f in folder_files)
            all_items.append({
                'type': 'folder',
                'name': folder_name,
                'files': folder_files,
                'file_count': len(folder_files),
                'total_size': total_size
            })
        
        # Add root files
        for file_info in root_files:
            all_items.append({
                'type': 'file',
                'file_info': file_info
            })
        
        # Paginate
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(all_items))
        page_items = all_items[start_idx:end_idx]
        
        # Populate the list
        self.file_list.clear()
        
        for item in page_items:
            if item['type'] == 'folder':
                size_str = FileProcessor.format_size(item['total_size'])
                item_text = f"📁 {item['name']}/ ({item['file_count']} files, {size_str})"
                list_item = QListWidgetItem(item_text)
                
                folder_info = {
                    'is_folder': True,
                    'folder_name': item['name'],
                    'files': item['files'],
                    'file_count': item['file_count'],
                    'total_size': item['total_size']
                }
                list_item.setData(Qt.ItemDataRole.UserRole, folder_info)
                self.file_list.addItem(list_item)
            else:
                file_info = item['file_info']
                size_str = FileProcessor.format_size(file_info['size'])
                item_text = f"📄 {file_info['key']} ({size_str})"
                list_item = QListWidgetItem(item_text)
                list_item.setData(Qt.ItemDataRole.UserRole, file_info)
                self.file_list.addItem(list_item)
        
        # Update count label
        if self.search_query:
            self.file_count_label.setText(f"{len(folders)} folders, {len(root_files)} files match '{self.search_query}'")
        else:
            self.file_count_label.setText(f"{len(folders)} folders, {len(root_files)} files")
    
    def populate_file_list_paginated(self, files: List[Dict[str, Any]], start_idx: int, total_items: int):
        """Populate the file list widget with paginated file view"""
        self.file_list.clear()
        
        for file_info in files:
            size_str = FileProcessor.format_size(file_info['size'])
            item_text = f"{file_info['key']} ({size_str})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, file_info)
            self.file_list.addItem(item)
        
        # Update count label
        if self.search_query:
            if total_items == len(files):
                self.file_count_label.setText(f"{total_items} files match '{self.search_query}'")
            else:
                self.file_count_label.setText(f"Showing {len(files)} of {total_items} files matching '{self.search_query}'")
        else:
            if total_items == len(files):
                self.file_count_label.setText(f"{total_items} files")
            else:
                self.file_count_label.setText(f"Showing {len(files)} of {total_items} files")
    
    # Pagination functionality
    def update_pagination_controls(self, total_items: int):
        """Update pagination controls visibility and state"""
        show_pagination = total_items > self.page_size
        
        if show_pagination:
            self.show_pagination_controls()
            
            # Update pagination info
            self.pagination_info_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
            
            # Update spinbox
            self.page_spinbox.setMaximum(self.total_pages)
            self.page_spinbox.setValue(self.current_page + 1)
            
            # Update button states
            self.first_page_button.setEnabled(self.current_page > 0)
            self.prev_page_button.setEnabled(self.current_page > 0)
            self.next_page_button.setEnabled(self.current_page < self.total_pages - 1)
            self.last_page_button.setEnabled(self.current_page < self.total_pages - 1)
        else:
            self.hide_pagination_controls()
    
    def show_pagination_controls(self):
        """Show pagination controls"""
        self.pagination_info_label.setVisible(True)
        self.first_page_button.setVisible(True)
        self.prev_page_button.setVisible(True)
        self.page_spinbox.setVisible(True)
        self.next_page_button.setVisible(True)
        self.last_page_button.setVisible(True)
    
    def hide_pagination_controls(self):
        """Hide pagination controls"""
        self.pagination_info_label.setVisible(False)
        self.first_page_button.setVisible(False)
        self.prev_page_button.setVisible(False)
        self.page_spinbox.setVisible(False)
        self.next_page_button.setVisible(False)
        self.last_page_button.setVisible(False)
    
    def go_to_first_page(self):
        """Go to first page"""
        self.current_page = 0
        self.filter_and_paginate_files()
    
    def go_to_prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.filter_and_paginate_files()
    
    def go_to_next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.filter_and_paginate_files()
    
    def go_to_last_page(self):
        """Go to last page"""
        self.current_page = self.total_pages - 1
        self.filter_and_paginate_files()
    
    def go_to_page(self, page_number: int):
        """Go to specific page (1-indexed)"""
        new_page = page_number - 1  # Convert to 0-indexed
        if 0 <= new_page < self.total_pages and new_page != self.current_page:
            self.current_page = new_page
            self.filter_and_paginate_files()
    
    def on_files_dropped(self, file_paths: List[str], target_prefix: str):
        """Handle files dropped onto the file list"""
        # Expand directories to individual files
        expanded_files = self.expand_paths_to_files(file_paths)
        
        if expanded_files:
            # Emit upload request with expanded file list
            self.upload_requested.emit(expanded_files, target_prefix)
    
    def expand_paths_to_files(self, paths: List[str]) -> List[str]:
        """Expand directory paths to individual file paths"""
        import os
        
        expanded_files = []
        
        for path in paths:
            if os.path.isfile(path):
                expanded_files.append(path)
            elif os.path.isdir(path):
                # Walk through directory and add all files
                try:
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            if os.path.isfile(file_path):
                                expanded_files.append(file_path)
                except (OSError, IOError):
                    # Skip directories that can't be accessed
                    continue
        
        return expanded_files
