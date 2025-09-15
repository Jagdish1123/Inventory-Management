from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlalchemy.orm import aliased # For aliasing tables in complex joins

# Assuming these models are defined in a 'models.py' file in the same directory
# Or adjust the import path as needed (e.g., from .models import ...)
from models import db, Product, Inventory, Warehouses, Suppliers, ProductSuppliers, InventoryHistory, Company

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
def get_low_stock_alerts(company_id):
    """
    Returns a list of low-stock alerts for a given company.
    Logic: Identifies products with quantity <= low_stock_threshold and recent sales activity.
    
    Optimizations:
    - Uses a single, optimized query to fetch low-stock items and their sales velocity.
      This avoids the N+1 query problem present in the previous iteration.
    - Includes comprehensive error handling for database operations.
    - Ensures all business rules are met.
    """
    try:
        # Validate company_id exists and belongs to the authenticated user's context
        # In a real app, company_id would likely be derived from auth tokens, not URL parameter.
        # For this exercise, we'll just check if it's a valid integer.
        # It's good practice to ensure the company exists.
        company_exists = db.session.query(Company.id).filter_by(id=company_id).first()
        if not company_exists:
            return jsonify({"error": "Company not found."}), 404

        recent_sales_period_days = 30 # days
        cutoff_date = datetime.utcnow() - timedelta(days=recent_sales_period_days)

        # 1. Create a subquery to calculate total sales for each product/warehouse pair
        #    This is the core of the N+1 optimization.
        sales_velocity_subquery = db.session.query(
            InventoryHistory.product_id,
            InventoryHistory.warehouse_id,
            func.sum(func.abs(InventoryHistory.quantity_change)).label('total_sales_in_period')
        ).filter(
            InventoryHistory.change_type == 'sale',
            InventoryHistory.timestamp >= cutoff_date
        ).group_by(
            InventoryHistory.product_id,
            InventoryHistory.warehouse_id
        ).subquery()

        # 2. Main query to fetch low-stock items, including their sales velocity from the subquery
        #    We need aliased Supplier and ProductSuppliers if a product can have multiple suppliers
        #    and we want to aggregate them, but for the requested format (single supplier entry per alert),
        #    outerjoin with distinct is generally acceptable, though it might pick one arbitrarily.
        #    If multiple suppliers should be returned, a different approach (e.g., array_agg or
        #    a separate query for suppliers) would be needed. For the given response format,
        #    we'll continue with the single supplier assumption from the distinct query.

        # Using aliased to make it explicit if needed, but not strictly required here.
        # Aliasiing is more common when joining the same table multiple times.
        
        low_stock_items_data = db.session.query(
            Product.id.label('product_id'),
            Product.name.label('product_name'),
            Product.sku,
            Inventory.warehouse_id,
            Warehouses.name.label('warehouse_name'),
            Inventory.quantity.label('current_stock'),
            Inventory.low_stock_threshold.label('threshold'),
            Suppliers.id.label('supplier_id'),
            Suppliers.name.label('supplier_name'),
            Suppliers.contact_email.label('supplier_contact_email'),
            sales_velocity_subquery.c.total_sales_in_period # Get sales from subquery
        ).join(Inventory, Inventory.product_id == Product.id)\
         .join(Warehouses, Inventory.warehouse_id == Warehouses.id)\
         .outerjoin(ProductSuppliers, ProductSuppliers.product_id == Product.id)\
         .outerjoin(Suppliers, ProductSuppliers.supplier_id == Suppliers.id)\
         .outerjoin(
             sales_velocity_subquery,
             and_(
                 sales_velocity_subquery.c.product_id == Product.id,
                 sales_velocity_subquery.c.warehouse_id == Inventory.warehouse_id # Link to Inventory's warehouse
             )
         )\
         .filter(Product.company_id == company_id)\
         .filter(Inventory.quantity <= Inventory.low_stock_threshold)\
         .filter(sales_velocity_subquery.c.total_sales_in_period.isnot(None))\
         .distinct(Product.id, Inventory.warehouse_id)\
         .all()

        alerts = []
        for item in low_stock_items_data:
            total_sales = item.total_sales_in_period or 0 # Coalesce None to 0, though filter should prevent None
            
            # The filter `.filter(sales_velocity_subquery.c.total_sales_in_period.isnot(None))`
            # already ensures we only get products with sales activity.
            # We still need to handle cases where daily_sales_velocity might be zero if recent_sales_period_days is 0
            # or if the query yields 0 sales for some reason after the filter.
            daily_sales_velocity = total_sales / recent_sales_period_days if recent_sales_period_days > 0 else 0

            days_until_stockout = None
            if daily_sales_velocity > 0:
                days_until_stockout = round(item.current_stock / daily_sales_velocity)

            # Build the final alert object
            alert = {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "sku": item.sku,
                "warehouse_id": item.warehouse_id,
                "warehouse_name": item.warehouse_name,
                "current_stock": item.current_stock,
                "threshold": item.threshold,
                "days_until_stockout": days_until_stockout,
                "supplier": {
                    "id": item.supplier_id,
                    "name": item.supplier_name if item.supplier_name else "No supplier assigned",
                    "contact_email": item.supplier_contact_email
                }
            }
            alerts.append(alert)

        return jsonify({
            "alerts": alerts,
            "total_alerts": len(alerts)
        })

    except Exception as e:
        # Log the full exception traceback for internal debugging
        import traceback
        traceback.print_exc() 
        print(f"Error fetching low stock alerts for company {company_id}: {e}")
        return jsonify({"error": "An unexpected server error occurred.", "details": "Please try again later."}), 500