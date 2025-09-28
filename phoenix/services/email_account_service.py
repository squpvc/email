"""
Email account service for managing email accounts in the database.
"""
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError

from ..models.email import EmailAccount
from ..database import db_manager
from ..utils.encryption import encrypt, decrypt

logger = logging.getLogger(__name__)

class EmailAccountService:
    """Service for managing email accounts in the database."""
    
    @staticmethod
    async def create_account(
        email: str,
        password: str,
        display_name: Optional[str] = None,
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = 993,
        imap_ssl: bool = True,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = 587,
        smtp_ssl: bool = True,
        smtp_tls: bool = True,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        **kwargs
    ) -> Optional[EmailAccount]:
        """
        Create a new email account in the database.
        
        Args:
            email: Email address
            password: Email password (will be encrypted)
            display_name: Display name for the account
            imap_server: IMAP server address
            imap_port: IMAP server port
            imap_ssl: Whether to use SSL for IMAP
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            smtp_ssl: Whether to use SSL for SMTP
            smtp_tls: Whether to use STARTTLS for SMTP
            smtp_username: SMTP username (if different from email)
            smtp_password: SMTP password (if different from main password)
            **kwargs: Additional account attributes
            
        Returns:
            The created EmailAccount instance or None if creation failed
        """
        try:
            # Encrypt sensitive data
            encrypted_password = encrypt(password)
            encrypted_smtp_password = (
                encrypt(smtp_password) 
                if smtp_password and smtp_password != password 
                else encrypted_password
            )
            
            # Create account dictionary
            account_data = {
                'email': email.lower().strip(),
                'display_name': display_name,
                'imap_server': imap_server,
                'imap_port': imap_port,
                'imap_ssl': imap_ssl,
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'smtp_ssl': smtp_ssl,
                'smtp_tls': smtp_tls,
                'username': email.lower().strip(),  # Default to email if not provided
                'password': encrypted_password,
                'smtp_username': smtp_username or email.lower().strip(),
                'smtp_password': encrypted_smtp_password,
                **kwargs
            }
            
            # Create account in database
            async with db_manager.session() as session:
                account = EmailAccount(**account_data)
                session.add(account)
                await session.commit()
                await session.refresh(account)
                logger.info(f"Created email account: {email}")
                return account
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating email account {email}: {e}")
            return None
    
    @staticmethod
    async def update_account(
        account_id: str,
        **updates
    ) -> bool:
        """
        Update an existing email account.
        
        Args:
            account_id: ID of the account to update
            **updates: Fields to update
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Encrypt sensitive data if provided
            if 'password' in updates and updates['password']:
                updates['password'] = encrypt(updates['password'])
                
            if 'smtp_password' in updates and updates['smtp_password']:
                updates['smtp_password'] = encrypt(updates['smtp_password'])
            
            async with db_manager.session() as session:
                result = await session.execute(
                    update(EmailAccount)
                    .where(EmailAccount.id == account_id)
                    .values(**updates)
                )
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Updated email account: {account_id}")
                    return True
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating email account {account_id}: {e}")
            return False
    
    @staticmethod
    async def delete_account(account_id: str) -> bool:
        """
        Delete an email account by ID.
        
        Args:
            account_id: ID of the account to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            async with db_manager.session() as session:
                result = await session.execute(
                    delete(EmailAccount)
                    .where(EmailAccount.id == account_id)
                )
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Deleted email account: {account_id}")
                    return True
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"Error deleting email account {account_id}: {e}")
            return False
    
    @staticmethod
    async def get_account(account_id: str) -> Optional[EmailAccount]:
        """
        Get an email account by ID.
        
        Args:
            account_id: ID of the account to retrieve
            
        Returns:
            EmailAccount instance or None if not found
        """
        try:
            async with db_manager.session() as session:
                result = await session.execute(
                    select(EmailAccount)
                    .where(EmailAccount.id == account_id)
                )
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting email account {account_id}: {e}")
            return None
    
    @staticmethod
    async def get_all_accounts() -> List[EmailAccount]:
        """
        Get all email accounts.
        
        Returns:
            List of EmailAccount instances
        """
        try:
            async with db_manager.session() as session:
                result = await session.execute(
                    select(EmailAccount)
                    .order_by(EmailAccount.email)
                )
                return list(result.scalars().all())
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all email accounts: {e}")
            return []
    
    @staticmethod
    async def get_account_by_email(email: str) -> Optional[EmailAccount]:
        """
        Get an email account by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            EmailAccount instance or None if not found
        """
        try:
            async with db_manager.session() as session:
                result = await session.execute(
                    select(EmailAccount)
                    .where(EmailAccount.email == email.lower().strip())
                )
                return result.scalar_one_or_none()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting email account by email {email}: {e}")
            return None
    
    @staticmethod
    async def decrypt_password(encrypted_password: str) -> str:
        """
        Decrypt an encrypted password.
        
        Args:
            encrypted_password: Encrypted password string
            
        Returns:
            Decrypted password
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            return decrypt(encrypted_password)
        except Exception as e:
            logger.error(f"Error decrypting password: {e}")
            raise ValueError("Failed to decrypt password")

# Global instance for convenience
email_account_service = EmailAccountService()
