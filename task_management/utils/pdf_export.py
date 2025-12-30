from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
import requests
from PIL import Image as PILImage
from datetime import datetime


def generate_reports_summary_pdf(reports, filters=None):
    """
    Generate comprehensive PDF with all closing reports in table format
    
    Args:
        reports: QuerySet of ClosingReport objects
        filters: Dict of applied filters (branch, date_from, date_to)
        
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    
    # Use landscape for wider tables
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=20,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    # HEADER
    elements.append(Paragraph("CATZONIA CAT HOTEL & GROOMING", title_style))
    elements.append(Paragraph("Daily Closing Reports Summary", heading_style))
    
    # Filter info
    filter_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if filters:
        filter_parts = []
        if filters.get('branch'):
            filter_parts.append(f"Branch: {filters['branch']}")
        if filters.get('date_from'):
            filter_parts.append(f"From: {filters['date_from']}")
        if filters.get('date_to'):
            filter_parts.append(f"To: {filters['date_to']}")
        if filter_parts:
            filter_text += " | Filters: " + ", ".join(filter_parts)
    
    elements.append(Paragraph(filter_text, subtitle_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # SUMMARY STATISTICS
    if reports:
        total_revenue = sum(r.revenue_total for r in reports)
        total_customers = sum(r.total_customers for r in reports)
        balanced_count = sum(1 for r in reports if r.is_balanced)
        
        summary_data = [
            ['Total Reports', 'Total Revenue', 'Total Customers', 'Balanced Reports'],
            [
                str(len(reports)),
                f'RM {total_revenue:.2f}',
                str(total_customers),
                f'{balanced_count}/{len(reports)}'
            ]
        ]
        
        summary_table = Table(summary_data, colWidths=[4*cm, 5*cm, 4*cm, 4*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f0f9ff')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.8*cm))
    
    # DETAILED REPORTS TABLE
    elements.append(Paragraph("Detailed Reports", heading_style))
    
    if not reports:
        elements.append(Paragraph("No reports found for the selected filters.", subtitle_style))
    else:
        # Table headers
        table_data = [[
            'Report ID',
            'Date',
            'Branch',
            'Revenue\n(RM)',
            'Customers',
            'Balanced',
            'Compliance'
        ]]
        
        # Add data rows
        for report in reports:
            table_data.append([
                report.report_id,
                report.date.strftime('%d/%m/%Y'),
                report.get_branch_display(),
                f'{report.revenue_total:.2f}',
                str(report.total_customers),
                '✓' if report.is_balanced else '✗',
                '✓' if report.is_compliant else '✗'
            ])
        
        # Create table
        col_widths = [3*cm, 2.5*cm, 3.5*cm, 2.5*cm, 2.5*cm, 2*cm, 2.5*cm]
        reports_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Style table
        table_style = [
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),      # Report ID
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),    # Date
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),      # Branch
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),     # Revenue
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),    # Customers
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),    # Balanced
            ('ALIGN', (6, 1), (6, -1), 'CENTER'),    # Compliance
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]
        
        # Alternate row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.append(
                    ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8fafc'))
                )
        
        reports_table.setStyle(TableStyle(table_style))
        elements.append(reports_table)
    
    # PAGE BREAK before detailed reports
    if reports and len(reports) > 0:
        elements.append(PageBreak())
        elements.append(Paragraph("Detailed Individual Reports", title_style))
        elements.append(Spacer(1, 0.5*cm))
    
    # INDIVIDUAL REPORT DETAILS (One per page with image)
    for idx, report in enumerate(reports):
        if idx > 0:
            elements.append(PageBreak())
        
        # Report header
        report_title = f"{report.report_id} - {report.get_branch_display()} - {report.date.strftime('%B %d, %Y')}"
        elements.append(Paragraph(report_title, heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Report info in 2 columns
        info_data = [
            ['Submitted By:', report.submitted_by.username, 'Total Customers:', str(report.total_customers)],
            ['Grooming:', str(report.grooming_count), 'Boarding:', str(report.boarding_count)],
            ['Payment Record:', f'RM {report.payment_record_amount:.2f}', 'Payment Receipt:', f'RM {report.payment_receipt_amount:.2f}'],
            ['Balanced:', '✓ Yes' if report.is_balanced else '✗ No', 'Compliant:', '✓ Yes' if report.is_compliant else '✗ No'],
        ]
        
        info_table = Table(info_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f9ff')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f0f9ff')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # Payment proof image
        elements.append(Paragraph("Payment Proof:", heading_style))
        elements.append(Spacer(1, 0.2*cm))
        
        try:
            image_url = report.payment_proof_photo.url
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            img_buffer = BytesIO(response.content)
            pil_img = PILImage.open(img_buffer)
            
            # Resize to fit (landscape page)
            max_width = 12 * cm
            max_height = 8 * cm
            
            img_width, img_height = pil_img.size
            aspect_ratio = img_height / img_width
            
            if img_width > max_width or img_height > max_height:
                if img_width / max_width > img_height / max_height:
                    new_width = max_width
                    new_height = max_width * aspect_ratio
                else:
                    new_height = max_height
                    new_width = max_height / aspect_ratio
            else:
                new_width = img_width
                new_height = img_height
            
            img_output = BytesIO()
            pil_img.save(img_output, format='JPEG', quality=80)
            img_output.seek(0)
            
            img = Image(img_output, width=new_width, height=new_height)
            elements.append(img)
            
        except Exception as e:
            error_para = Paragraph(f"<i>Image unavailable: {str(e)}</i>", styles['Normal'])
            elements.append(error_para)
        
        # Notes if any
        if report.notes:
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph("Notes:", heading_style))
            notes_para = Paragraph(report.notes, styles['Normal'])
            elements.append(notes_para)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer