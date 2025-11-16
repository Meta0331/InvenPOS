from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Product(models.Model):
    product_name = models.CharField(max_length=100)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_quantity = models.IntegerField(default=0)
    product_category = models.CharField(max_length=50)
    product_img = models.ImageField(upload_to='products/', blank=True, null=True)

    def __str__(self):
        return self.product_name

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    company = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Restock(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True)
    quantity_added = models.PositiveIntegerField(default=0)
    date_restocked = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.product.product_name} - {self.quantity_added} added"

class TaxRate(models.Model):
    name = models.CharField(max_length=50)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"





# models.py - Add this to your existing models
class Invoice(models.Model):
    invoice_number = models.CharField(max_length=20, unique=True)
    customer_id = models.CharField(max_length=20, default='CUST-000')
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date_issued = models.DateTimeField(default=timezone.now)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    change = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.ForeignKey(TaxRate, null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices_created')
    staff_name = models.CharField(max_length=100, default='Cashier')
    is_active = models.BooleanField(default=True)  # For soft delete

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice:
                try:
                    last_number = int(last_invoice.invoice_number.split('-')[-1])
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            self.invoice_number = f"INV-{new_number:06d}"
        
        if self.customer_id == 'CUST-000':
            last_customer = Invoice.objects.exclude(customer_id='CUST-000').order_by('-id').first()
            if last_customer:
                try:
                    last_cust_number = int(last_customer.customer_id.split('-')[-1])
                    new_cust_number = last_cust_number + 1
                except:
                    new_cust_number = 1
            else:
                new_cust_number = 1
            self.customer_id = f"CUST-{new_cust_number:03d}"
        
        if self.tax_rate and self.subtotal > 0:
            self.tax_amount = self.subtotal * (self.tax_rate.percentage / 100)
            self.total_amount = self.subtotal + self.tax_amount
        else:
            self.tax_amount = 0
            self.total_amount = self.subtotal
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Soft delete - mark as inactive instead of actually deleting"""
        self.is_active = False
        self.save()

    def hard_delete(self, *args, **kwargs):
        """Actual delete from database"""
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.customer_id}"

class SoldItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='sold_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        
        # Store product name if not provided
        if not self.product_name and self.product:
            self.product_name = self.product.product_name
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name} x{self.quantity} - ₱{self.total_price}"
    






class PurchaseOrder(models.Model):
    supplier_name = models.CharField(max_length=100)
    expected_date = models.DateField()
    date_created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Pending')
    total_cost = models.FloatField(default=0)

class PurchaseItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    cost_per_unit = models.FloatField()
    
    @property
    def total_cost(self):
        return self.quantity * self.cost_per_unit