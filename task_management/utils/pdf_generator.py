from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import requests
from PIL import Image as PILImage
from datetime import datetime


def generate_closing_report_pdf(report):
    """
    Generate a professional PDF for a ClosingReport with embedded image
    
    Args:
        report: ClosingReport instance
        
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold',
        borderWidth=1,
        borderColor=colors.HexColor('#3b82f6'),
        borderPadding=5,
        backColor=colors.HexColor('#f0f9ff')
    )
    
    normal_style = styles['Normal']
    
    # =====================================
    # HEADER
    # =====================================
    elements.append(Paragraph("CATZONIA CAT HOTEL & GROOMING", title_style))
    elements.append(Paragraph("Daily Closing Report", heading_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # =====================================
    # REPORT INFORMATION
    # =====================================
    report_info_data = [
        ['Report ID:', report.report_id],
        ['Date:', report.date.strftime('%A, %B %d, %Y')],
        ['Branch:', report.get_branch_display()],
        ['Submitted By:', report.submitted_by.get_full_name()],
        ['Submitted At:', report.submitted_at.strftime('%Y-%m-%d %H:%M:%S')],
    ]
    
    report_info_table = Table(report_info_data, colWidths=[4*cm, 12*cm])
    report_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f9ff')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(report_info_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # =====================================
    # CUSTOMER & SERVICE COUNTS
    # =====================================
    elements.append(Paragraph("Customer & Service Counts", heading_style))
    
    customer_data = [
        ['Metric', 'Count'],
        ['Cat Grooming Today', str(report.grooming_count)],
        ['Boarded Rooms Today', str(report.boarding_count)],
        ['Total Customers', str(report.total_customers)],
    ]
    
    customer_table = Table(customer_data, colWidths=[10*cm, 6*cm])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(customer_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # =====================================
    # PAYMENT INFORMATION
    # =====================================
    elements.append(Paragraph("Payment Information", heading_style))
    
    payment_difference = abs(report.payment_record_amount - report.payment_receipt_amount)
    difference_color = colors.green if payment_difference == 0 else colors.red
    
    payment_data = [
        ['Description', 'Amount (RM)'],
        ['Total Payment Record (System)', f'RM {report.payment_record_amount:.2f}'],
        ['Total Payment Receipt (Actual)', f'RM {report.payment_receipt_amount:.2f}'],
        ['Difference', f'RM {payment_difference:.2f}'],
    ]
    
    payment_table = Table(payment_data, colWidths=[10*cm, 6*cm])
    payment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (1, 3), (1, 3), difference_color),
        ('FONTNAME', (1, 3), (1, 3), 'Helvetica-Bold'),
    ]))
    
    elements.append(payment_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # =====================================
    # COMPLIANCE CHECKS
    # =====================================
    elements.append(Paragraph("Compliance Checks", heading_style))
    
    compliance_data = [
        ['Question', 'Answer'],
        ['All customers paid through system?', 'Yes ✓' if report.compliance_all_paid_through_system else 'No ✗'],
        ['Any free services today?', 'Yes ✓' if report.compliance_free_services_today else 'No ✗'],
    ]
    
    compliance_table = Table(compliance_data, colWidths=[10*cm, 6*cm])
    compliance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(compliance_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # =====================================
    # NOTES
    # =====================================
    if report.notes:
        elements.append(Paragraph("Additional Notes", heading_style))
        notes_para = Paragraph(report.notes or 'None', normal_style)
        elements.append(notes_para)
        elements.append(Spacer(1, 0.8*cm))
    
    # =====================================
    # PAYMENT PROOF IMAGE
    # =====================================
    elements.append(Paragraph("Payment Proof Image", heading_style))
    
    try:
        # Download image from Cloudinary
        image_url = report.payment_proof_photo.url
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Open image and resize if needed
        img_buffer = BytesIO(response.content)
        pil_img = PILImage.open(img_buffer)
        
        # Resize to fit page width (max 16cm wide)
        max_width = 16 * cm
        max_height = 12 * cm
        
        img_width, img_height = pil_img.size
        aspect_ratio = img_height / img_width
        
        if img_width > max_width:
            new_width = max_width
            new_height = new_width * aspect_ratio
            if new_height > max_height:
                new_height = max_height
                new_width = new_height / aspect_ratio
        else:
            new_width = img_width
            new_height = img_height
        
        # Save resized image to buffer
        img_output = BytesIO()
        pil_img.save(img_output, format='JPEG', quality=85)
        img_output.seek(0)
        
        # Add image to PDF
        img = Image(img_output, width=new_width, height=new_height)
        elements.append(img)
        
    except Exception as e:
        error_text = f"Error loading image: {str(e)}"
        elements.append(Paragraph(error_text, normal_style))
    
    elements.append(Spacer(1, 1*cm))
    
    # =====================================
    # FOOTER
    # =====================================
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Catzonia Employee Management System"
    elements.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer