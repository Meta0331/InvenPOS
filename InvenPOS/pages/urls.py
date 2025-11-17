from django.urls import path, include
from django.contrib.auth.views import LogoutView
from .views import authView, home, custom_login, admin_dashboard, cashier_dashboard, products
from django.urls import path
from . import views
from django.urls import path
from django.contrib.auth import update_session_auth_hash

urlpatterns = [
    path("", home, name="home"),
    path("signup/", authView, name="authView"),
    path("login/", custom_login, name="login"),
    path("logout/", LogoutView.as_view(next_page='pages:login'), name="logout"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
    path("products/", views.products, name="products"),
    path("cashier-dashboard/", cashier_dashboard, name="cashier_dashboard"),
    path("accounts/", include("django.contrib.auth.urls")),

       path("products/", views.products, name="products"),
    path("products/add/", views.add_product, name="add_product"),
    path("products/edit/<int:id>/", views.edit_product, name="edit_product"),
    path("products/delete/<int:id>/", views.delete_product, name="delete_product"),
      path('users/', views.users, name='users'),

path('products/restock/<int:id>/', views.restock_product, name='restock_product'),
 path('api/create-invoice/', views.create_invoice, name='create_invoice'),
    path('api/default-tax-rate/', views.get_default_tax_rate, name='get_default_tax_rate'),


   path('add-category/', views.add_category, name='add_category'),
    path('edit-category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    
      path('users/', views.users, name='users'),
      path('suppliers/', views.suppliers, name='suppliers'),

path('add_supplier/', views.add_supplier, name='add_supplier'),
path('delete_supplier/<int:supplier_id>/', views.delete_supplier, name='delete_supplier'),
path('edit_supplier/<int:supplier_id>/', views.edit_supplier, name='edit_supplier'),

 path('payment/', views.payment_page, name='payment'),
   path('invoices/', views.invoices_management, name='invoices'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoice/<int:invoice_id>/edit/', views.invoice_update, name='invoice_update'),
    path('invoice/form/', views.invoice_form, name='invoice_form'),
      path('invoice/<int:invoice_id>/print/', views.print_invoice_pdf, name='print_invoice_pdf'),
    path('invoice/<int:invoice_id>/download/', views.download_invoice_pdf, name='download_invoice_pdf'),
    
    
    path('tax/add/', views.tax_create_inline, name='tax_create_inline'),
path('tax/<int:pk>/update/', views.tax_update_inline, name='tax_update_inline'),
path('tax/<int:pk>/delete/', views.tax_delete_inline, name='tax_delete_inline'),


    path('sales/', views.sales_list, name='sales_list'),
    path('sales/<int:invoice_id>/', views.sales_detail, name='sales_detail'),
    path('sales/edit/<int:invoice_id>/', views.sales_edit, name='sales_edit'),
    path('sales/delete/<int:invoice_id>/', views.sales_delete, name='sales_delete'),

    
     path('sales-reports/', views.sales_reports, name='sales_reports'),  # ← ADD THIS LINE
    path('sales-reports/print/', views.print_sales_report, name='print_sales_report'),


      path('purchases/', views.purchase_management, name='purchase_management'),
    path('purchases/mark-received/<int:pk>/', views.mark_received, name='mark_received'),
    path('purchases/create/', views.create_purchase_order, name='create_purchase_order'),
    path('purchases/view/<int:pk>/', views.view_purchase, name='view_purchase'),
    path('purchases/cancel/<int:pk>/', views.cancel_purchase, name='cancel_purchase'),

    path('purchases/reports/', views.purchase_reports, name='purchase_reports'),
    path('purchases/print-report/', views.print_purchase_report, name='print_purchase_report'),
path('deactivate-supplier/<int:pk>/', views.deactivate_supplier, name='deactivate_supplier'),
path('activate-supplier/<int:pk>/', views.activate_supplier, name='activate_supplier'),
# urls.py
path('manage-categories-bulk/', views.manage_categories_bulk, name='manage_categories_bulk'),

    # Cashier management URLs
        path('cashiers/', views.cashiers, name='cashiers'),  # New URL for cashiers
path('cashiers/add/', views.add_cashier, name='add_cashier'),
path('cashiers/edit/<int:pk>/', views.edit_cashier, name='edit_cashier'),
path('cashiers/delete/<int:pk>/', views.delete_cashier, name='delete_cashier'),
path('cashiers/deactivate/<int:pk>/', views.deactivate_cashier, name='deactivate_cashier'),
path('cashiers/activate/<int:pk>/', views.activate_cashier, name='activate_cashier'),

path('edit-profile/', views.edit_profile, name='edit_profile'),
]