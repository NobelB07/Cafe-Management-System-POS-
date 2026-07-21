# Cafe Management System

A comprehensive Django-based cafe management system with menu management, order processing, billing, and user role management.

## Features

### 1. Menu Management
- Add, edit, and delete menu items
- Categories: Beverages, Snacks, Meals, Desserts
- Image upload support for menu items
- Availability status toggle

### 2. Order Management
- Create new orders with customer details
- Add multiple items to orders with quantities
- View all orders with status filtering
- Update order status (Pending, Preparing, Completed, Cancelled)
- Remove items from orders

### 3. Billing / Invoice
- Automatic calculation of subtotal, discounts, and total
- Apply discounts to orders
- Generate printable invoices/receipts
- Detailed billing breakdown

### 4. User Roles
- **Admin**: Full access to menu management, reports, and all features
- **Staff/Cashier**: Can place orders and generate bills
- Role-based access control throughout the system

### 5. Dashboard
- Today's total orders count
- Today's revenue from completed orders
- Pending vs completed orders statistics
- Most ordered items analysis
- Quick action buttons for common tasks

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Instructions

1. **Navigate to the project directory**
   ```bash
   cd c:\Users\nobel\OneDrive\Documents\Cafe
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser (Admin account)**
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to create your admin account.

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Open your web browser and go to: `http://127.0.0.1:8000/`
   - Admin panel: `http://127.0.0.1:8000/admin/`

## Usage

### First Time Setup

1. **Login as Admin**
   - Use the superuser credentials you created
   - Access the admin panel at `/admin/`

2. **Add Menu Items**
   - Go to Dashboard → Menu → Add Menu Item
   - Add items with name, price, category, description, and optional image
   - Set availability status

3. **Create Staff Accounts**
   - Go to Admin panel → Users
   - Create new users and assign appropriate permissions
   - Staff users can access the main interface but not admin features

### Daily Operations

1. **Place an Order**
   - Dashboard → New Order
   - Enter customer name and notes
   - Add menu items with quantities
   - Apply discounts if needed
   - Update order status as it progresses

2. **View Orders**
   - Dashboard → Orders
   - Filter by status (Pending, Preparing, Completed, Cancelled)
   - Click on an order to view details or generate invoice

3. **Generate Invoice**
   - From order detail page, click "View Invoice"
   - Print the invoice using the print button
   - Invoice includes all order details and billing breakdown

4. **Monitor Performance**
   - Dashboard shows today's statistics
   - View most ordered items
   - Track revenue and order counts

## Project Structure

```
Cafe/
├── cafe_project/          # Django project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── cafe_app/              # Main application
│   ├── __init__.py
│   ├── admin.py           # Admin configuration
│   ├── apps.py            # App configuration
│   ├── forms.py           # Form definitions
│   ├── models.py          # Database models
│   ├── urls.py            # URL routing
│   └── views.py           # View functions
├── templates/             # HTML templates
│   ├── base.html          # Base template
│   └── cafe_app/          # App-specific templates
│       ├── dashboard.html
│       ├── menu_list.html
│       ├── menu_form.html
│       ├── menu_confirm_delete.html
│       ├── order_list.html
│       ├── order_form.html
│       ├── order_detail.html
│       ├── order_invoice.html
│       └── signup.html
├── static/                # Static files
│   └── css/
│       └── style.css
├── media/                 # User-uploaded files (created automatically)
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Database Models

### MenuItem
- Stores menu item details
- Fields: name, price, category, description, image, is_available

### Order
- Stores order information
- Fields: order_number, customer_name, status, subtotal, discount, total, notes
- Status options: pending, preparing, completed, cancelled

### OrderItem
- Links orders to menu items
- Fields: order, menu_item, quantity, price_at_order

## User Roles

### Admin (is_staff=True)
- Full access to all features
- Can manage menu items
- Can access Django admin panel
- Can view all reports and statistics

### Staff/Cashier (is_staff=False)
- Can place orders
- Can generate bills
- Can update order status
- Cannot access menu management or admin panel

## Technologies Used

- **Django 4.2+**: Web framework
- **Python 3.8+**: Programming language
- **SQLite**: Database (default)
- **Bootstrap 5**: Frontend framework
- **Font Awesome**: Icons
- **Pillow**: Image handling

## Customization

### Adding New Categories
Update the `CATEGORY_CHOICES` in `cafe_app/models.py`:
```python
CATEGORY_CHOICES = [
    ('beverages', 'Beverages'),
    ('snacks', 'Snacks'),
    ('meals', 'Meals'),
    ('desserts', 'Desserts'),
    ('new_category', 'New Category'),  # Add your category here
]
```

### Changing Colors
Edit the color values in `templates/base.html` and `static/css/style.css`:
- Primary color: `#d35400` (orange)
- Change to your preferred color scheme

## Troubleshooting

### Static files not loading
- Run: `python manage.py collectstatic`
- Ensure `STATIC_URL` and `STATICFILES_DIRS` are correctly set in `settings.py`

### Images not uploading
- Ensure `MEDIA_URL` and `MEDIA_ROOT` are correctly set in `settings.py`
- Check that the media directory has write permissions

### Database errors
- Delete the `db.sqlite3` file
- Run migrations again: `python manage.py migrate`

## License

This project is provided as-is for educational and commercial use.

## Support

For issues or questions, please refer to Django documentation at https://docs.djangoproject.com/
