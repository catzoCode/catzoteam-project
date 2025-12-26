# task_management/utils/email_parser.py

import re
from datetime import datetime


def parse_booking_email(subject, body):
    """
    Parse booking confirmation email
    
    Returns: dict with extracted booking data
    """
    
    data = {}
    
    # Extract Order ID
    order_match = re.search(r'#?(ORD-[\d-]+)', subject + body, re.IGNORECASE)
    if order_match:
        data['order_id'] = order_match.group(1)
    
    # Extract Customer Name
    name_match = re.search(r'Customer\s*Name:?\s*(.+?)(?:\n|Email|Phone)', body, re.IGNORECASE)
    if name_match:
        data['customer_name'] = name_match.group(1).strip()
    
    # Extract Phone
    phone_match = re.search(r'Phone:?\s*([\d\-\+]+)', body, re.IGNORECASE)
    if phone_match:
        data['customer_phone'] = phone_match.group(1).strip()
    
    # Extract Email
    email_match = re.search(r'Email:?\s*([\w\.-]+@[\w\.-]+\.\w+)', body, re.IGNORECASE)
    if email_match:
        data['customer_email'] = email_match.group(1).strip()
    
    # Extract IC Number
    ic_match = re.search(r'IC\s*(?:Number)?:?\s*([\d\-]+)', body, re.IGNORECASE)
    if ic_match:
        data['customer_ic'] = ic_match.group(1).strip()
    
    # Extract Cat Name
    cat_name_match = re.search(r'Cat\s*Name:?\s*(.+?)(?:\n|Breed|Age)', body, re.IGNORECASE)
    if cat_name_match:
        data['cat_name'] = cat_name_match.group(1).strip()
    
    # Extract Breed
    breed_match = re.search(r'Breed:?\s*(.+?)(?:\n|Age|Gender)', body, re.IGNORECASE)
    if breed_match:
        breed = breed_match.group(1).strip().lower()
        breed_map = {
            'persian': 'persian',
            'siamese': 'siamese',
            'maine coon': 'maine_coon',
            'british shorthair': 'british_shorthair',
            'british': 'british_shorthair',
            'ragdoll': 'ragdoll',
            'bengal': 'bengal',
            'mixed': 'mixed',
        }
        data['cat_breed'] = breed_map.get(breed, 'mixed')
    
    # Extract Age
    age_match = re.search(r'Age:?\s*(\d+)', body, re.IGNORECASE)
    if age_match:
        data['cat_age'] = int(age_match.group(1))
    
    # Extract Gender
    gender_match = re.search(r'Gender:?\s*(Male|Female)', body, re.IGNORECASE)
    if gender_match:
        data['cat_gender'] = gender_match.group(1).lower()
    
    # Extract Services (multiple lines)
    services = []
    service_section = re.search(
        r'SERVICES?\s*(?:REQUESTED)?:?\s*(.*?)(?=APPOINTMENT|Preferred|Branch|Special|$)',
        body,
        re.IGNORECASE | re.DOTALL
    )
    if service_section:
        service_text = service_section.group(1)
        service_lines = re.findall(r'[-*•]\s*(.+)', service_text)
        services = [s.strip() for s in service_lines if s.strip()]
    
    data['services'] = services
    
    # Extract Preferred Date
    date_match = re.search(r'Preferred\s*Date:?\s*(\d{4}-\d{2}-\d{2})', body, re.IGNORECASE)
    if date_match:
        data['preferred_date'] = date_match.group(1)
    
    # Extract Preferred Time
    time_match = re.search(r'Preferred\s*Time:?\s*(\d{1,2}:\d{2})', body, re.IGNORECASE)
    if time_match:
        data['preferred_time'] = time_match.group(1)
    
    # Extract Branch - UPDATED WITH CORRECT MAPPING
    branch_match = re.search(r'Branch:?\s*(.+?)(?:\n|$)', body, re.IGNORECASE)
    if branch_match:
        branch_name = branch_match.group(1).strip().lower()
        
        # Map email branch names to database branch codes
        branch_map = {
            # Damansara Perdana
            'damansara perdana': 'damansara_perdana',
            'damansara': 'damansara_perdana',
            'perdana': 'damansara_perdana',
            'dp': 'damansara_perdana',
            
            # Wangsa Maju
            'wangsa maju': 'wangsa_maju',
            'wangsa': 'wangsa_maju',
            'wm': 'wangsa_maju',
            
            # Shah Alam
            'shah alam': 'shah_alam',
            'shah': 'shah_alam',
            'sa': 'shah_alam',
            
            # Bangi
            'bangi': 'bangi',
            
            # Cheng, Melaka
            'cheng': 'cheng_melaka',
            'melaka': 'cheng_melaka',
            'cheng melaka': 'cheng_melaka',
            'malacca': 'cheng_melaka',
            
            # Johor Bahru
            'johor bahru': 'johor_bahru',
            'johor': 'johor_bahru',
            'jb': 'johor_bahru',
            
            # Seremban 2
            'seremban': 'seremban',
            'seremban 2': 'seremban',
            's2': 'seremban',
            
            # Seri Kembangan
            'seri kembangan': 'seri_kembangan',
            'kembangan': 'seri_kembangan',
            'sk': 'seri_kembangan',
            
            # USJ 21
            'usj 21': 'usj21',
            'usj21': 'usj21',
            'usj': 'usj21',
            'subang': 'usj21',
            'subang jaya': 'usj21',
            
            # Ipoh
            'ipoh': 'ipoh',
            
            # Legacy/Old names (in case Collar App uses old names)
            'petaling jaya': 'seri_kembangan',  # If PJ is now SK
            'pj': 'seri_kembangan',
        }
        
        mapped_branch = branch_map.get(branch_name)
        
        if mapped_branch:
            data['branch'] = mapped_branch
        else:
            # Log unmapped branch for debugging
            print(f"⚠️ Unknown branch name: '{branch_name}'")
            data['branch'] = None
    
    # Extract Special Notes
    notes_match = re.search(
        r'SPECIAL\s*NOTES?:?\s*(.+?)(?=---|$)',
        body,
        re.IGNORECASE | re.DOTALL
    )
    if notes_match:
        data['special_notes'] = notes_match.group(1).strip()
    
    return data