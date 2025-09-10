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
    QMessageBox, QInputDialog
)
from PyQt6.QtCore import pyqtSignal


class ConnectionWidget(QWidget):
    """Widget for managing S3 connections and profiles"""
    
    # Signals
    connection_requested = pyqtSignal(str, str, str, str)  # endpoint, access_key, secret_key, bucket
    connection_cancelled = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.profiles_file = os.path.join(os.path.expanduser("~"), ".s3_browser_profiles.json")
        self.init_ui()
        self.load_profiles()
    
    def init_ui(self):
        """Initialize the connection widget UI"""
        layout = QVBoxLayout(self)
        
        # Create connection group
        self.connection_group = self._create_connection_group()
        layout.addWidget(self.connection_group)
    
    def _create_connection_group(self) -> QGroupBox:
        """Create the connection settings group with compact layout"""
        group = QGroupBox("S3 Connection")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)  # Compact spacing
        
        # First row: Profile, Endpoint, and Bucket
        row1_layout = QHBoxLayout()
        self._setup_profile_controls(row1_layout)
        self._setup_endpoint_controls(row1_layout)
        self._setup_bucket_controls(row1_layout)
        layout.addLayout(row1_layout)
        
        # Second row: Credentials and Connect button
        row2_layout = QHBoxLayout()
        self._setup_credential_controls(row2_layout)
        self._setup_connect_controls(row2_layout)
        layout.addLayout(row2_layout)
        
        return group
    
    def _setup_profile_controls(self, layout: QHBoxLayout):
        """Setup profile management controls"""
        layout.addWidget(QLabel("Profile:"))
        
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(120)
        self.profile_combo.setMaximumWidth(150)
        self.profile_combo.addItem("-- New --")
        self.profile_combo.currentTextChanged.connect(self.on_profile_selected)
        layout.addWidget(self.profile_combo)
        
        self.save_profile_button = QPushButton("Save")
        self.save_profile_button.clicked.connect(self.save_current_profile)
        self.save_profile_button.setMaximumWidth(50)
        layout.addWidget(self.save_profile_button)
        
        self.delete_profile_button = QPushButton("Del")
        self.delete_profile_button.clicked.connect(self.delete_current_profile)
        self.delete_profile_button.setMaximumWidth(40)
        self.delete_profile_button.setEnabled(False)
        layout.addWidget(self.delete_profile_button)

        # Export and import buttons
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self.export_credentials)
        layout.addWidget(self.export_button)

        self.import_button = QPushButton("Import")
        self.import_button.clicked.connect(self.import_credentials)
        layout.addWidget(self.import_button)
    
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
        """Setup browse and cancel buttons"""
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
    
    # Profile Management Methods
    def load_profiles(self):
        """Load saved credential profiles from file"""
        try:
            if os.path.exists(self.profiles_file):
                with open(self.profiles_file, 'r') as f:
                    profiles = json.load(f)
                
                # Clear existing profiles (except the default)
                self.profile_combo.clear()
                self.profile_combo.addItem("-- Select or create new --")
                
                # Add saved profiles
                for profile_name in sorted(profiles.keys()):
                    self.profile_combo.addItem(profile_name)
                    
        except Exception as e:
            print(f"Error loading profiles: {e}")
    
    def save_profiles(self, profiles: Dict[str, Any]):
        """Save credential profiles to file"""
        try:
            with open(self.profiles_file, 'w') as f:
                json.dump(profiles, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save profiles: {e}")
    
    def export_credentials(self):
            """Export credentials to JSON file"""
            credentials = self.get_current_profile_data()
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "Export Credentials", "", "JSON Files (*.json)", options=options)
            if file_name:
                try:
                    with open(file_name, 'w') as f:
                        json.dump(credentials, f, indent=2)
                    QMessageBox.information(self, "Success", "Credentials exported successfully.")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to export credentials: {e}")

    def import_credentials(self):
            """Import credentials from JSON file"""
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getOpenFileName(self, "Import Credentials", "", "JSON Files (*.json)", options=options)
            if file_name:
                try:
                    with open(file_name, 'r') as f:
                        credentials = json.load(f)
                    self.load_profile_data(credentials)
                    QMessageBox.information(self, "Success", "Credentials imported successfully.")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to import credentials: {e}")

    
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
    
    def on_profile_selected(self, profile_name: str):
        """Handle profile selection from dropdown"""
        if profile_name == "-- Select or create new --":
            self.delete_profile_button.setEnabled(False)
            return
            
        try:
            if os.path.exists(self.profiles_file):
                with open(self.profiles_file, 'r') as f:
                    profiles = json.load(f)
                
                if profile_name in profiles:
                    self.load_profile_data(profiles[profile_name])
                    self.delete_profile_button.setEnabled(True)
                else:
                    self.delete_profile_button.setEnabled(False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load profile: {e}")
    
    def save_current_profile(self):
        """Save current form data as a new profile"""
        # Validate that we have some data to save
        current_data = self.get_current_profile_data()
        if not any(current_data.values()):
            QMessageBox.warning(self, "Nothing to Save", 
                              "Please enter connection details before saving a profile.")
            return
        
        # Ask for profile name
        profile_name, ok = QInputDialog.getText(
            self, "Save Profile", 
            "Enter a name for this profile:",
            QLineEdit.EchoMode.Normal,
            f"{current_data.get('bucket_name', 'New Profile')}"
        )
        
        if not ok or not profile_name.strip():
            return
            
        profile_name = profile_name.strip()
        
        # Load existing profiles
        profiles = {}
        try:
            if os.path.exists(self.profiles_file):
                with open(self.profiles_file, 'r') as f:
                    profiles = json.load(f)
        except Exception as e:
            print(f"Error loading existing profiles: {e}")
        
        # Check if profile already exists
        if profile_name in profiles:
            reply = QMessageBox.question(
                self, "Profile Exists", 
                f"Profile '{profile_name}' already exists. Overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Save the profile
        profiles[profile_name] = current_data
        self.save_profiles(profiles)
        
        # Update the dropdown
        self.load_profiles()
        
        # Select the newly saved profile
        index = self.profile_combo.findText(profile_name)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
    
    def delete_current_profile(self):
        """Delete the currently selected profile"""
        current_profile = self.profile_combo.currentText()
        
        if current_profile == "-- Select or create new --":
            return
        
        reply = QMessageBox.question(
            self, "Delete Profile", 
            f"Are you sure you want to delete the profile '{current_profile}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Load existing profiles
            profiles = {}
            if os.path.exists(self.profiles_file):
                with open(self.profiles_file, 'r') as f:
                    profiles = json.load(f)
            
            # Remove the profile
            if current_profile in profiles:
                del profiles[current_profile]
                self.save_profiles(profiles)
                
                # Clear the form
                self.endpoint_edit.setText("https://s3.amazonaws.com")
                self.bucket_edit.clear()
                self.access_key_edit.clear()
                self.secret_key_edit.clear()
                
                # Refresh the dropdown
                self.load_profiles()
                self.profile_combo.setCurrentIndex(0)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not delete profile: {e}")
