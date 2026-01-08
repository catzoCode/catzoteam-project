# registration_portal/ocr_utils.py
# SIMPLIFIED - Only extract Customer & Cat data

import re
from PIL import Image
import pytesseract
from django.conf import settings

def extract_text_from_image(image_file):
    """Extract text from uploaded image using Tesseract OCR"""
    try:
        img = Image.open(image_file)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        
        text = pytesseract.image_to_string(img, config='--psm 6')
        
        print(f"✓ OCR: Extracted {len(text)} characters")
        
        return text
    
    except Exception as e:
        print(f"✗ OCR Error: {str(e)}")
        raise


def parse_portal_collar_data(raw_text):
    """
    Parse ONLY Customer and Cat data from extracted text
    Based on Customer and Cat models only
    """
    
    data = {
        # ===== CUSTOMER MODEL FIELDS =====
        'name': '',              # Customer.name (required)
        'phone': '',             # Customer.phone (required)
        'email': '',             # Customer.email
        'ic_number': '',         # Customer.ic_number
        'address': '',           # Customer.address
        
        # ===== CAT MODEL FIELDS =====
        'cat_name': '',          # Cat.name (required)
        'breed': '',             # Cat.breed
        'age': '',               # Cat.age (in months)
        'gender': '',            # Cat.gender
        'color': '',             # Cat.color
        'weight': '',            # Cat.weight (kg)
        'vaccination_status': '', # Cat.vaccination_status
        'medical_notes': '',     # Cat.medical_notes
        'special_requirements': '', # Cat.special_requirements
        
        # ===== METADATA =====
        'raw_text': raw_text,
    }
    
    lines = raw_text.split('\n')
    
    # ============================================
    # EXTRACT CUSTOMER INFORMATION
    # ============================================
    
    # Customer Name
    for line in lines:
        if 'customer name' in line.lower() or ('name:' in line.lower() and 'cat' not in line.lower()):
            match = re.search(r'name[:\s]+([A-Z\s]+)', line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'\b(CUSTOMER|INFORMATION|NAME)\b', '', name, flags=re.IGNORECASE).strip()
                if len(name) > 2:
                    data['name'] = name.upper()
                    print(f"✓ Customer Name: {data['name']}")
                    break
    
    # Phone Number - Malaysian format (more flexible)
    for line in lines:
        if 'phone' in line.lower():
            # Try multiple patterns
            # Pattern 1: 012-3456789 or 012 3456789
            match = re.search(r'(\d{3}[-\s]?\d{7,8})', line)
            if not match:
                # Pattern 2: 0123456789 (no separator)
                match = re.search(r'(0\d{9,10})', line)
            if not match:
                # Pattern 3: Just any phone-like number after "Phone:"
                match = re.search(r'phone[:\s]+(\d[\d\s-]{8,})', line, re.IGNORECASE)
            
            if match:
                phone = match.group(1).replace(' ', '').replace('-', '')
                # Remove leading zeros and non-digits
                phone = re.sub(r'[^\d]', '', phone)
                # Ensure starts with 0 and has 10-11 digits
                if phone.startswith('0') and 10 <= len(phone) <= 11:
                    data['phone'] = f"{phone[:3]}-{phone[3:]}"
                    print(f"✓ Phone: {data['phone']}")
                    break
    
    # Email
    for line in lines:
        if 'email' in line.lower():
            match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
            if match:
                data['email'] = match.group(0).lower()
                print(f"✓ Email: {data['email']}")
                break
    
    # IC Number - Malaysian format: 123456-12-1234
    for line in lines:
        if 'ic' in line.lower() or 'nric' in line.lower():
            match = re.search(r'(\d{6}[-\s]?\d{2}[-\s]?\d{4})', line)
            if match:
                ic = match.group(1).replace(' ', '')
                if len(ic) == 12:
                    data['ic_number'] = f"{ic[:6]}-{ic[6:8]}-{ic[8:]}"
                else:
                    data['ic_number'] = ic
                print(f"✓ IC: {data['ic_number']}")
                break
    
    # Address - usually multi-line, look for keywords
    address_lines = []
    for i, line in enumerate(lines):
        if 'address' in line.lower():
            # Get lines after "address" keyword
            for j in range(i+1, min(i+4, len(lines))):
                addr_line = lines[j].strip()
                if addr_line and len(addr_line) > 5:
                    # Stop if we hit another section
                    if any(keyword in addr_line.lower() for keyword in ['cat', 'phone', 'email', 'ic', 'service']):
                        break
                    address_lines.append(addr_line)
            break
    
    if address_lines:
        data['address'] = ', '.join(address_lines)
        print(f"✓ Address: {data['address'][:50]}...")
    
    # ============================================
    # EXTRACT CAT INFORMATION
    # ============================================
    
    # Cat Name
    for line in lines:
        if 'cat name' in line.lower():
            match = re.search(r'name[:\s]+([A-Z\s]+)', line, re.IGNORECASE)
            if match:
                cat_name = match.group(1).strip()
                cat_name = re.sub(r'\b(CAT|INFORMATION|NAME)\b', '', cat_name, flags=re.IGNORECASE).strip()
                if len(cat_name) > 1:
                    data['cat_name'] = cat_name.upper()
                    print(f"✓ Cat Name: {data['cat_name']}")
                    break
    
    # Breed
    for line in lines:
        if 'breed' in line.lower():
            match = re.search(r'breed[:\s]+([A-Za-z\s]+)', line, re.IGNORECASE)
            if match:
                breed = match.group(1).strip()
                breed = re.sub(r'\b(BREED|CAT|INFORMATION)\b', '', breed, flags=re.IGNORECASE).strip()
                if len(breed) > 2:
                    data['breed'] = breed.title()
                    print(f"✓ Breed: {data['breed']}")
                    break
    
    # Age (in months)
    for line in lines:
        if 'age' in line.lower():
            match = re.search(r'age[:\s]+(\d+)', line, re.IGNORECASE)
            if match:
                data['age'] = match.group(1)
                print(f"✓ Age: {data['age']} months")
                break
    
    # Gender
    for line in lines:
        if 'gender' in line.lower():
            if 'female' in line.lower():
                data['gender'] = 'female'
            elif 'male' in line.lower():
                data['gender'] = 'male'
            if data['gender']:
                print(f"✓ Gender: {data['gender']}")
                break
    
    # Color
    for line in lines:
        if 'color' in line.lower() or 'colour' in line.lower():
            match = re.search(r'colou?r[:\s]+([A-Za-z\s]+)', line, re.IGNORECASE)
            if match:
                color = match.group(1).strip()
                color = re.sub(r'\b(COLOR|COLOUR|CAT)\b', '', color, flags=re.IGNORECASE).strip()
                if len(color) > 2:
                    data['color'] = color.title()
                    print(f"✓ Color: {data['color']}")
                    break
    
    # Weight (in kg)
    for line in lines:
        if 'weight' in line.lower():
            match = re.search(r'weight[:\s]+([\d.]+)', line, re.IGNORECASE)
            if match:
                data['weight'] = match.group(1)
                print(f"✓ Weight: {data['weight']} kg")
                break
    
    # Vaccination Status
    for line in lines:
        if 'vaccination' in line.lower() or 'vaccine' in line.lower():
            if 'up to date' in line.lower() or 'updated' in line.lower() or 'complete' in line.lower():
                data['vaccination_status'] = 'up_to_date'
            elif 'partial' in line.lower():
                data['vaccination_status'] = 'partial'
            elif 'none' in line.lower() or 'not vaccinated' in line.lower():
                data['vaccination_status'] = 'none'
            else:
                data['vaccination_status'] = 'unknown'
            
            if data['vaccination_status']:
                print(f"✓ Vaccination: {data['vaccination_status']}")
                break
    
    # Medical Notes - look for health, medical, allergies
    medical_keywords = ['medical', 'health', 'allerg', 'condition', 'illness', 'disease']
    medical_lines = []
    
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in medical_keywords):
            # Get this line and next few
            for j in range(i, min(i+3, len(lines))):
                med_line = lines[j].strip()
                if med_line and len(med_line) > 5:
                    # Clean up
                    for keyword in medical_keywords:
                        med_line = re.sub(rf'\b{keyword}\w*\b[:\s]*', '', med_line, flags=re.IGNORECASE)
                    if med_line.strip():
                        medical_lines.append(med_line.strip())
            break
    
    if medical_lines:
        data['medical_notes'] = ' '.join(medical_lines)
        print(f"✓ Medical Notes: {data['medical_notes'][:50]}...")
    
    # Special Requirements/Notes
    special_keywords = ['special', 'note', 'requirement', 'behavior', 'temperament']
    special_lines = []
    
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in special_keywords):
            # Get lines after keyword
            for j in range(i, min(i+3, len(lines))):
                spec_line = lines[j].strip()
                if spec_line and len(spec_line) > 5:
                    # Skip if it's another section header
                    if any(skip in spec_line.lower() for skip in ['customer', 'service', 'appointment']):
                        break
                    # Clean up
                    for keyword in special_keywords:
                        spec_line = re.sub(rf'\b{keyword}s?\b[:\s]*', '', spec_line, flags=re.IGNORECASE)
                    if spec_line.strip():
                        special_lines.append(spec_line.strip())
            break
    
    if special_lines:
        data['special_requirements'] = ' '.join(special_lines)
        print(f"✓ Special Requirements: {data['special_requirements'][:50]}...")
    
    return data


def validate_extracted_data(data):
    """
    Validate extracted data
    REQUIRED: name (customer), phone, cat_name
    OPTIONAL: Everything else
    """
    
    required_fields = {
        'name': 'Customer Name',
        'phone': 'Phone Number', 
        'cat_name': 'Cat Name'
    }
    
    errors = []
    warnings = []
    
    # Check required fields
    for field, label in required_fields.items():
        if not data.get(field):
            errors.append(f"❌ Missing REQUIRED: {label}")
    
    # Check optional fields
    optional_fields = {
        'email': 'Email',
        'ic_number': 'IC Number',
        'address': 'Address',
        'breed': 'Cat Breed',
        'age': 'Cat Age',
        'gender': 'Cat Gender',
        'color': 'Cat Color',
        'weight': 'Cat Weight',
        'vaccination_status': 'Vaccination Status',
        'medical_notes': 'Medical Notes',
        'special_requirements': 'Special Requirements'
    }
    
    for field, label in optional_fields.items():
        if not data.get(field):
            warnings.append(f"⚠️ Missing optional: {label}")
    
    # Calculate confidence
    total_fields = len(required_fields) + len(optional_fields)
    filled_fields = sum(1 for f in list(required_fields.keys()) + list(optional_fields.keys()) if data.get(f))
    
    confidence = filled_fields / total_fields
    
    # Boost confidence if all required fields present
    if all(data.get(f) for f in required_fields.keys()):
        confidence = max(confidence, 0.7)
    else:
        confidence = min(confidence, 0.5)
    
    is_valid = len(errors) == 0
    
    all_messages = errors + warnings
    
    print(f"\n{'='*50}")
    print(f"VALIDATION RESULTS:")
    print(f"Required Fields: {len([f for f in required_fields.keys() if data.get(f)])}/{len(required_fields)}")
    print(f"Optional Fields: {len([f for f in optional_fields.keys() if data.get(f)])}/{len(optional_fields)}")
    print(f"Confidence: {confidence:.1%}")
    print(f"Valid: {is_valid}")
    print(f"{'='*50}\n")
    
    return is_valid, confidence, all_messages