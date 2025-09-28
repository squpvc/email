"""
Outlook PST/OST file importer.

This module provides functionality to import emails from Outlook PST/OST files
into the Phoenix email system.
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator, Tuple
from datetime import datetime
import tempfile
import shutil

from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

# Try to import libpff, but make it optional
try:
    import pypff
    PFF_AVAILABLE = True
except ImportError:
    PFF_AVAILABLE = False

from ..models import Email, EmailAccount, EmailFolder
from ..models.email_management import (
    EmailCategory, EmailLabel, OutlookImport, OutlookImportMapping
)
from ..config import DATA_DIR

logger = logging.getLogger(__name__)

class OutlookImporter:
    """Class for importing emails from Outlook PST/OST files."""
    
    def __init__(self, db_session: Session, user_id: Optional[int] = None):
        """Initialize the Outlook importer."""
        if not PFF_AVAILABLE:
            raise ImportError("pypff library is required for Outlook import. Install with: pip install pypff-python")
        
        self.db = db_session
        self.user_id = user_id
        self.temp_dir = Path(tempfile.mkdtemp(prefix="phoenix_outlook_"))
        self.pff_file = None
        
    def __del__(self):
        """Clean up temporary files when the importer is destroyed."""
        self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up temporary files."""
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {e}")
    
    def open_file(self, file_path: str) -> bool:
        """Open a PST/OST file for importing."""
        try:
            self.pff_file = pypff.file()
            self.pff_file.open(file_path)
            self.root_folder = self.pff_file.get_root_folder()
            return True
        except Exception as e:
            logger.error(f"Error opening Outlook file {file_path}: {e}")
            return False
    
    def close(self) -> None:
        """Close the currently opened PST/OST file."""
        if self.pff_file:
            self.pff_file.close()
            self.pff_file = None
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze the PST/OST file and return statistics.
        
        Returns:
            Dictionary containing analysis results including folder structure and item counts.
        """
        if not self.pff_file:
            return {"error": "No file is currently open"}
        
        try:
            stats = {
                "total_folders": 0,
                "total_emails": 0,
                "folders": [],
                "path": self.pff_file.get_identifier_ascii_codepage()
            }
            
            # Recursively process folders
            def process_folder(folder, path=""):
                folder_name = folder.name if hasattr(folder, 'name') else "Root"
                current_path = f"{path}/{folder_name}" if path else folder_name
                
                # Count messages in this folder
                message_count = 0
                try:
                    message_count = folder.get_number_of_sub_messages()
                except Exception as e:
                    logger.debug(f"Could not get message count for {current_path}: {e}")
                
                # Add folder info
                folder_info = {
                    "name": folder_name,
                    "path": current_path,
                    "message_count": message_count,
                    "subfolders": []
                }
                
                stats["total_emails"] += message_count
                stats["total_folders"] += 1
                
                # Process subfolders
                try:
                    for subfolder in folder.sub_folders:
                        subfolder_info = process_folder(subfolder, current_path)
                        folder_info["subfolders"].append(subfolder_info)
                except Exception as e:
                    logger.debug(f"Could not process subfolders for {current_path}: {e}")
                
                return folder_info
            
            # Start processing from root
            root_info = process_folder(self.root_folder)
            stats["folders"].append(root_info)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error analyzing Outlook file: {e}")
            return {"error": str(e)}
    
    def import_emails(
        self,
        import_id: int,
        folder_mappings: List[Dict[str, Any]],
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Import emails based on folder mappings.
        
        Args:
            import_id: ID of the OutlookImport record
            folder_mappings: List of folder mappings with source and target info
            batch_size: Number of emails to process in each batch
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with import results
        """
        try:
            import_record = self.db.query(OutlookImport).get(import_id)
            if not import_record:
                return {"error": f"Import record {import_id} not found"}
            
            # Update import status
            import_record.status = "in_progress"
            import_record.started_at = datetime.utcnow()
            self.db.commit()
            
            # Process each folder mapping
            stats = {
                "total_emails": 0,
                "imported_emails": 0,
                "failed_emails": 0,
                "folders": {}
            }
            
            for mapping in folder_mappings:
                folder_path = mapping.get("source_path")
                category_id = mapping.get("category_id")
                label_id = mapping.get("label_id")
                
                if not folder_path:
                    continue
                
                # Find the folder in the PST/OST file
                folder = self._find_folder_by_path(folder_path)
                if not folder:
                    logger.warning(f"Folder not found: {folder_path}")
                    continue
                
                # Import messages from this folder
                folder_stats = self._import_folder_messages(
                    folder=folder,
                    import_record=import_record,
                    category_id=category_id,
                    label_id=label_id,
                    batch_size=batch_size,
                    progress_callback=progress_callback
                )
                
                # Update statistics
                stats["total_emails"] += folder_stats["total_emails"]
                stats["imported_emails"] += folder_stats["imported_emails"]
                stats["failed_emails"] += folder_stats["failed_emails"]
                stats["folders"][folder_path] = folder_stats
                
                # Update the mapping with the actual counts
                mapping_record = self.db.query(OutlookImportMapping).get(mapping["id"])
                if mapping_record:
                    mapping_record.item_count = folder_stats["imported_emails"]
                    self.db.commit()
            
            # Update import status
            import_record.status = "completed"
            import_record.completed_at = datetime.utcnow()
            import_record.stats = {
                "total_emails": stats["total_emails"],
                "imported_emails": stats["imported_emails"],
                "failed_emails": stats["failed_emails"]
            }
            self.db.commit()
            
            return {"success": True, "stats": stats}
            
        except Exception as e:
            logger.error(f"Error during import: {e}", exc_info=True)
            if import_record:
                import_record.status = "failed"
                import_record.error_message = str(e)
                self.db.commit()
            return {"error": str(e)}
    
    def _find_folder_by_path(self, folder_path: str):
        """Find a folder by its path in the PST/OST file."""
        if not folder_path or not self.pff_file:
            return None
            
        try:
            # Split the path into components
            path_parts = [p for p in folder_path.split('/') if p]
            if not path_parts:
                return self.root_folder
                
            # Start from the root folder
            current = self.root_folder
            
            # Navigate through the folder hierarchy
            for part in path_parts:
                found = False
                try:
                    for folder in current.sub_folders:
                        if folder.name == part:
                            current = folder
                            found = True
                            break
                    if not found:
                        return None
                except Exception:
                    return None
                    
            return current
            
        except Exception as e:
            logger.error(f"Error finding folder {folder_path}: {e}")
            return None
    
    def _import_folder_messages(
        self,
        folder,
        import_record: OutlookImport,
        category_id: Optional[int] = None,
        label_id: Optional[int] = None,
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, int]:
        """Import messages from a single folder."""
        stats = {
            "total_emails": 0,
            "imported_emails": 0,
            "failed_emails": 0,
            "errors": []
        }
        
        try:
            # Get all messages in this folder
            messages = []
            try:
                messages = list(folder.sub_messages)
            except Exception as e:
                logger.warning(f"Could not get messages from folder: {e}")
                stats["errors"].append(str(e))
                return stats
                
            stats["total_emails"] = len(messages)
            
            # Process messages in batches
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                
                for message in batch:
                    try:
                        # Convert the message to our Email model
                        email = self._convert_message_to_email(
                            message,
                            import_record.id,
                            category_id,
                            label_id
                        )
                        
                        # Save to database
                        self.db.add(email)
                        stats["imported_emails"] += 1
                        
                        # Call progress callback if provided
                        if progress_callback:
                            progress = (i + 1) / len(messages) * 100
                            progress_callback(progress)
                            
                    except Exception as e:
                        logger.error(f"Error importing message: {e}", exc_info=True)
                        stats["failed_emails"] += 1
                        stats["errors"].append(str(e))
                        continue
                
                # Commit after each batch
                try:
                    self.db.commit()
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Error committing batch: {e}")
                    stats["errors"].append(f"Batch commit error: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in _import_folder_messages: {e}", exc_info=True)
            stats["errors"].append(str(e))
            return stats
    
    def _convert_message_to_email(
        self,
        message,
        import_id: int,
        category_id: Optional[int] = None,
        label_id: Optional[int] = None
    ) -> Email:
        """Convert a pypff.Message object to our Email model."""
        # Extract basic message properties
        subject = getattr(message, 'subject', '(No subject)')
        sender_name = getattr(message, 'sender_name', '')
        sender_email = getattr(message, 'sender_email_address', '')
        received_time = getattr(message, 'delivery_time', None)
        
        # Create the email object
        email = Email(
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            received_at=received_time or datetime.utcnow(),
            import_id=import_id,
            # Add other fields as needed
        )
        
        # Set body content
        try:
            email.body_plain = message.plain_text_body or ""
            email.body_html = message.html_body or ""
        except Exception as e:
            logger.warning(f"Could not get message body: {e}")
            email.body_plain = "[Message body could not be extracted]"
        
        # Set thread ID if available
        try:
            email.thread_id = message.conversation_id
        except Exception:
            pass
        
        # Set flags
        try:
            email.is_read = bool(getattr(message, 'is_read', False))
            email.is_flagged = bool(getattr(message, 'is_flagged', False))
            email.has_attachments = bool(getattr(message, 'number_of_attachments', 0) > 0)
        except Exception as e:
            logger.warning(f"Could not set message flags: {e}")
        
        # Add category mapping if specified
        if category_id is not None:
            mapping = EmailCategoryMapping(
                email=email,
                category_id=category_id,
                label_id=label_id,
                is_user_confirmed=True,
                confidence=1.0,
                source="outlook_import"
            )
            self.db.add(mapping)
        
        return email


def create_outlook_import(
    db: Session,
    file_path: str,
    user_id: Optional[int] = None
) -> Tuple[Optional[OutlookImport], Optional[str]]:
    """
    Create a new Outlook import record.
    
    Args:
        db: Database session
        file_path: Path to the PST/OST file
        user_id: ID of the user performing the import
        
    Returns:
        Tuple of (OutlookImport instance, error_message)
    """
    try:
        # Check if file exists
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return None, "File does not exist"
        
        # Create import record
        import_record = OutlookImport(
            file_path=str(path.absolute()),
            file_size=path.stat().st_size,
            user_id=user_id,
            status="pending"
        )
        
        db.add(import_record)
        db.commit()
        
        return import_record, None
        
    except Exception as e:
        logger.error(f"Error creating Outlook import: {e}", exc_info=True)
        db.rollback()
        return None, str(e)


def get_outlook_import(db: Session, import_id: int) -> Optional[OutlookImport]:
    """Get an Outlook import record by ID."""
    return db.query(OutlookImport).get(import_id)


def list_outlook_imports(
    db: Session,
    user_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> List[OutlookImport]:
    """List Outlook import records."""
    query = db.query(OutlookImport)
    
    if user_id is not None:
        query = query.filter(OutlookImport.user_id == user_id)
    
    return query.order_by(OutlookImport.created_at.desc()).offset(offset).limit(limit).all()


def delete_outlook_import(db: Session, import_id: int) -> bool:
    """Delete an Outlook import record and its associated data."""
    try:
        import_record = db.query(OutlookImport).get(import_id)
        if not import_record:
            return False
            
        # Delete associated mappings
        db.query(OutlookImportMapping).filter(
            OutlookImportMapping.import_id == import_id
        ).delete(synchronize_session=False)
        
        # Delete the import record
        db.delete(import_record)
        db.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Error deleting Outlook import {import_id}: {e}")
        db.rollback()
        return False
