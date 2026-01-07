# registration_portal/ocr_utils.py
"""
OCR utilities for extracting customer data from Portal Collar screenshots
"""

import pytesseract
from PIL import Image
import re
from io import BytesIO
import platform
import os

# Configure Tesseract path based on OS
if os.environ.get('RENDER') or platform.system() == 'Linux':
    # Production on Render (Linux)
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
    print("✓ OCR: Using Linux Tesseract path")
elif platform.system() == 'Windows':
    # Windows local development
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    print("✓ OCR: Using Windows Tesseract path")
elif platform.system() == 'Darwin':
    # Mac local development
    pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
    print("✓ OCR: Using Mac Tesseract path")
else:
    # Default fallback
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
    print("✓ OCR: Using default Tesseract path")


def extract_text_from_image(image_file):
    """
    Extract text from uploaded image using Tesseract OCR
    
    Args:
        image_file: Django UploadedFile object
    
    Returns:
        str: Extracted text or None if failed
    """
    try:
        # Read image from upload
        image = Image.open(image_file)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Extract text using pytesseract
        text = pytesseract.image_to_string(image)
        
        return text.strip()
    
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return None


def parse_portal_collar_data(text):
    """
    Parse extracted text to find customer information
    Looks for Malaysian phone numbers, IC numbers, names, etc.
    
    Args:
        text: Raw OCR text
    
    Returns:
        dict: Parsed customer data
    """
    
    data = {
        'name': '',
        'phone': '',
        'ic_number': '',
        'service': '',
        'date': '',
        'notes': '',
        'raw_text': text,
    }
    
    # Extract phone number (Malaysian format: 01X-XXXXXXX or 01XXXXXXXXX)
    phone_pattern = r'(?:(?:\+?6?0?1[0-9])|(?:01[0-9]))[\s-]?\d{7,8}'
    phone_matches = re.findall(phone_pattern, text)
    if phone_matches:
        # Clean phone number
        phone = phone_matches[0].replace('-', '').replace(' ', '')
        # Remove +6 or 6 prefix if exists
        phone = re.sub(r'^\+?6?', '', phone)
        # Ensure starts with 0
        if not phone.startswith('0'):
            phone = '0' + phone
        data['phone'] = phone
    
    # Extract IC number (XXXXXX-XX-XXXX)
    ic_pattern = r'\d{6}[-]?\d{2}[-]?\d{4}'
    ic_matches = re.findall(ic_pattern, text)
    if ic_matches:
        ic = ic_matches[0]
        # Format with dashes
        if '-' not in ic:
            ic = f"{ic[:6]}-{ic[6:8]}-{ic[8:]}"
        data['ic_number'] = ic
    
    # Extract name (looking for lines with capitalized words)
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        # Look for name patterns (2-4 words, mostly capitals)
        if len(line) > 5 and len(line) < 50:
            words = line.split()
            if 2 <= len(words) <= 4:
                # Check if mostly uppercase or title case
                if line.isupper() or line.istitle():
                    # Skip if it's a phone or IC
                    if not re.search(r'\d{6,}', line):
                        if not data['name']:  # Take first match
                            data['name'] = line.upper()
    
    # Extract date (common formats: DD/MM/YYYY, DD-MM-YYYY)
    date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
    date_matches = re.findall(date_pattern, text)
    if date_matches:
        data['date'] = date_matches[0]
    
    # Look for service keywords
    service_keywords = ['grooming', 'bath', 'shower', 'nail', 'trim', 'combo', 'treatment']
    for line in lines:
        line_lower = line.lower()
        for keyword in service_keywords:
            if keyword in line_lower:
                data['service'] = line.strip()
                break
        if data['service']:
            break
    
    # Store remaining text as notes (excluding what we've extracted)
    notes_lines = []
    for line in lines:
        line = line.strip()
        if line and line != data['name'] and line != data['phone'] and line != data['ic_number']:
            if len(line) > 10:  # Only meaningful lines
                notes_lines.append(line)
    
    data['notes'] = '\n'.join(notes_lines[:5])  # Max 5 lines of notes
    
    return data


def validate_extracted_data(data):
    """
    Validate extracted data and calculate confidence score
    
    Args:
        data: Parsed data dict
    
    Returns:
        tuple: (is_valid, confidence, errors)
    """
    
    errors = []
    confidence = 0.0
    
    # Check phone (most important)
    if data['phone']:
        if len(data['phone']) >= 10:
            confidence += 0.4
        else:
            errors.append('Phone number seems incomplete')
    else:
        errors.append('No phone number found')
    
    # Check name
    if data['name']:
        if len(data['name']) >= 3:
            confidence += 0.3
        else:
            errors.append('Name seems too short')
    else:
        errors.append('No name found')
    
    # Check IC (optional but adds confidence)
    if data['ic_number']:
        if len(data['ic_number']) >= 12:
            confidence += 0.2
        else:
            errors.append('IC number seems incomplete')
    
    # Check if we have any data at all
    if data['service'] or data['date']:
        confidence += 0.1
    
    is_valid = confidence >= 0.5
    
    return is_valid, confidence, errors


def clean_phone_number(phone):
    """
    Clean and format Malaysian phone number
    
    Args:
        phone: Raw phone string
    
    Returns:
        str: Cleaned phone number in format 01X-XXXXXXXX
    """
    
    if not phone:
        return ''
    
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    
    # Remove country code if present
    if digits.startswith('60'):
        digits = digits[2:]
    
    # Ensure starts with 0
    if not digits.startswith('0'):
        digits = '0' + digits
    
    # Format: 01X-XXXXXXX or 01X-XXXXXXXX
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:]}"
    elif len(digits) == 11:
        return f"{digits[:3]}-{digits[3:]}"
    else:
        return digits


def clean_ic_number(ic):
    """
    Clean and format Malaysian IC number
    
    Args:
        ic: Raw IC string
    
    Returns:
        str: Cleaned IC in format XXXXXX-XX-XXXX
    """
    
    if not ic:
        return ''
    
    # Remove all non-digits
    digits = re.sub(r'\D', '', ic)
    
    # Format: XXXXXX-XX-XXXX
    if len(digits) == 12:
        return f"{digits[:6]}-{digits[6:8]}-{digits[8:]}"
    else:
        return ic