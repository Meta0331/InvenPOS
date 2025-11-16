# utils.py
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime
from io import BytesIO
from collections import defaultdict 

# Alternative enhanced receipt version
def generate_invoice_pdf(invoice, sold_items):
    """Generate PDF that looks exactly like a thermal receipt"""
    buffer = BytesIO()
    
    # Receipt paper size (80mm thermal paper)
    page_width = 80 * mm
    page_height = 400 * mm  # Will auto-adjust
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(page_width, page_height),
        rightMargin=3 * mm,
        leftMargin=3 * mm,
        topMargin=5 * mm,
        bottomMargin=5 * mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Receipt styles with monospace font
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        fontName='Courier-Bold',
        spaceAfter=4,
        spaceBefore=4
    )
    
    item_style = ParagraphStyle(
        'Item',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_LEFT,
        fontName='Courier',
        leftIndent=0,
        rightIndent=0
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        fontName='Courier',
        spaceAfter=3,
        spaceBefore=3
    )
    
    # Header Section
    elements.append(Paragraph("=" * 29, header_style))
    elements.append(Paragraph("STOCKSMART", header_style))
    elements.append(Paragraph("SCHOOL SUPPLIES", header_style))
    elements.append(Paragraph("=" * 29, header_style))
    elements.append(Paragraph("STORE: 01234", item_style))
    elements.append(Paragraph(f"DATE: {invoice.date_issued.strftime('%m/%d/%Y %I:%M%p')}", item_style))
    elements.append(Paragraph(f"TRANS#: {invoice.invoice_number}", item_style))
    elements.append(Paragraph(f"CASHIER: {invoice.staff_name}", item_style))
    elements.append(Paragraph(f"CUSTOMER: {invoice.customer_id}", item_style))
    elements.append(Paragraph("-" * 36, item_style))
    
    # Column Headers
    elements.append(Paragraph("QTY DESCRIPTION         AMOUNT", item_style))
    elements.append(Paragraph("-" * 36, item_style))
    
    # Items
    for item in sold_items:
        # Format for receipt display
        qty = str(item.quantity).rjust(3)
        desc = item.product_name.ljust(18)[:18]
        price = f" {item.total_price:7.2f}"
        
        elements.append(Paragraph(f"{qty} {desc} {price}", item_style))
        
        # Show unit price if quantity > 1
        if item.quantity > 1:
            elements.append(Paragraph(f"    @ {item.unit_price:.2f} each", item_style))
    
    elements.append(Paragraph("-" * 36, item_style))
    
    # Totals Section
    elements.append(Paragraph(f"SUB-TOTAL: {f' {invoice.subtotal:9.2f}'.rjust(25)}", item_style))
    
    if invoice.tax_rate:
        elements.append(Paragraph(f"TAX: {invoice.tax_rate.percentage}%{f' {invoice.tax_amount:9.2f}'.rjust(25)}", item_style))
    
    elements.append(Paragraph(f"TOTAL: {f' {invoice.total_amount:9.2f}'.rjust(29)}", item_style))
    elements.append(Paragraph("-" * 36, item_style))
    
    # Payment Section
    elements.append(Paragraph(f"CASH RECEIVED: {f' {invoice.cash_received:9.2f}'.rjust(21)}", item_style))
    elements.append(Paragraph(f"CHANGE: {f' {invoice.change:9.2f}'.rjust(28)}", item_style))
    elements.append(Paragraph("=" * 36, item_style))
    
    # Footer Section
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("THANK YOU FOR SHOPPING AT", footer_style))
    elements.append(Paragraph("STOCKAMART!", footer_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("** 7-DAY RETURN POLICY **", footer_style))
    elements.append(Paragraph("WITH ORIGINAL RECEIPT", footer_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("VISIT US AGAIN SOON!", footer_style))
    elements.append(Paragraph("=" * 36, footer_style))
    elements.append(Paragraph(f"REF#: {invoice.invoice_number}", footer_style))
    elements.append(Paragraph("TERMINAL: POS001", footer_style))
    elements.append(Paragraph(f"TIME: {invoice.date_issued.strftime('%H:%M:%S')}", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf





def generate_sales_report_pdf(invoices, filters=None):
    """Generate professional PDF sales report"""
    buffer = BytesIO()
    
    # Use A4 size for reports
    page_width = 210 * mm
    page_height = 297 * mm
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25 * mm,
        leftMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom professional styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#2E7D32'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.HexColor('#1B5E20'),
        fontName='Helvetica-Bold'
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#2E7D32'),
        fontName='Helvetica-Bold',
        leftIndent=0
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        textColor=colors.HexColor('#333333'),
        fontName='Helvetica'
    )
    
    highlight_style = ParagraphStyle(
        'Highlight',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        textColor=colors.HexColor('#1B5E20'),
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#E8F5E8'),
        borderPadding=8,
        borderColor=colors.HexColor('#C8E6C9'),
        borderWidth=1
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        spaceBefore=20,
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica-Oblique'
    )
    
    # Header Section
    elements.append(Paragraph("STOCKSMART", title_style))
    elements.append(Paragraph("SALES PERFORMANCE REPORT", subtitle_style))
    
    # Report Metadata
    elements.append(Paragraph(f"<b>Report Generated:</b> {timezone.now().strftime('%B %d, %Y at %I:%M %p')}", normal_style))
    
    # Filter Information
    if filters:
        filter_text = "<b>Report Filters:</b> "
        filter_parts = []
        
        if filters.get('date_from') and filters.get('date_to'):
            filter_parts.append(f"Period: {filters['date_from']} to {filters['date_to']}")
        elif filters.get('date_from'):
            filter_parts.append(f"From: {filters['date_from']}")
        elif filters.get('date_to'):
            filter_parts.append(f"To: {filters['date_to']}")
        
        if filters.get('cashier'):
            filter_parts.append(f"Cashier: {filters['cashier']}")
        
        if filters.get('customer_id'):
            filter_parts.append(f"Customer: {filters['customer_id']}")
        
        if filters.get('invoice_number'):
            filter_parts.append(f"Invoice: {filters['invoice_number']}")
        
        filter_text += " • ".join(filter_parts) if filter_parts else "All Records"
        elements.append(Paragraph(filter_text, normal_style))
    
    elements.append(Spacer(1, 25))
    
    # Executive Summary Section
    elements.append(Paragraph("EXECUTIVE SUMMARY", section_header_style))
    
    # Calculate key metrics
    total_sales = sum(invoice.total_amount for invoice in invoices)
    total_transactions = len(invoices)
    average_sale = total_sales / total_transactions if total_transactions > 0 else 0
    
    # Summary in a professional layout
    summary_data = [
        [f"P {total_sales:,.2f}", "Total Revenue"],
        [f"{total_transactions}", "Transactions Processed"],
        [f"P {average_sale:,.2f}", "Average Transaction Value"],
    ]
    
    # Create a grid layout for summary
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, -1), 20),
        ('RIGHTPADDING', (0, 0), (0, -1), 20),
        ('LEFTPADDING', (1, 0), (1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (0, -1), 16),
        ('FONTSIZE', (1, 0), (1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E7D32')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#666666')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 25))
    
    # Sales Breakdown Section
    if invoices:
        elements.append(Paragraph("SALES BREAKDOWN", section_header_style))
        
        # Group by date for trend analysis
        from collections import defaultdict
        daily_sales = defaultdict(float)
        cashier_performance = defaultdict(lambda: {'sales': 0, 'transactions': 0})
        
        for invoice in invoices:
            date_str = invoice.date_issued.strftime('%Y-%m-%d')
            daily_sales[date_str] += float(invoice.total_amount)
            cashier_performance[invoice.staff_name]['sales'] += float(invoice.total_amount)
            cashier_performance[invoice.staff_name]['transactions'] += 1
        
        # Top performing days
        if daily_sales:
            elements.append(Paragraph("<b>Top Performing Days:</b>", normal_style))
            top_days = sorted(daily_sales.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for date, amount in top_days:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                elements.append(Paragraph(
                    f"• {date_obj.strftime('%B %d, %Y')}: <b>P{amount:,.2f}</b>", 
                    normal_style
                ))
        
        
        elements.append(Spacer(1, 15))
        
        # Cashier Performance
        if cashier_performance:
            elements.append(Paragraph("<b>Cashier Performance:</b>", normal_style))
            sorted_cashiers = sorted(cashier_performance.items(), key=lambda x: x[1]['sales'], reverse=True)
            
            for cashier, data in sorted_cashiers:
                avg_sale = data['sales'] / data['transactions'] if data['transactions'] > 0 else 0
                elements.append(Paragraph(
                    f"• {cashier}: {data['transactions']} transactions, P{data['sales']:,.2f} total (P{avg_sale:,.2f} avg)", 
                    normal_style
                ))
        
        elements.append(Spacer(1, 25))
        
        # Recent Transactions Section
        elements.append(Paragraph("RECENT TRANSACTIONS", section_header_style))
        
        # Show last 10 transactions
        recent_invoices = invoices[:10]
        for i, invoice in enumerate(recent_invoices, 1):
            transaction_text = f"""
            <b>{invoice.invoice_number}</b> • {invoice.date_issued.strftime('%b %d, %Y %I:%M %p')}<br/>
            Customer: {invoice.customer_id} • Cashier: {invoice.staff_name}<br/>
            Amount: <font color="#2E7D32"><b>P {invoice.total_amount:,.2f}</b></font> • Items: {invoice.sold_items.count()}
            """
            
            # Alternate background colors for readability
            if i % 2 == 0:
                bg_color = colors.HexColor('#F8F9FA')
            else:
                bg_color = colors.HexColor('#FFFFFF')
            
            transaction_table = Table([[Paragraph(transaction_text, normal_style)]], 
                                    colWidths=[6*inch])
            transaction_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
                ('PADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(transaction_table)
        
        # Show "more transactions" note if there are more
        if len(invoices) > 10:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(
                f"<i>... and {len(invoices) - 10} more transactions</i>", 
                footer_style
            ))
    
    else:
        # No data message
        elements.append(Paragraph("No sales data available for the selected period.", normal_style))
        elements.append(Paragraph("Please adjust your filters or check your data.", normal_style))
    
    elements.append(Spacer(1, 25))
    

      # Highest Product Sold Section
    if invoices:
        from collections import defaultdict

        product_sales = defaultdict(int)

        # Loop through all invoices and count quantities of sold products
        for invoice in invoices:
            for item in invoice.sold_items.all():
                product_sales[item.product_name] += item.quantity

        if product_sales:
            elements.append(Paragraph("TOP SELLING PRODUCTS", section_header_style))

            # Sort products by quantity sold, descending
            sorted_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)
            top_products = sorted_products[:5]  # Top 5 bestsellers

            for product, qty in top_products:
                elements.append(Paragraph(f"• {product}: <b>{qty}</b> sold", normal_style))

            # Add small note if there are many products
            if len(product_sales) > 5:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph(
                    f"<i>... and {len(product_sales) - 5} more products.</i>",
                    footer_style
                ))

        elements.append(Spacer(1, 25))


    # Performance Insights
    if invoices and total_transactions > 1:
        elements.append(Paragraph("PERFORMANCE INSIGHTS", section_header_style))
        
        # Calculate some insights
        max_sale = max(invoice.total_amount for invoice in invoices)
        min_sale = min(invoice.total_amount for invoice in invoices)
        
        insights = [
            f"• <b>Highest single transaction:</b> P{max_sale:,.2f}",
            f"• <b>Average transaction value:</b> P{average_sale:,.2f}",
            f"• <b>Total processing volume:</b> {total_transactions} transactions",
        ]
        
        if len(daily_sales) > 1:
            best_day = max(daily_sales.items(), key=lambda x: x[1])
            best_day_date = datetime.strptime(best_day[0], '%Y-%m-%d')
            insights.append(f"• <b>Best performing day:</b> {best_day_date.strftime('%B %d')} (P{best_day[1]:,.2f})")
        
        for insight in insights:
            elements.append(Paragraph(insight, normal_style))
    
    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Confidential Business Document • Generated by StockSmart POS", footer_style))
    elements.append(Paragraph(f"Page 1 of 1 • Report ID: SR-{timezone.now().strftime('%Y%m%d-%H%M')}", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf







def generate_purchase_report_pdf(purchase_orders, filters=None):
    """Generate professional PDF purchase report"""
    buffer = BytesIO()
    
    # Use A4 size for reports
    page_width = 210 * mm
    page_height = 297 * mm
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25 * mm,
        leftMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom professional styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#2E7D32'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=30,
        textColor=colors.HexColor('#1B5E20'),
        fontName='Helvetica-Bold'
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#2E7D32'),
        fontName='Helvetica-Bold',
        leftIndent=0
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        textColor=colors.HexColor('#333333'),
        fontName='Helvetica'
    )
    
    highlight_style = ParagraphStyle(
        'Highlight',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        textColor=colors.HexColor('#1B5E20'),
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#E8F5E8'),
        borderPadding=8,
        borderColor=colors.HexColor('#C8E6C9'),
        borderWidth=1
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        spaceBefore=20,
        textColor=colors.HexColor('#666666'),
        fontName='Helvetica-Oblique'
    )
    
    # Header Section
    elements.append(Paragraph("STOCKSMART", title_style))
    elements.append(Paragraph("PURCHASE MANAGEMENT REPORT", subtitle_style))
    
    # Report Metadata
    elements.append(Paragraph(f"<b>Report Generated:</b> {timezone.now().strftime('%B %d, %Y at %I:%M %p')}", normal_style))
    
    # Filter Information
    if filters:
        filter_text = "<b>Report Filters:</b> "
        filter_parts = []
        
        if filters.get('date_from') and filters.get('date_to'):
            filter_parts.append(f"Period: {filters['date_from']} to {filters['date_to']}")
        elif filters.get('date_from'):
            filter_parts.append(f"From: {filters['date_from']}")
        elif filters.get('date_to'):
            filter_parts.append(f"To: {filters['date_to']}")
        
        if filters.get('supplier'):
            filter_parts.append(f"Supplier: {filters['supplier']}")
        
        if filters.get('search'):
            filter_parts.append(f"Search: {filters['search']}")
        
        filter_text += " • ".join(filter_parts) if filter_parts else "All Received Orders"
        elements.append(Paragraph(filter_text, normal_style))
    
    elements.append(Spacer(1, 25))
    
    # Executive Summary Section
    elements.append(Paragraph("EXECUTIVE SUMMARY", section_header_style))
    
    # Calculate key metrics
    total_purchases = sum(po.total_cost for po in purchase_orders)
    total_orders = len(purchase_orders)
    average_purchase = total_purchases / total_orders if total_orders > 0 else 0
    
    # Count total items purchased
    total_items = sum(po.purchaseitem_set.count() for po in purchase_orders)
    
    # Summary in a professional layout
    summary_data = [
        [f"P {total_purchases:,.2f}", "Total Purchases"],
        [f"{total_orders}", "Purchase Orders"],
        [f"P {average_purchase:,.2f}", "Average Order Value"],
        [f"{total_items}", "Total Items Purchased"],
    ]
    
    # Create a grid layout for summary
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, -1), 20),
        ('RIGHTPADDING', (0, 0), (0, -1), 20),
        ('LEFTPADDING', (1, 0), (1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (0, -1), 16),
        ('FONTSIZE', (1, 0), (1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E7D32')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#666666')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 25))
    
    # Purchase Analysis Section
    if purchase_orders:
        elements.append(Paragraph("PURCHASE ANALYSIS", section_header_style))
        
        # Group by date for trend analysis
        daily_purchases = defaultdict(float)
        supplier_analysis = defaultdict(lambda: {'purchases': 0, 'orders': 0, 'items': 0})
        
        for po in purchase_orders:
            date_str = po.date_created.strftime('%Y-%m-%d')
            daily_purchases[date_str] += float(po.total_cost)
            supplier_analysis[po.supplier_name]['purchases'] += float(po.total_cost)
            supplier_analysis[po.supplier_name]['orders'] += 1
            supplier_analysis[po.supplier_name]['items'] += po.purchaseitem_set.count()
        
        # Top purchasing days
        if daily_purchases:
            elements.append(Paragraph("<b>Top Purchasing Days:</b>", normal_style))
            top_days = sorted(daily_purchases.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for date, amount in top_days:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                elements.append(Paragraph(
                    f"• {date_obj.strftime('%B %d, %Y')}: <b>P{amount:,.2f}</b>", 
                    normal_style
                ))
        
        elements.append(Spacer(1, 15))
        
        # Supplier Performance
        if supplier_analysis:
            elements.append(Paragraph("<b>Supplier Analysis:</b>", normal_style))
            sorted_suppliers = sorted(supplier_analysis.items(), key=lambda x: x[1]['purchases'], reverse=True)
            
            for supplier, data in sorted_suppliers:
                avg_order = data['purchases'] / data['orders'] if data['orders'] > 0 else 0
                elements.append(Paragraph(
                    f"• {supplier}: {data['orders']} orders, {data['items']} items, P{data['purchases']:,.2f} total (P{avg_order:,.2f} avg)", 
                    normal_style
                ))
        
        elements.append(Spacer(1, 25))
        
        # Recent Purchases Section
        elements.append(Paragraph("RECENT PURCHASE ORDERS", section_header_style))
        
        # Show last 10 purchase orders
        recent_orders = purchase_orders[:10]
        for i, po in enumerate(recent_orders, 1):
            # Get item details
            items_text = ", ".join([f"{item.product_name} (x{item.quantity})" for item in po.purchaseitem_set.all()[:3]])
            if po.purchaseitem_set.count() > 3:
                items_text += f" ... and {po.purchaseitem_set.count() - 3} more items"
            
            purchase_text = f"""
            <b>PO #{po.id}</b> • {po.date_created.strftime('%b %d, %Y')}<br/>
            Supplier: {po.supplier_name} • Items: {po.purchaseitem_set.count()}<br/>
            Total: <font color="#2E7D32"><b>P {po.total_cost:,.2f}</b></font><br/>
            Products: {items_text}
            """
            
            # Alternate background colors for readability
            if i % 2 == 0:
                bg_color = colors.HexColor('#F8F9FA')
            else:
                bg_color = colors.HexColor('#FFFFFF')
            
            purchase_table = Table([[Paragraph(purchase_text, normal_style)]], 
                                 colWidths=[6*inch])
            purchase_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
                ('PADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(purchase_table)
        
        # Show "more orders" note if there are more
        if len(purchase_orders) > 10:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(
                f"<i>... and {len(purchase_orders) - 10} more purchase orders</i>", 
                footer_style
            ))
    
    else:
        # No data message
        elements.append(Paragraph("No purchase data available for the selected period.", normal_style))
        elements.append(Paragraph("Please adjust your filters or check your data.", normal_style))
    
    elements.append(Spacer(1, 25))
    
    # Top Purchased Products Section
    if purchase_orders:
        product_purchases = defaultdict(lambda: {'quantity': 0, 'total_cost': 0})
        
        # Aggregate product purchases across all orders
        for po in purchase_orders:
            for item in po.purchaseitem_set.all():
                product_purchases[item.product_name]['quantity'] += item.quantity
                product_purchases[item.product_name]['total_cost'] += item.quantity * item.cost_per_unit
        
        if product_purchases:
            elements.append(Paragraph("MOST PURCHASED PRODUCTS", section_header_style))
            
            # Sort products by quantity purchased, descending
            sorted_products = sorted(product_purchases.items(), key=lambda x: x[1]['quantity'], reverse=True)
            top_products = sorted_products[:5]  # Top 5 most purchased
            
            for product, data in top_products:
                avg_cost = data['total_cost'] / data['quantity'] if data['quantity'] > 0 else 0
                elements.append(Paragraph(
                    f"• {product}: <b>{data['quantity']}</b> units (P{data['total_cost']:,.2f} total, P{avg_cost:,.2f} avg)", 
                    normal_style
                ))
            
            # Add small note if there are many products
            if len(product_purchases) > 5:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph(
                    f"<i>... and {len(product_purchases) - 5} more products.</i>",
                    footer_style
                ))
        
        elements.append(Spacer(1, 25))
    
    # Inventory Insights
    if purchase_orders and total_orders > 1:
        elements.append(Paragraph("INVENTORY INSIGHTS", section_header_style))
        
        # Calculate some insights
        max_order = max(po.total_cost for po in purchase_orders)
        min_order = min(po.total_cost for po in purchase_orders)
        
        insights = [
            f"• <b>Largest single purchase:</b> P{max_order:,.2f}",
            f"• <b>Average purchase value:</b> P{average_purchase:,.2f}",
            f"• <b>Total items restocked:</b> {total_items} units",
            f"• <b>Average items per order:</b> {total_items/total_orders:.1f}",
        ]
        
        if len(daily_purchases) > 1:
            best_day = max(daily_purchases.items(), key=lambda x: x[1])
            best_day_date = datetime.strptime(best_day[0], '%Y-%m-%d')
            insights.append(f"• <b>Highest spending day:</b> {best_day_date.strftime('%B %d')} (P{best_day[1]:,.2f})")
        
        for insight in insights:
            elements.append(Paragraph(insight, normal_style))
    
    # Cost Analysis
    if purchase_orders:
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("COST DISTRIBUTION", section_header_style))
        
        # Categorize orders by size
        small_orders = [po for po in purchase_orders if po.total_cost < 1000]
        medium_orders = [po for po in purchase_orders if 1000 <= po.total_cost < 5000]
        large_orders = [po for po in purchase_orders if po.total_cost >= 5000]
        
        cost_distribution = [
            f"• <b>Small orders</b> (< P1,000): {len(small_orders)} orders",
            f"• <b>Medium orders</b> (P1,000 - P5,000): {len(medium_orders)} orders", 
            f"• <b>Large orders</b> (≥ P5,000): {len(large_orders)} orders",
        ]
        
        for distribution in cost_distribution:
            elements.append(Paragraph(distribution, normal_style))
    
    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Confidential Business Document • Generated by StockSmart POS", footer_style))
    elements.append(Paragraph(f"Page 1 of 1 • Report ID: PR-{timezone.now().strftime('%Y%m%d-%H%M')}", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf