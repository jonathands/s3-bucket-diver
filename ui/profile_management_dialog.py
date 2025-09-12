#!/usr/bin/env python3
"""
Profile Management Dialog for S3 Browser
Advanced profile management with better UI and organization
"""

import json
import os
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QInputDialog, QTextEdit, QSplitter,
    QFormLayout, QFrame, QCheckBox, QProgressDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from PyQt6.QtGui import QFont


class ConnectionTestWorker(QThread):
    """Worker thread to test S3 connection without loading files"""
    
    test_complete = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket_name: str):
        super().__init__()
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        
    def run(self):
        """Test the S3 connection"""
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
            
            # Create S3 client with custom endpoint
            session = boto3.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key
            )
            
            s3_client = session.client(
                's3',
                endpoint_url=self.endpoint_url,
                verify=False  # For testing, ignore SSL verification
            )
            
            # Test 1: Check if we can connect to the endpoint
            try:
                s3_client.list_buckets()
            except EndpointConnectionError:
                self.test_complete.emit(False, "Cannot connect to endpoint. Please check the URL and your network connection.")
                return
            except NoCredentialsError:
                self.test_complete.emit(False, "Invalid credentials. Please check your access key and secret key.")
                return
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'InvalidAccessKeyId':
                    self.test_complete.emit(False, "Invalid access key. Please check your credentials.")
                    return
                elif error_code == 'SignatureDoesNotMatch':
                    self.test_complete.emit(False, "Invalid secret key. Please check your credentials.")
                    return
                else:
                    # Connection works but we might not have list_buckets permission, that's ok
                    pass
            
            # Test 2: Check if bucket exists and is accessible
            try:
                s3_client.head_bucket(Bucket=self.bucket_name)
                self.test_complete.emit(True, f"Connection successful! Bucket '{self.bucket_name}' is accessible.")
                return
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    self.test_complete.emit(False, f"Bucket '{self.bucket_name}' does not exist or is not accessible.")
                    return
                elif error_code == '403':
                    self.test_complete.emit(False, f"Access denied to bucket '{self.bucket_name}'. Please check your permissions.")
                    return
                else:
                    self.test_complete.emit(False, f"Error accessing bucket: {e}")
                    return
            
            # If we get here, basic connection works
            self.test_complete.emit(True, "Connection test completed successfully.")
            
        except ImportError:
            self.test_complete.emit(False, "boto3 library not available for connection testing.")
        except Exception as e:
            self.test_complete.emit(False, f"Unexpected error during connection test: {str(e)}")


class ProfileManagementDialog(QDialog):
    """Advanced profile management dialog with better organization and features"""
    
    profile_selected = pyqtSignal(str)  # Emitted when user selects a profile to load
    
    def __init__(self, connection_widget, parent=None):
        super().__init__(parent)
        self.connection_widget = connection_widget
        self.profiles_file = os.path.join(os.path.expanduser("~"), ".s3_browser_profiles.json")
        self.profiles = {}
        self.current_profile_name = None
        
        self.init_ui()
        self.load_profiles()
        self.update_profile_list()
        
    def init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("Profile Management")
        self.setGeometry(200, 200, 800, 600)
        self.setModal(True)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for left/right panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Profile list
        left_panel = self._create_profile_list_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Profile details
        right_panel = self._create_profile_details_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (30% left, 70% right)
        splitter.setSizes([240, 560])
        
        # Button row
        button_layout = self._create_button_layout()
        main_layout.addLayout(button_layout)
        
    def _create_profile_list_panel(self) -> QGroupBox:
        """Create the left panel with profile list"""
        group = QGroupBox("Saved Profiles")
        layout = QVBoxLayout(group)
        
        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self.on_profile_selection_changed)
        layout.addWidget(self.profile_list)
        
        # Profile list buttons
        list_buttons_layout = QHBoxLayout()
        
        self.new_profile_btn = QPushButton("New")
        self.new_profile_btn.clicked.connect(self.new_profile)
        list_buttons_layout.addWidget(self.new_profile_btn)
        
        self.duplicate_profile_btn = QPushButton("Duplicate")
        self.duplicate_profile_btn.clicked.connect(self.duplicate_profile)
        self.duplicate_profile_btn.setEnabled(False)
        list_buttons_layout.addWidget(self.duplicate_profile_btn)
        
        self.delete_profile_btn = QPushButton("Delete")
        self.delete_profile_btn.clicked.connect(self.delete_profile)
        self.delete_profile_btn.setEnabled(False)
        list_buttons_layout.addWidget(self.delete_profile_btn)
        
        layout.addLayout(list_buttons_layout)
        
        return group
        
    def _create_profile_details_panel(self) -> QGroupBox:
        """Create the right panel with profile details"""
        group = QGroupBox("Profile Details")
        layout = QVBoxLayout(group)
        
        # Profile form
        form_layout = QFormLayout()
        
        # Profile name
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.on_profile_data_changed)
        form_layout.addRow("Profile Name:", self.name_edit)
        
        # Connection details
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        form_layout.addRow(separator)
        
        self.endpoint_edit = QLineEdit()
        self.endpoint_edit.textChanged.connect(self.on_profile_data_changed)
        form_layout.addRow("Endpoint URL:", self.endpoint_edit)
        
        self.bucket_edit = QLineEdit()
        self.bucket_edit.textChanged.connect(self.on_profile_data_changed)
        form_layout.addRow("Bucket Name:", self.bucket_edit)
        
        self.access_key_edit = QLineEdit()
        self.access_key_edit.textChanged.connect(self.on_profile_data_changed)
        form_layout.addRow("Access Key:", self.access_key_edit)
        
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_key_edit.textChanged.connect(self.on_profile_data_changed)
        form_layout.addRow("Secret Key:", self.secret_key_edit)
        
        # Show password checkbox
        self.show_passwords_checkbox = QCheckBox("Show credentials")
        self.show_passwords_checkbox.stateChanged.connect(self.toggle_password_visibility)
        form_layout.addRow("", self.show_passwords_checkbox)
        
        layout.addLayout(form_layout)
        
        # Profile actions
        profile_buttons_layout = QHBoxLayout()
        
        self.save_profile_btn = QPushButton("Save Changes")
        self.save_profile_btn.clicked.connect(self.save_profile)
        self.save_profile_btn.setEnabled(False)
        profile_buttons_layout.addWidget(self.save_profile_btn)
        
        self.load_profile_btn = QPushButton("Load Profile")
        self.load_profile_btn.clicked.connect(self.load_profile)
        self.load_profile_btn.setEnabled(False)
        profile_buttons_layout.addWidget(self.load_profile_btn)
        
        self.test_connection_btn = QPushButton("Test Connection")
        self.test_connection_btn.clicked.connect(self.test_connection)
        self.test_connection_btn.setEnabled(False)
        profile_buttons_layout.addWidget(self.test_connection_btn)
        
        layout.addLayout(profile_buttons_layout)
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        return group
        
    def _create_button_layout(self) -> QHBoxLayout:
        """Create the bottom button layout"""
        layout = QHBoxLayout()
        layout.addStretch()
        
        # Import/Export buttons
        self.import_btn = QPushButton("Import Profile...")
        self.import_btn.clicked.connect(self.import_profile)
        layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("Export Selected...")
        self.export_btn.clicked.connect(self.export_profile)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)
        
        layout.addStretch()
        
        # Dialog buttons
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
        return layout
        
    def load_profiles(self):
        """Load profiles from file"""
        try:
            if os.path.exists(self.profiles_file):
                with open(self.profiles_file, 'r') as f:
                    self.profiles = json.load(f)
            else:
                self.profiles = {}
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load profiles: {e}")
            self.profiles = {}
    
    def save_profiles(self):
        """Save profiles to file"""
        try:
            with open(self.profiles_file, 'w') as f:
                json.dump(self.profiles, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save profiles: {e}")
    
    def update_profile_list(self):
        """Update the profile list widget"""
        self.profile_list.clear()
        
        for profile_name in sorted(self.profiles.keys()):
            item = QListWidgetItem(profile_name)
            self.profile_list.addItem(item)
    
    def on_profile_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Handle profile selection change"""
        if current is None:
            self.clear_profile_details()
            self.current_profile_name = None
            self._update_button_states()
            return
            
        profile_name = current.text()
        self.current_profile_name = profile_name
        
        if profile_name in self.profiles:
            profile_data = self.profiles[profile_name]
            self.load_profile_details(profile_data)
        
        self._update_button_states()
    
    def load_profile_details(self, profile_data: Dict[str, str]):
        """Load profile data into the detail form"""
        self.name_edit.setText(self.current_profile_name or "")
        self.endpoint_edit.setText(profile_data.get("endpoint_url", ""))
        self.bucket_edit.setText(profile_data.get("bucket_name", ""))
        self.access_key_edit.setText(profile_data.get("access_key", ""))
        self.secret_key_edit.setText(profile_data.get("secret_key", ""))
    
    def clear_profile_details(self):
        """Clear the profile detail form"""
        self.name_edit.clear()
        self.endpoint_edit.clear()
        self.bucket_edit.clear()
        self.access_key_edit.clear()
        self.secret_key_edit.clear()
    
    def on_profile_data_changed(self):
        """Handle changes to profile data"""
        self.save_profile_btn.setEnabled(True)
    
    def toggle_password_visibility(self, state):
        """Toggle visibility of credential fields"""
        if state == 2:  # Checked
            self.access_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.secret_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.access_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.secret_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
    
    def new_profile(self):
        """Create a new profile"""
        name, ok = QInputDialog.getText(
            self, "New Profile", "Enter profile name:",
            QLineEdit.EchoMode.Normal, "New Profile"
        )
        
        if not ok or not name.strip():
            return
            
        name = name.strip()
        
        if name in self.profiles:
            QMessageBox.warning(self, "Profile Exists", f"Profile '{name}' already exists.")
            return
        
        # Create empty profile
        self.profiles[name] = {
            "endpoint_url": "",
            "bucket_name": "",
            "access_key": "",
            "secret_key": ""
        }
        
        self.update_profile_list()
        
        # Select the new profile
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.text() == name:
                self.profile_list.setCurrentItem(item)
                break
    
    def duplicate_profile(self):
        """Duplicate the selected profile"""
        if not self.current_profile_name:
            return
            
        name, ok = QInputDialog.getText(
            self, "Duplicate Profile", "Enter new profile name:",
            QLineEdit.EchoMode.Normal, f"{self.current_profile_name} Copy"
        )
        
        if not ok or not name.strip():
            return
            
        name = name.strip()
        
        if name in self.profiles:
            QMessageBox.warning(self, "Profile Exists", f"Profile '{name}' already exists.")
            return
        
        # Copy current profile data
        current_data = self.profiles[self.current_profile_name].copy()
        self.profiles[name] = current_data
        
        self.update_profile_list()
        
        # Select the new profile
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.text() == name:
                self.profile_list.setCurrentItem(item)
                break
    
    def delete_profile(self):
        """Delete the selected profile"""
        if not self.current_profile_name:
            return
        
        reply = QMessageBox.question(
            self, "Delete Profile",
            f"Are you sure you want to delete profile '{self.current_profile_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.profiles[self.current_profile_name]
            self.update_profile_list()
            self.save_profiles()
    
    def save_profile(self):
        """Save the current profile data"""
        if not self.current_profile_name:
            return
        
        new_name = self.name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Invalid Name", "Profile name cannot be empty.")
            return
        
        profile_data = {
            "endpoint_url": self.endpoint_edit.text().strip(),
            "bucket_name": self.bucket_edit.text().strip(),
            "access_key": self.access_key_edit.text().strip(),
            "secret_key": self.secret_key_edit.text().strip()
        }
        
        # If name changed, we need to handle renaming
        if new_name != self.current_profile_name:
            if new_name in self.profiles:
                reply = QMessageBox.question(
                    self, "Profile Exists",
                    f"Profile '{new_name}' already exists. Overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Remove old profile
            del self.profiles[self.current_profile_name]
            self.current_profile_name = new_name
        
        # Save profile data
        self.profiles[new_name] = profile_data
        self.save_profiles()
        self.update_profile_list()
        
        # Select the saved profile
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.text() == new_name:
                self.profile_list.setCurrentItem(item)
                break
        
        self.save_profile_btn.setEnabled(False)
        QMessageBox.information(self, "Success", f"Profile '{new_name}' saved successfully.")
    
    def load_profile(self):
        """Load the selected profile into the main connection widget"""
        if not self.current_profile_name:
            return
        
        profile_data = self.profiles[self.current_profile_name]
        self.connection_widget.load_profile_data(profile_data)
        
        # Emit signal to update main window
        self.profile_selected.emit(self.current_profile_name)
        
        QMessageBox.information(self, "Success", f"Profile '{self.current_profile_name}' loaded.")
    
    def test_connection(self):
        """Test the connection with current profile data"""
        profile_data = {
            "endpoint_url": self.endpoint_edit.text().strip(),
            "bucket_name": self.bucket_edit.text().strip(),
            "access_key": self.access_key_edit.text().strip(),
            "secret_key": self.secret_key_edit.text().strip()
        }
        
        if not all(profile_data.values()):
            QMessageBox.warning(self, "Incomplete Data", "Please fill in all connection fields.")
            return
        
        # Disable the test button during testing
        self.test_connection_btn.setEnabled(False)
        self.test_connection_btn.setText("Testing...")
        
        # Create and show progress dialog
        self.progress_dialog = QProgressDialog("Testing connection...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowTitle("Connection Test")
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
        
        # Start the connection test worker
        self.test_worker = ConnectionTestWorker(
            profile_data["endpoint_url"],
            profile_data["access_key"],
            profile_data["secret_key"],
            profile_data["bucket_name"]
        )
        
        self.test_worker.test_complete.connect(self.on_test_complete)
        self.progress_dialog.canceled.connect(self.cancel_test)
        self.test_worker.finished.connect(self.on_test_finished)
        
        self.test_worker.start()
    
    def on_test_complete(self, success: bool, message: str):
        """Handle test completion"""
        self.progress_dialog.hide()
        
        if success:
            QMessageBox.information(self, "Connection Test - Success", message)
        else:
            QMessageBox.warning(self, "Connection Test - Failed", message)
    
    def cancel_test(self):
        """Cancel the connection test"""
        if hasattr(self, 'test_worker') and self.test_worker.isRunning():
            self.test_worker.terminate()
            self.test_worker.wait(1000)  # Wait up to 1 second for thread to finish
    
    def on_test_finished(self):
        """Handle test worker finished"""
        self.test_connection_btn.setEnabled(True)
        self.test_connection_btn.setText("Test Connection")
        self.progress_dialog.hide()
    
    def import_profile(self):
        """Import a profile from JSON file"""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Profile", "", "JSON Files (*.json)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r') as f:
                imported_data = json.load(f)
            
            # Ask for profile name
            name, ok = QInputDialog.getText(
                self, "Import Profile", "Enter name for imported profile:",
                QLineEdit.EchoMode.Normal, "Imported Profile"
            )
            
            if not ok or not name.strip():
                return
            
            name = name.strip()
            
            if name in self.profiles:
                reply = QMessageBox.question(
                    self, "Profile Exists",
                    f"Profile '{name}' already exists. Overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Validate imported data structure
            required_fields = ["endpoint_url", "bucket_name", "access_key", "secret_key"]
            if not all(field in imported_data for field in required_fields):
                QMessageBox.warning(self, "Invalid File", "The selected file does not contain valid profile data.")
                return
            
            self.profiles[name] = imported_data
            self.save_profiles()
            self.update_profile_list()
            
            QMessageBox.information(self, "Success", f"Profile '{name}' imported successfully.")
            
        except Exception as e:
            QMessageBox.warning(self, "Import Error", f"Could not import profile: {e}")
    
    def export_profile(self):
        """Export the selected profile to JSON file"""
        if not self.current_profile_name:
            return
        
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Profile", f"{self.current_profile_name}.json", 
            "JSON Files (*.json)"
        )
        
        if not filename:
            return
        
        try:
            profile_data = self.profiles[self.current_profile_name]
            with open(filename, 'w') as f:
                json.dump(profile_data, f, indent=2)
            
            QMessageBox.information(self, "Success", f"Profile exported to {filename}")
            
        except Exception as e:
            QMessageBox.warning(self, "Export Error", f"Could not export profile: {e}")
    
    def _update_button_states(self):
        """Update button enabled states based on current selection"""
        has_selection = self.current_profile_name is not None
        
        self.duplicate_profile_btn.setEnabled(has_selection)
        self.delete_profile_btn.setEnabled(has_selection)
        self.load_profile_btn.setEnabled(has_selection)
        self.test_connection_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)