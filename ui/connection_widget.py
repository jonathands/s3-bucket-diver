#!/usr/bin/env python3
"""
Connection widget for S3 browser
Handles S3 connection settings and profile management
"""

import json
import os
from typing import Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QGroupBox, QCheckBox, QComboBox,
    QMessageBox, QInputDialog, QFileDialog
)
from PyQt6.QtCore import pyqtSignal


class ConnectionWidget(QWidget):
    """Widget for managing S3 connections and profiles"""
    
    # Signals
    connection_requested = pyqtSignal(str, str, str, str)  # endpoint, access_key, secret_key, bucket
    connection_cancelled = pyqtSignal()
    profiles_changed = pyqtSignal()  # Emitted when profiles are modified
    bookmark_added = pyqtSignal(dict)  # Emitted when connection is added to bookmarks
    
    def __init__(self):
        super().__init__()
        self.profiles_file = os.path.join(os.path.expanduser("~"), ".s3_browser_profiles.json")
        self.init_ui()
    
    def init_ui(self):
        """Initialize the connection widget UI"""
        layout = QVBoxLayout(self)
        
        # Create connection group
        self.connection_group = self._create_connection_group()
        layout.addWidget(self.connection_group)
        
        # Create floating favorites button
        self._create_floating_favorites_button()
    
    def _create_floating_favorites_button(self):
        """Create the floating bookmarks button in top right corner"""
        self.favorites_button = QPushButton("☆", self)  # Just the star, no text for floating button
        self.favorites_button.setEnabled(False)  # Disabled initially
        self.favorites_button.setFixedSize(24, 24)  # Small square button
        self.favorites_button.clicked.connect(self.add_to_bookmarks)
        self.favorites_button.setToolTip("Add to Bookmarks")
        
        # Position in top right corner
        self.favorites_button.move(self.width() - 30, 6)
    
    def resizeEvent(self, event):
        """Handle resize to keep favorites button in top right"""
        super().resizeEvent(event)
        if hasattr(self, 'favorites_button'):
            self.favorites_button.move(self.width() - 30, 6)
    
    def _create_connection_group(self) -> QGroupBox:
        """Create the connection settings group with compact layout"""
        group = QGroupBox("S3 Connection")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)  # Compact spacing
        
        # First row: Endpoint and Bucket
        row1_layout = QHBoxLayout()
        self._setup_endpoint_controls(row1_layout)
        self._setup_bucket_controls(row1_layout)
        layout.addLayout(row1_layout)
        
        # Second row: Credentials and Connect button
        row2_layout = QHBoxLayout()
        self._setup_credential_controls(row2_layout)
        self._setup_connect_controls(row2_layout)
        layout.addLayout(row2_layout)
        
        return group
    
    def _setup_endpoint_controls(self, layout: QHBoxLayout):
        """Setup endpoint URL controls"""
        layout.addWidget(QLabel("Endpoint:"))
        
        self.endpoint_edit = QLineEdit()
        self.endpoint_edit.setPlaceholderText("https://s3.amazonaws.com")
        self.endpoint_edit.setText("https://s3.amazonaws.com")
        self.endpoint_edit.setMinimumHeight(24)
        layout.addWidget(self.endpoint_edit)
    
    def _setup_bucket_controls(self, layout: QHBoxLayout):
        """Setup bucket name controls"""
        layout.addWidget(QLabel("Bucket:"))
        
        self.bucket_edit = QLineEdit()
        self.bucket_edit.setPlaceholderText("bucket-name")
        self.bucket_edit.setMinimumHeight(24)
        self.bucket_edit.setMaximumWidth(240)
        layout.addWidget(self.bucket_edit)
    
    def _setup_credential_controls(self, layout: QHBoxLayout):
        """Setup credential input controls"""
        layout.addWidget(QLabel("Access:"))
        
        self.access_key_edit = QLineEdit()
        self.access_key_edit.setPlaceholderText("Access key")
        self.access_key_edit.setMinimumHeight(24)
        layout.addWidget(self.access_key_edit)
        
        layout.addWidget(QLabel("Secret:"))
        
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_key_edit.setPlaceholderText("Secret key")
        self.secret_key_edit.setMinimumHeight(24)
        layout.addWidget(self.secret_key_edit)
        
        # Show passwords checkbox
        self.show_passwords_checkbox = QCheckBox("Show")
        self.show_passwords_checkbox.stateChanged.connect(self.toggle_password_visibility)
        layout.addWidget(self.show_passwords_checkbox)
    
    def _setup_connect_controls(self, layout: QHBoxLayout):
        """Setup browse, cancel, and favorites buttons"""
        self.connect_button = QPushButton("Browse")
        self.connect_button.clicked.connect(self.request_connection)
        self.connect_button.setDefault(True)
        self.connect_button.setMinimumHeight(24)
        self.connect_button.setMinimumWidth(80)
        layout.addWidget(self.connect_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_connection)
        self.cancel_button.setMinimumHeight(24)
        self.cancel_button.setMinimumWidth(60)
        self.cancel_button.setVisible(False)  # Hidden by default
        layout.addWidget(self.cancel_button)
    
    def toggle_password_visibility(self, state):
        """Toggle visibility of credential fields"""
        if state == 2:  # Checked
            self.access_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.secret_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.access_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.secret_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
    
    def request_connection(self):
        """Request connection with current settings"""
        # Validate inputs
        endpoint_url = self.endpoint_edit.text().strip()
        access_key = self.access_key_edit.text().strip()
        secret_key = self.secret_key_edit.text().strip()
        bucket_name = self.bucket_edit.text().strip()
        
        if not all([endpoint_url, access_key, secret_key, bucket_name]):
            QMessageBox.warning(self, "Missing Information", 
                              "Please fill in all connection fields.")
            return
        
        self.connection_requested.emit(endpoint_url, access_key, secret_key, bucket_name)
    
    def cancel_connection(self):
        """Handle cancel button click"""
        self.connection_cancelled.emit()
    
    def set_connect_enabled(self, enabled: bool, show_cancel: bool = False):
        """Enable or disable the browse button and show/hide cancel button"""
        self.connect_button.setEnabled(enabled)
        self.cancel_button.setVisible(show_cancel)
    
    def get_current_profile_data(self) -> Dict[str, str]:
        """Get current form data as profile"""
        return {
            "endpoint_url": self.endpoint_edit.text().strip(),
            "bucket_name": self.bucket_edit.text().strip(),
            "access_key": self.access_key_edit.text().strip(),
            "secret_key": self.secret_key_edit.text().strip()
        }
    
    def load_profile_data(self, profile_data: Dict[str, str]):
        """Load profile data into form fields"""
        self.endpoint_edit.setText(profile_data.get("endpoint_url", ""))
        self.bucket_edit.setText(profile_data.get("bucket_name", ""))
        self.access_key_edit.setText(profile_data.get("access_key", ""))
        self.secret_key_edit.setText(profile_data.get("secret_key", ""))
    
    def add_to_bookmarks(self):
        """Add current connection to bookmarks using bucket name"""
        profile_data = self.get_current_profile_data()
        
        # Validate that we have connection data
        if not all([profile_data.get("endpoint_url"), profile_data.get("access_key"), 
                   profile_data.get("secret_key"), profile_data.get("bucket_name")]):
            QMessageBox.warning(self, "Incomplete Data", 
                              "Cannot add to bookmarks: Missing connection information.")
            return
        
        # Use bucket name as bookmark name
        bookmark_name = profile_data.get("bucket_name", "Unknown Bucket")
        profile_data['name'] = bookmark_name
        
        self.bookmark_added.emit(profile_data)
        QMessageBox.information(self, "Success", 
                              f"Bucket '{bookmark_name}' has been bookmarked.")
    
    def set_bookmarks_enabled(self, enabled: bool):
        """Enable or disable the bookmarks button"""
        self.favorites_button.setEnabled(enabled)
        if enabled:
            self.favorites_button.setText("⭐")  # Golden star when enabled
            self.favorites_button.setToolTip("Add to Bookmarks")
        else:
            self.favorites_button.setText("☆")  # Gray star when disabled  
            self.favorites_button.setToolTip("Connect first to add bookmarks")
