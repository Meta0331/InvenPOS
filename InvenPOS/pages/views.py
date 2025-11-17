from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import Product, Category, Supplier, Invoice, TaxRate, SoldItem, PurchaseOrder, PurchaseItem
from .utils import generate_invoice_pdf
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q, F, DecimalField, ExpressionWrapper
from .utils import generate_sales_report_pdf, generate_purchase_report_pdf # Make sure this is imported
from django.db import transaction
from reportlab.lib.units import inch

from django.contrib.auth.hashers import make_password

# ADD THESE IMPORTS FOR AGGREGATION AND DATE HANDLING
from django.db.models import Sum, Count  # ← ADD THIS LINE
from datetime import datetime, timedelta  # ← ADD THIS LINE
# ---------------- AUTHENTICATION ----------------

@login_required
def home(request):
    # Redirect based on user type
    if request.user.is_superuser:
        return redirect('pages:admin_dashboard')
    elif request.user.is_staff:
        return redirect('pages:cashier_dashboard')
    else:
        return redirect('pages:cashier_dashboard')


def authView(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST or None)
        if form.is_valid():
            form.save()
            return redirect('pages:login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {"form": form})


def custom_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)

            # Redirect based on user type
            if user.is_superuser:
                return redirect('pages:admin_dashboard')
            elif user.is_staff:
                return redirect('pages:cashier_dashboard')
            else:
                return redirect('pages:cashier_dashboard')
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {"form": form})


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('pages:cashier_dashboard')
    return render(request, 'admin/admin_dashboard.html', {})


@login_required
def cashier_dashboard(request):
    return render(request, 'cashier/cashier_dashboard.html', {})


# ---------------- PRODUCT & CATEGORY MANAGEMENT ----------------

@login_required
def products(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    products = Product.objects.all().order_by('id')

    # --- FILTER BY SEARCH QUERY ---
    if query:
        products = products.filter(product_name__icontains=query)

    # --- FILTER BY CATEGORY ---
    selected_category = None
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
            selected_category = category
            products = products.filter(product_category=category.name)
        except Category.DoesNotExist:
            pass

    categories = Category.objects.all()
    suppliers = Supplier.objects.all()  # ✅ Fetch suppliers here

    # --- PAGINATION ---
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    products_page = paginator.get_page(page_number)

    current_page = products_page.number
    total_pages = paginator.num_pages
    start = max(1, current_page - 2)
    end = min(total_pages, current_page + 2)
    page_range = range(start, end + 1)

    # --- ADD CATEGORY FUNCTIONALITY ---
    if request.method == "POST" and 'add_category' in request.POST:
        category_name = request.POST.get('category_name')
        if category_name:
            Category.objects.get_or_create(name=category_name)
        return redirect('pages:products')

    return render(request, 'admin/products.html', {
        'products': products_page,
        'paginator': paginator,
        'page_range': page_range,
        'categories': categories,
        'selected_category': selected_category,
        'suppliers': suppliers,  # ✅ Pass to template
    })




@login_required
def add_product(request):
    if request.method == "POST":
        name = request.POST.get('name')
        price = request.POST.get('price')
        quantity = request.POST.get('quantity')
        category_id = request.POST.get('category')
        image = request.FILES.get('image')

        # Find category object if exists
        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                category = None

        Product.objects.create(
            product_name=name,
            product_price=price,
            product_quantity=quantity,
            product_category=category.name if category else '',
            product_img=image
        )
        return redirect('pages:products')
    return redirect('pages:products')


@login_required
def edit_product(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == "POST":
        product.product_name = request.POST.get('name')
        product.product_price = request.POST.get('price')
        product.product_quantity = request.POST.get('quantity')

        category_id = request.POST.get('category')
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                product.product_category = category.name
            except Category.DoesNotExist:
                pass

        if request.FILES.get('image'):
            product.product_img = request.FILES.get('image')

        product.save()
        return redirect('pages:products')

    return render(request, 'admin/edit_product.html', {'product': product})


@login_required
def delete_product(request, id):
    product = get_object_or_404(Product, id=id)
    product.delete()
    return redirect('pages:products')

def users(request):
    return render(request, 'admin/users.html')


# ✅ Add Category
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Category.objects.create(name=name)
            messages.success(request, f'Category "{name}" added successfully!')
    return redirect('pages:products')


# ✅ Edit Category (POST only — no missing template)
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        new_name = request.POST.get('name')
        if new_name:
            category.name = new_name
            category.save()
            messages.success(request, f'Category renamed to "{new_name}" successfully!')
    return redirect('pages:products')


# ✅ Delete Category (and all its products)
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    # Delete all products with this category
    Product.objects.filter(product_category=category.name).delete()
    category.delete()
    messages.warning(request, f'Category "{category.name}" and all its products have been deleted!')
    return redirect('pages:products')


def suppliers(request):
    suppliers = Supplier.objects.all()
    total_suppliers = suppliers.count()
    active_suppliers = suppliers.filter(is_active=True).count()
    return render(request, 'admin/suppliers.html', {
        'suppliers': suppliers,
        'total_suppliers': total_suppliers,
        'active_suppliers': active_suppliers
    })


def add_supplier(request):
    if request.method == 'POST':
        Supplier.objects.create(
            name=request.POST['name'],
            contact=request.POST.get('contact', ''),
            email=request.POST.get('email', ''),
            address=request.POST.get('address', ''),
            company=request.POST.get('company', '')
        )
        return redirect('pages:suppliers')
    return redirect('pages:suppliers')

def edit_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    if request.method == 'POST':
        supplier.name = request.POST['name']
        supplier.contact = request.POST.get('contact', '')
        supplier.email = request.POST.get('email', '')
        supplier.address = request.POST.get('address', '')
        supplier.company = request.POST.get('company', '')
        supplier.save()
        return redirect('pages:suppliers')
    return redirect('pages:suppliers')

def delete_supplier(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    supplier.delete()
    return redirect('pages:suppliers')


@login_required
def restock_product(request, id):
    product = get_object_or_404(Product, id=id)
    suppliers = Supplier.objects.all()  # ✅ Fetch all suppliers

    if request.method == "POST":
        try:
            restock_qty = int(request.POST.get("restock_qty", 0))
            supplier_id = request.POST.get("supplier")

            if restock_qty > 0:
                product.product_quantity += restock_qty
                product.save()

                supplier = None
                if supplier_id:
                    try:
                        supplier = Supplier.objects.get(id=supplier_id)
                    except Supplier.DoesNotExist:
                        supplier = None

                # ✅ Save to Restock table
                from .models import Restock
                Restock.objects.create(
                    product=product,
                    supplier=supplier,
                    quantity_added=restock_qty
                )

                messages.success(
                    request,
                    f"{product.product_name} restocked by {restock_qty} units."
                )
            else:
                messages.error(request, "Please enter a valid quantity.")
        except ValueError:
            messages.error(request, "Invalid quantity entered.")

        return redirect('pages:products')

    # ✅ If GET request, render restock modal or page
    return render(request, 'admin/restock_product.html', {
        'product': product,
        'suppliers': suppliers
    })

def cashier_dashboard(request):
    category = request.GET.get('category')
    if category:
        products = Product.objects.filter(product_category=category)
    else:
        products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, 'cashier/cashier_dashboard.html', {
        'products': products,
        'categories': categories
    })

@login_required
def payment_page(request):
    # This view just renders the payment template
    # The actual payment processing is handled by JavaScript
    return render(request, 'cashier/payment.html')





@login_required
def invoices_management(request):
    invoices = Invoice.objects.all().order_by('-created_at')
    tax_rates = TaxRate.objects.all().order_by('name')
    return render(request, 'admin/invoices.html', {
        'invoices': invoices,
        'tax_rates': tax_rates,
    })

@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    tax_rates = TaxRate.objects.filter(is_active=True)
    return render(request, 'admin/invoice_print.html', {
        'invoice': invoice,
        'tax_rates': tax_rates
    })


@login_required
def invoice_update(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    tax_rates = TaxRate.objects.filter(is_active=True)

    if request.method == "POST":
        tax_rate_id = request.POST.get("tax_rate")
        if tax_rate_id:
            invoice.tax_rate = TaxRate.objects.get(id=tax_rate_id)
        else:
            invoice.tax_rate = None
        invoice.update_total()
        messages.success(request, "Invoice updated with new tax.")
        return redirect("pages:invoice_detail", invoice_id=invoice.id)

    return render(request, "admin/invoice_edit.html", {
        "invoice": invoice,
        "tax_rates": tax_rates,
    })


@login_required
def invoice_form(request):
    tax_rates = TaxRate.objects.filter(is_active=True)
    return render(request, 'admin/invoice_form.html', {'tax_rates': tax_rates})


def tax_create_inline(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        percentage = request.POST.get('percentage')

        if not name or not percentage:
            messages.error(request, '❌ Please fill in all fields.')
            return redirect(request.META.get('HTTP_REFERER', 'pages:invoice_form'))

        try:
            percentage = float(percentage)
            TaxRate.objects.create(name=name, percentage=percentage, is_active=True)
            messages.success(request, f'✅ Tax "{name}" ({percentage}%) added successfully!')
        except ValueError:
            messages.error(request, '❌ Invalid percentage value. Please enter a valid number.')

        return redirect(request.META.get('HTTP_REFERER', 'pages:invoice_form'))


def tax_update_inline(request, pk):
    tax = get_object_or_404(TaxRate, pk=pk)
    if request.method == 'POST':
        tax.name = request.POST.get('name')
        tax.percentage = request.POST.get('percentage')
        tax.save()
        messages.success(request, 'Tax updated successfully!')
    return redirect(request.META.get('HTTP_REFERER', 'pages:invoice_form'))


def tax_delete_inline(request, pk):
    tax = get_object_or_404(TaxRate, pk=pk)
    tax.delete()
    messages.success(request, 'Tax deleted successfully!')
    return redirect(request.META.get('HTTP_REFERER', 'pages:invoice_form'))


@csrf_exempt
@require_POST
@login_required  # Add login required decorator
def create_invoice(request):
    try:
        data = json.loads(request.body)
        
        # Get the default active tax rate
        tax_rate = TaxRate.objects.filter(is_active=True).first()
        
        # Use the actual logged-in user's information
        staff_name = f"{request.user.first_name} {request.user.last_name}".strip()
        if not staff_name:
            staff_name = request.user.username
        
        # Create invoice with actual user info
        invoice = Invoice(
            customer_id=data['customer_id'],
            subtotal=data['subtotal'],
            cash_received=data['cash_received'],
            change=data['change'],
            staff_name=staff_name,  # Use actual user info instead of hardcoded "Cashier Staff"
            tax_rate=tax_rate,
            created_by=request.user  # Store the actual user object
        )
        invoice.save()
        
        # Create sold items and update product quantities
        for item_data in data['sold_items']:
            try:
                product = Product.objects.get(id=item_data['product_id'])
                
                # Check if enough stock is available
                if product.product_quantity < item_data['quantity']:
                    invoice.delete()
                    return JsonResponse({
                        'success': False,
                        'error': f'Not enough stock for {product.product_name}. Available: {product.product_quantity}, Requested: {item_data["quantity"]}'
                    }, status=400)
                
                # Update product quantity
                product.product_quantity -= item_data['quantity']
                product.save()
                
            except Product.DoesNotExist:
                invoice.delete()
                return JsonResponse({
                    'success': False,
                    'error': f'Product with ID {item_data["product_id"]} does not exist'
                }, status=400)
            
            sold_item = SoldItem(
                invoice=invoice,
                product=product,
                product_name=item_data['product_name'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['total_price']
            )
            sold_item.save()
        
        # Get the sold items for the response
        sold_items = SoldItem.objects.filter(invoice=invoice)
        
        return JsonResponse({
            'success': True,
            'invoice_number': invoice.invoice_number,
            'customer_id': invoice.customer_id,
            'total_amount': float(invoice.total_amount),
            'tax_amount': float(invoice.tax_amount),
            'tax_rate_name': invoice.tax_rate.name if invoice.tax_rate else 'No Tax',
            'tax_rate_percentage': float(invoice.tax_rate.percentage) if invoice.tax_rate else 0,
            'invoice_id': invoice.id,
            'staff_name': staff_name,  # Return the actual staff name for confirmation
            'message': 'Invoice created successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def download_invoice_pdf(request, invoice_id):
    """Download PDF for a specific invoice"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        sold_items = SoldItem.objects.filter(invoice=invoice)
        
        # Generate PDF
        pdf_content = generate_invoice_pdf(invoice, sold_items)
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def print_invoice_pdf(request, invoice_id):
    """View PDF for a specific invoice (open in browser)"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        sold_items = SoldItem.objects.filter(invoice=invoice)
        
        # Generate PDF
        pdf_content = generate_invoice_pdf(invoice, sold_items)
        
        # Create HTTP response with PDF
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="invoice_{invoice.invoice_number}.pdf"'
        
        return response
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def get_default_tax_rate(request):
    """API to get the default tax rate that will be applied automatically"""
    tax_rate = TaxRate.objects.filter(is_active=True).first()
    
    if tax_rate:
        tax_data = {
            'id': tax_rate.id,
            'name': tax_rate.name,
            'percentage': float(tax_rate.percentage),
            'display_name': f"{tax_rate.name} ({tax_rate.percentage}%)"
        }
    else:
        tax_data = None
    
    return JsonResponse({
        'success': True,
        'tax_rate': tax_data
    })

# SALES MANAGEMENT
def sales_list(request):
    sales = Invoice.objects.all()

    # 🔍 Search by invoice or customer
    query = request.GET.get("q")
    if query:
        sales = sales.filter(
            Q(invoice_number__icontains=query) |
            Q(customer_id__icontains=query)
        )

    # 👨‍💼 Filter by staff (using full name)
    cashier = request.GET.get("cashier")
    if cashier:
        sales = sales.filter(staff_name__iexact=cashier)

    # 📅 Sort by date
    date_order = request.GET.get("date_order")
    if date_order == "asc":
        sales = sales.order_by("date_issued")
    elif date_order == "desc":
        sales = sales.order_by("-date_issued")

    # Get all cashiers with full names
    cashiers_list = []
    for user in User.objects.filter(is_staff=False, is_superuser=False):
        full_name = f"{user.first_name} {user.last_name}".strip()
        if not full_name:
            full_name = user.username  # Fallback to username if no name
        cashiers_list.append({
            'username': user.username,
            'full_name': full_name
        })

    # Remove duplicates and sort by full name
    unique_cashiers = {}
    for cashier in cashiers_list:
        unique_cashiers[cashier['full_name']] = cashier
    
    cashiers = sorted(unique_cashiers.values(), key=lambda x: x['full_name'])

    return render(request, "admin/sales_list.html", {
        "sales": sales,
        "cashiers": cashiers,
    })


def sales_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    sold_items = invoice.sold_items.all()
    return render(request, 'admin/sales_detail.html', {'invoice': invoice, 'sold_items': sold_items})

@login_required
def sales_edit(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    sold_items = SoldItem.objects.filter(invoice=invoice)
    staff_list = User.objects.filter(is_staff=False, is_superuser=False)  # show only staff users

    if request.method == 'POST':
        # Update invoice details
        invoice.staff_name = request.POST.get('staff_name')
        invoice.cash_received = request.POST.get('cash_received')
        invoice.change = request.POST.get('change')
        invoice.date_issued = request.POST.get('date_issued') or invoice.date_issued
        invoice.save()

        # Update sold items
        for item in sold_items:
            qty = request.POST.get(f'quantity_{item.id}')
            price = request.POST.get(f'unit_price_{item.id}')
            if qty and price:
                item.quantity = int(qty)
                item.unit_price = float(price)
                item.total_price = item.quantity * item.unit_price
                item.save()

        messages.success(request, 'Invoice updated successfully!')
        return redirect('pages:sales_list')

    return render(request, 'admin/sales_edit.html', {
        'invoice': invoice,
        'sold_items': sold_items,
        'staff_list': staff_list,
    })
def sales_delete(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice.delete()  
    messages.success(request, 'Sale record deleted successfully!')
    return redirect('pages:sales_list')





@login_required
def sales_reports(request):
    # Start with all invoices
    invoices = Invoice.objects.all().order_by('-date_issued')
    
    # Get filter inputs and clean them
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    cashier = request.GET.get('cashier', '').strip()
    customer_id = request.GET.get('customer_id', '').strip()
    invoice_number = request.GET.get('invoice_number', '').strip()
    
    # Convert "None" strings to empty strings
    if date_from == 'None': date_from = ''
    if date_to == 'None': date_to = ''
    if cashier == 'None': cashier = ''
    if customer_id == 'None': customer_id = ''
    if invoice_number == 'None': invoice_number = ''
    
    # Apply filters only if they have actual values
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            invoices = invoices.filter(date_issued__date__gte=date_from_obj.date())
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            invoices = invoices.filter(date_issued__date__lte=date_to_obj.date())
        except ValueError:
            pass

    if cashier:
        invoices = invoices.filter(staff_name__iexact=cashier)
    
    if customer_id:
        invoices = invoices.filter(customer_id__icontains=customer_id)
    
    if invoice_number:
        invoices = invoices.filter(invoice_number__icontains=invoice_number)

    # Calculate statistics
    total_sales = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_transactions = invoices.count()
    average_sale = total_sales / total_transactions if total_transactions > 0 else 0
    
    # Get distinct cashiers for dropdown
    cashiers = Invoice.objects.values_list('staff_name', flat=True).distinct()

    return render(request, 'admin/sales_reports.html', {
        'invoices': invoices,
        'total_sales': total_sales,
        'total_transactions': total_transactions,
        'average_sale': average_sale,
        'cashiers': cashiers,
        'date_from': date_from if date_from else None,
        'date_to': date_to if date_to else None,
        'cashier': cashier if cashier else None,
        'customer_id': customer_id if customer_id else None,
        'invoice_number': invoice_number if invoice_number else None,
    })


@login_required
def print_sales_report(request):
    """Generate PDF sales report based on current filters"""
    # Get the same filters as sales_reports view
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    cashier = request.GET.get('cashier')
    customer_id = request.GET.get('customer_id')
    invoice_number = request.GET.get('invoice_number')
    
    # Apply the same filtering logic
    invoices = Invoice.objects.all().order_by('-date_issued')
    
    filters_applied = {}
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            invoices = invoices.filter(date_issued__date__gte=date_from_obj)
            filters_applied['date_from'] = date_from
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            invoices = invoices.filter(date_issued__date__lte=date_to_obj)
            filters_applied['date_to'] = date_to
        except ValueError:
            pass
    
    if cashier:
        invoices = invoices.filter(staff_name__icontains=cashier)
        filters_applied['cashier'] = cashier
    
    if customer_id:
        invoices = invoices.filter(customer_id__icontains=customer_id)
        filters_applied['customer_id'] = customer_id
    
    if invoice_number:
        invoices = invoices.filter(invoice_number__icontains=invoice_number)
        filters_applied['invoice_number'] = invoice_number
    
    try:
        # Generate PDF
        pdf_content = generate_sales_report_pdf(invoices, filters_applied)
        
        # Create HTTP response with PDF - CHANGED TO INLINE
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="sales_report.pdf"'  # Changed to inline
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error generating report: {str(e)}')
        return redirect('sales_reports')
    






def purchase_management(request):
    suppliers = Supplier.objects.all()
    products = Product.objects.all()
    
    # Start with all purchase orders
    purchase_orders = PurchaseOrder.objects.all()
    
    # Apply search filter
    search_query = request.GET.get('q')
    if search_query:
        purchase_orders = purchase_orders.filter(
            Q(id__icontains=search_query) | 
            Q(supplier_name__icontains=search_query)
        )
    
    # Apply supplier filter
    supplier_filter = request.GET.get('supplier')
    if supplier_filter:
        purchase_orders = purchase_orders.filter(supplier_name=supplier_filter)
    
    # Apply status filter
    status_filter = request.GET.get('status')
    if status_filter:
        purchase_orders = purchase_orders.filter(status=status_filter)
    
    # Apply date ordering
    date_order = request.GET.get('date_order')
    if date_order == 'asc':
        purchase_orders = purchase_orders.order_by('date_created')
    elif date_order == 'desc':
        purchase_orders = purchase_orders.order_by('-date_created')
    else:
        purchase_orders = purchase_orders.order_by('-date_created')

    return render(request, 'admin/purchase_management.html', {
        'suppliers': suppliers,
        'products': products,
        'purchase_orders': purchase_orders
    })

@csrf_exempt
def create_purchase_order(request):
    if request.method == 'POST':
        try:
            supplier_id = request.POST.get('supplier')
            expected_date = request.POST.get('expected_date')
            remarks = request.POST.get('remarks', '')
            
            # Get product data (arrays)
            product_ids = request.POST.getlist('product[]')
            quantities = request.POST.getlist('quantity[]')
            costs = request.POST.getlist('cost[]')
            
            # Debug logging
            print(f"Supplier ID: {supplier_id}")
            print(f"Expected Date: {expected_date}")
            print(f"Remarks: {remarks}")
            print(f"Product IDs: {product_ids}")
            print(f"Quantities: {quantities}")
            print(f"Costs: {costs}")
            
            if not supplier_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Supplier is required.'
                })
            
            if not expected_date:
                return JsonResponse({
                    'success': False,
                    'message': 'Expected delivery date is required.'
                })
            
            if not product_ids or len(product_ids) == 0:
                return JsonResponse({
                    'success': False,
                    'message': 'At least one product is required.'
                })
            
            # Use transaction to ensure data consistency
            with transaction.atomic():
                # Get supplier
                try:
                    supplier = Supplier.objects.get(id=supplier_id)
                except Supplier.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Selected supplier does not exist.'
                    })
                
                # Create the purchase order - using exact field names from your model
                purchase_order = PurchaseOrder.objects.create(
                    supplier_name=supplier.name,  # Using supplier.name based on your template
                    expected_date=expected_date,
                    status='Pending',
                    total_cost=0  # Will be calculated below
                    # Note: remarks field doesn't exist in your model, so we're not saving it
                )
                
                # Calculate total cost and create purchase items
                total_cost = 0
                for i in range(len(product_ids)):
                    product_id = product_ids[i]
                    quantity = int(quantities[i]) if quantities[i] else 0
                    cost = float(costs[i]) if costs[i] else 0
                    
                    if quantity <= 0 or cost <= 0:
                        continue
                    
                    # Find the product
                    try:
                        product = Product.objects.get(id=product_id)
                        
                        # Create purchase item - using exact field names from your model
                        PurchaseItem.objects.create(
                            purchase_order=purchase_order,
                            product_name=product.product_name,  # Using product_name field
                            quantity=quantity,
                            cost_per_unit=cost  # Using cost_per_unit field
                        )
                        
                        total_cost += quantity * cost
                        
                    except Product.DoesNotExist:
                        # If product not found, delete the purchase order and return error
                        purchase_order.delete()
                        return JsonResponse({
                            'success': False,
                            'message': f'Selected product does not exist.'
                        })
                
                # Update total cost
                purchase_order.total_cost = total_cost
                purchase_order.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Purchase Order #{purchase_order.id} created successfully!',
                'purchase_order_id': purchase_order.id
            })
            
        except Exception as e:
            import traceback
            print(f"Error details: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'message': f'Error creating purchase order: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

def mark_received(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    po.status = 'Received'
    po.save()
    messages.success(request, f'Purchase Order #{pk} marked as received.')
    return redirect('pages:purchase_management')

def view_purchase(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    items = PurchaseItem.objects.filter(purchase_order=po)  # Use filter instead of purchaseitem_set
    return render(request, 'view_purchase.html', {'po': po, 'items': items})

def cancel_purchase(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if po.status == 'Pending':
        po.status = 'Cancelled'
        po.save()
        messages.success(request, f'Purchase Order #{pk} has been cancelled.')
    else:
        messages.error(request, f'Only pending orders can be cancelled.')
    return redirect('pages:purchase_management')


def purchase_reports(request):
    # Only include received orders for reports
    purchase_orders = PurchaseOrder.objects.filter(status='Received')
    
    # Apply filters
    search = request.GET.get('search')
    if search:
        purchase_orders = purchase_orders.filter(
            Q(id__icontains=search) | 
            Q(supplier_name__icontains=search)
        )
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Fix date filtering - use date__range for proper date comparison
    if date_from and date_to:
        # Convert to datetime for proper range filtering
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            purchase_orders = purchase_orders.filter(
                date_created__range=[start_date, end_date]
            )
        except ValueError:
            # Handle invalid date formats
            pass
    elif date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            purchase_orders = purchase_orders.filter(date_created__gte=start_date)
        except ValueError:
            pass
    elif date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            purchase_orders = purchase_orders.filter(date_created__lte=end_date)
        except ValueError:
            pass
    
    supplier = request.GET.get('supplier')
    if supplier:
        purchase_orders = purchase_orders.filter(supplier_name=supplier)
    
    # Calculate statistics
    total_purchases = sum(po.total_cost for po in purchase_orders)
    total_orders = purchase_orders.count()
    average_purchase = total_purchases / total_orders if total_orders > 0 else 0
    
    # Get unique suppliers for filter dropdown
    suppliers = PurchaseOrder.objects.filter(status='Received').values_list('supplier_name', flat=True).distinct()
    
    context = {
        'purchase_orders': purchase_orders,
        'total_purchases': total_purchases,
        'total_orders': total_orders,
        'average_purchase': average_purchase,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'supplier': supplier,
        'suppliers': suppliers,
    }
    
    return render(request, 'admin/purchase_reports.html', context)


def print_purchase_report(request):
    """Generate PDF purchase report based on filters"""
    # Get filtered purchase orders (only received)
    purchase_orders = PurchaseOrder.objects.filter(status='Received')
    
    # Apply the same filters as in purchase_reports view
    search = request.GET.get('search')
    if search:
        purchase_orders = purchase_orders.filter(
            Q(id__icontains=search) | 
            Q(supplier_name__icontains=search)
        )
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from and date_to:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            purchase_orders = purchase_orders.filter(
                date_created__range=[start_date, end_date]
            )
        except ValueError:
            pass
    elif date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            purchase_orders = purchase_orders.filter(date_created__gte=start_date)
        except ValueError:
            pass
    elif date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            purchase_orders = purchase_orders.filter(date_created__lte=end_date)
        except ValueError:
            pass
    
    supplier = request.GET.get('supplier')
    if supplier:
        purchase_orders = purchase_orders.filter(supplier_name=supplier)
    
    # Prepare filters for PDF
    filters = {
        'date_from': date_from,
        'date_to': date_to,
        'supplier': supplier,
        'search': search,
    }
    
    # Generate PDF
    pdf = generate_purchase_report_pdf(purchase_orders, filters)
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    filename = f"purchase_report_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response

def view_purchase(request, pk):
    """View purchase order details"""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    items = po.purchaseitem_set.all()
    
    return render(request, 'modals/purchase_detail_modal.html', {
        'po': po,
        'items': items
    })


def deactivate_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = False
    supplier.save()
    messages.success(request, f'Supplier {supplier.name} deactivated successfully!')
    return redirect('pages:suppliers')

def activate_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = True
    supplier.save()
    messages.success(request, f'Supplier {supplier.name} activated successfully!')
    return redirect('pages:suppliers')

def cashiers(request):
    cashiers = User.objects.filter(is_superuser=False, is_staff=False).order_by('-date_joined')
    total_cashiers = cashiers.count()
    active_cashiers = cashiers.filter(is_active=True).count()
    
    context = {
        'cashiers': cashiers,
        'total_cashiers': total_cashiers,
        'active_cashiers': active_cashiers,
    }
    return render(request, 'admin/cashiers.html', context)

def add_cashier(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_active = request.POST.get('is_active') == 'on'
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        elif password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        else:
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=make_password(password),
                is_active=is_active,
                is_staff=False,
                is_superuser=False
            )
            messages.success(request, f'Cashier {username} created successfully!')
        
    return redirect('pages:cashiers')  # Redirect to cashiers page

def edit_cashier(request, pk):
    cashier = get_object_or_404(User, pk=pk, is_superuser=False, is_staff=False)
    
    if request.method == 'POST':
        cashier.username = request.POST.get('username')
        cashier.email = request.POST.get('email')
        cashier.first_name = request.POST.get('first_name', '')
        cashier.last_name = request.POST.get('last_name', '')
        cashier.is_active = request.POST.get('is_active') == 'on'
        
        password = request.POST.get('password')
        if password:
            cashier.password = make_password(password)
        
        cashier.save()
        messages.success(request, f'Cashier {cashier.username} updated successfully!')
    
    return redirect('pages:cashiers')  # Redirect to cashiers page

# Update all other cashier functions to redirect to 'pages:cashiers'
def delete_cashier(request, pk):
    cashier = get_object_or_404(User, pk=pk, is_superuser=False, is_staff=False)
    username = cashier.username
    cashier.delete()
    messages.success(request, f'Cashier {username} deleted successfully!')
    return redirect('pages:cashiers')  # Fixed redirect

def deactivate_cashier(request, pk):
    cashier = get_object_or_404(User, pk=pk, is_superuser=False, is_staff=False)
    cashier.is_active = False
    cashier.save()
    messages.success(request, f'Cashier {cashier.username} deactivated successfully!')
    return redirect('pages:cashiers')  # Fixed redirect

def activate_cashier(request, pk):
    cashier = get_object_or_404(User, pk=pk, is_superuser=False, is_staff=False)
    cashier.is_active = True
    cashier.save()
    messages.success(request, f'Cashier {cashier.username} activated successfully!')
    return redirect('pages:cashiers')  # Fixed redirect


# views.py
def manage_categories_bulk(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Handle category updates
            for key, value in request.POST.items():
                if key.startswith('category_name_'):
                    category_id = key.replace('category_name_', '')
                    category = Category.objects.get(id=category_id)
                    if category.name != value:
                        category.name = value
                        category.save()
            
            # Handle new categories
            new_categories = request.POST.getlist('new_categories')
            for category_name in new_categories:
                if category_name.strip():
                    Category.objects.create(name=category_name.strip())
            
            # Handle deletions
            categories_to_delete = request.POST.get('categories_to_delete', '')
            if categories_to_delete:
                category_ids = [int(id) for id in categories_to_delete.split(',') if id]
                Category.objects.filter(id__in=category_ids).delete()
            
            return JsonResponse({'success': True})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})



@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('pages:cashier_dashboard')
    
    # Calculate date ranges
    today = timezone.now().date()
    
    # Basic stats - convert to float to avoid Decimal/float mixing
    total_sales = float(Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0)
    
    # Purchases - use 'Received' status and convert to float
    total_purchases_result = PurchaseOrder.objects.filter(status='Received').aggregate(total=Sum('total_cost'))['total']
    total_purchases = float(total_purchases_result or 0)
    
    total_products = Product.objects.count()
    total_profit = total_sales - total_purchases  # Now both are floats
    
    # Today's stats
    today_sales_result = Invoice.objects.filter(date_issued__date=today).aggregate(total=Sum('total_amount'))['total']
    today_sales = float(today_sales_result or 0)
    today_orders = Invoice.objects.filter(date_issued__date=today).count()
    
    # Inventory stats - ensure we're working with floats
    total_inventory_value = 0
    products = Product.objects.all()
    for product in products:
        # Convert both values to float before calculation
        quantity = float(product.product_quantity)
        price = float(product.product_price)
        product_value = quantity * price * 0.6  # estimated cost ratio
        total_inventory_value += product_value
    
    # Additional stats for new panels
    total_categories = Category.objects.count()
    total_suppliers = Supplier.objects.count()
    total_cashiers = User.objects.filter(is_superuser=False, is_staff=False).count()
    active_cashiers = User.objects.filter(is_superuser=False, is_staff=False, is_active=True).count()
    pending_orders = PurchaseOrder.objects.filter(status='Pending').count()
    
    # Low stock count (assuming min_stock_level exists, otherwise use a default)
    try:
        low_stock_count = Product.objects.filter(product_quantity__lte=10).count()  # Default threshold
    except:
        low_stock_count = 0
    
    # Recent activity
    recent_sales = Invoice.objects.all().order_by('-date_issued')[:5]
    recent_purchases = PurchaseOrder.objects.filter(status='Received').order_by('-date_created')[:5]
    
    context = {
        'total_sales': total_sales,
        'total_purchases': total_purchases,
        'total_products': total_products,
        'total_profit': total_profit,
        'today_sales': today_sales,
        'today_orders': today_orders,
        'inventory_value': total_inventory_value,
        'total_categories': total_categories,
        'total_suppliers': total_suppliers,
        'total_cashiers': total_cashiers,
        'active_cashiers': active_cashiers,
        'pending_orders': pending_orders,
        'low_stock_count': low_stock_count,
        'recent_sales': recent_sales,
        'recent_purchases': recent_purchases,
    }
    
    return render(request, 'admin/admin_dashboard.html', context)



@login_required
def edit_profile(request):
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        username = request.POST.get('username', '')
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Update basic profile information
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        
        # Check if username is being changed and if it's available
        if username != user.username:
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                messages.error(request, 'Username already exists. Please choose a different one.')
            else:
                user.username = username
        
        # Handle password change if provided
        if new_password:
            if not current_password:
                messages.error(request, 'Current password is required to change your password.')
            elif not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            elif len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
            else:
                user.set_password(new_password)
                messages.success(request, 'Password updated successfully!')
                # Re-authenticate user if password was changed
                update_session_auth_hash(request, user)
        
        try:
            user.save()
            messages.success(request, 'Profile updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
        
        return redirect('pages:edit_profile')
    
    return render(request, 'admin/edit_profile.html')