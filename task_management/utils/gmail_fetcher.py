# task_management/utils/gmail_fetcher.py

import imaplib
import email
from email.header import decode_header
from django.conf import settings


def fetch_booking_emails(max_emails=10):
    """
    Fetch unread booking emails from Gmail using IMAP
    
    Returns: list of dicts with email data
    """
    
    emails_data = []
    
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        
        # Login
        mail.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
        
        # Select inbox
        mail.select('inbox')
        
        # Search for unread emails with "Booking" in subject
        status, messages = mail.search(None, '(UNSEEN SUBJECT "Booking")')
        
        if status != 'OK':
            print("No emails found.")
            return emails_data
        
        # Get email IDs
        email_ids = messages[0].split()
        
        # Limit to max_emails
        email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids
        
        for email_id in email_ids:
            # Fetch email
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                continue
            
            # Parse email
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    # Parse message
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Get subject
                    subject_header = msg['Subject']
                    subject = ''
                    if subject_header:
                        decoded = decode_header(subject_header)
                        subject_parts = []
                        for content, encoding in decoded:
                            if isinstance(content, bytes):
                                if encoding:
                                    subject_parts.append(content.decode(encoding))
                                else:
                                    subject_parts.append(content.decode('utf-8', errors='ignore'))
                            else:
                                subject_parts.append(str(content))
                        subject = ''.join(subject_parts)
                    
                    # Get from
                    from_email = msg.get('From', '')
                    
                    # Get date
                    date_header = msg.get('Date', '')
                    
                    # Get body
                    body = ''
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == 'text/plain':
                                try:
                                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    break
                                except:
                                    pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except:
                            body = ''
                    
                    emails_data.append({
                        'email_id': email_id.decode(),
                        'subject': subject,
                        'from_email': from_email,
                        'date': date_header,
                        'body': body
                    })
        
        # Close connection
        mail.close()
        mail.logout()
        
    except imaplib.IMAP4.error as e:
        print(f"IMAP error: {e}")
    except Exception as e:
        print(f"Error fetching emails: {e}")
    
    return emails_data


def mark_email_as_read(email_id):
    """Mark an email as read after processing"""
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
        mail.select('inbox')
        
        # Mark as seen
        mail.store(email_id.encode(), '+FLAGS', '\\Seen')
        
        mail.close()
        mail.logout()
        
        return True
    except Exception as e:
        print(f"Error marking email as read: {e}")
        return False