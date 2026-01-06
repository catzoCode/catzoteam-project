# registration_portal/ocr_utils.py
# OCR utilities for extracting customer data from Portal Collar screenshots

import re
from PIL import Image
import pytesseract
from datetime import datetime



pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_text_from_image(image_file):
    """
    Extract text from uploaded image using Tesseract OCR
    
    Args:
        image_file: Django UploadedFile object
    
    Returns:
        str: Extracted text
    """
    try:
        # Open image
        image = Image.open(image_file)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(image, lang='eng')
        
        return text
    
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""


def parse_portal_collar_data(text):
    """
    Parse Portal Collar screenshot text and extract customer data
    
    Expected format:
    - Name: JOHN DOE
    - Phone: 0123456789 / +60123456789
    - IC: 123456-78-9012
    - Service: Grooming / Boarding / Spa
    - Date: 06/01/2026 or 2026-01-06
    
    Args:
        text: Extracted text from OCR
    
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
        'raw_text': text
    }
    
    try:
        # Clean text
        text = text.strip()
        
        # Extract Name (look for patterns like "Name:", "Nama:", "Customer:")
        name_patterns = [
            r'(?:Name|Nama|Customer)\s*[:\-]\s*([A-Z][A-Z\s]+)',
            r'(?:Name|Nama|Customer)\s+([A-Z][A-Z\s]+)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['name'] = match.group(1).strip()
                break
        
        # Extract Phone (Malaysian format: 01X-XXXXXXX or +601X-XXXXXXX)
        phone_patterns = [
            r'(?:Phone|Tel|HP|Mobile)\s*[:\-]?\s*(\+?6?0\d{8,10})',
            r'(\+?6?0\d{2}[\s\-]?\d{7,8})',
            r'(01\d[\s\-]?\d{7,8})',
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(1)
                # Clean phone number (remove spaces, dashes)
                phone = re.sub(r'[\s\-]', '', phone)
                # Add +60 if not present
                if phone.startswith('0'):
                    phone = '+6' + phone
                elif not phone.startswith('+'):
                    phone = '+' + phone
                data['phone'] = phone
                break
        
        # Extract IC Number (format: XXXXXX-XX-XXXX)
        ic_patterns = [
            r'(?:IC|NRIC|MyKad)\s*[:\-]?\s*(\d{6}[\s\-]?\d{2}[\s\-]?\d{4})',
            r'(\d{6}[\s\-]\d{2}[\s\-]\d{4})',
        ]
        for pattern in ic_patterns:
            match = re.search(pattern, text)
            if match:
                ic = match.group(1)
                # Clean IC (add dashes if not present)
                ic = re.sub(r'[\s\-]', '', ic)
                if len(ic) == 12:
                    ic = f"{ic[:6]}-{ic[6:8]}-{ic[8:]}"
                data['ic_number'] = ic
                break
        
        # Extract Service
        service_keywords = ['grooming', 'boarding', 'spa', 'bath', 'hotel', 'daycare']
        for keyword in service_keywords:
            if keyword.lower() in text.lower():
                data['service'] = keyword.capitalize()
                break
        
        # Extract Date (multiple formats)
        date_patterns = [
            r'(?:Date|Tarikh)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
            r'(\d{4}[\/\-]\d{2}[\/\-]\d{2})',
            r'(\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Try to parse date
                try:
                    # Try DD/MM/YYYY
                    if '/' in date_str or '-' in date_str:
                        separator = '/' if '/' in date_str else '-'
                        parts = date_str.split(separator)
                        if len(parts[0]) == 2:  # DD/MM/YYYY
                            date_obj = datetime.strptime(date_str, f'%d{separator}%m{separator}%Y')
                        else:  # YYYY-MM-DD
                            date_obj = datetime.strptime(date_str, f'%Y{separator}%m{separator}%d')
                        data['date'] = date_obj.strftime('%Y-%m-%d')
                except:
                    data['date'] = date_str
                break
        
        # Extract any additional notes (capture lines with "Note:" or "Remarks:")
        notes_match = re.search(r'(?:Note|Remarks|Notes)[:\-]?\s*(.+)', text, re.IGNORECASE)
        if notes_match:
            data['notes'] = notes_match.group(1).strip()
    
    except Exception as e:
        print(f"Parse Error: {e}")
    
    return data


def validate_extracted_data(data):
    """
    Validate extracted data and return confidence score
    
    Args:
        data: dict from parse_portal_collar_data
    
    Returns:
        tuple: (is_valid: bool, confidence: float, errors: list)
    """
    
    errors = []
    confidence_scores = []
    
    # Check name
    if data['name']:
        if len(data['name']) >= 3:
            confidence_scores.append(1.0)
        else:
            confidence_scores.append(0.5)
            errors.append("Name seems too short")
    else:
        confidence_scores.append(0.0)
        errors.append("Name not found")
    
    # Check phone
    if data['phone']:
        # Valid Malaysian phone
        if re.match(r'\+60\d{9,10}', data['phone']):
            confidence_scores.append(1.0)
        else:
            confidence_scores.append(0.5)
            errors.append("Phone format may be incorrect")
    else:
        confidence_scores.append(0.0)
        errors.append("Phone not found")
    
    # Check IC
    if data['ic_number']:
        # Valid IC format
        if re.match(r'\d{6}-\d{2}-\d{4}', data['ic_number']):
            confidence_scores.append(1.0)
        else:
            confidence_scores.append(0.5)
            errors.append("IC format may be incorrect")
    else:
        confidence_scores.append(0.3)  # IC is optional
    
    # Calculate overall confidence
    if confidence_scores:
        confidence = sum(confidence_scores) / len(confidence_scores)
    else:
        confidence = 0.0
    
    # Valid if at least name AND phone are found
    is_valid = bool(data['name'] and data['phone'])
    
    return is_valid, confidence, errors
