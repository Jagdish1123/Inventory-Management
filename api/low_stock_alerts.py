# (Code from Part 3)
# See the README.md for the full explanation.

from flask import Blueprint, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, Product, Inventory, Warehouses, Suppliers, ProductSuppliers, InventoryHistory

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
def get_low_stock_alerts(company_id):
    """
    Returns a list of low-stock alerts for a given company.
    Logic: Identifies products with quantity <= low_stock_threshold and recent sales activity.
    """
    # Define a time frame for "recent sales activity"
    recent_sales_period = 30 # days
    cutoff_date = datetime.utcnow() - timedelta(days=recent_sales_period)

    # Main query to find low-stock items
    # Join necessary tables to get all required information
    query = db.session.query(
        Product,
        Inventory,
        Warehouses,
        Suppliers
    ).join(Inventory, Inventory.product_id == Product.id)\
     .join(Warehouses, Inventory.warehouse_id == Warehouses.id)\
     .outerjoin(ProductSuppliers, ProductSuppliers.product_id == Product.id)\
     .outerjoin(Suppliers, ProductSuppliers.supplier_id == Suppliers.id)\
     .filter(Product.company_id == company_id)\
     .filter(Inventory.quantity <= Inventory.low_stock_threshold)\
     .distinct(Product.id, Inventory.warehouse_id) # Use distinct to handle multiple suppliers

    # Fetch results
    low_stock_items = query.all()

    alerts = []
    # Loop through the low-stock items to calculate sales velocity and build the response
    for product, inventory, warehouse, supplier in low_stock_items:
        # Calculate daily sales velocity from InventoryHistory
        sales_velocity_query = db.session.query(
            func.sum(func.abs(InventoryHistory.quantity_change))
        ).filter(
            InventoryHistory.product_id == product.id,
            InventoryHistory.warehouse_id == warehouse.id,
            InventoryHistory.change_type == 'sale',
            InventoryHistory.timestamp >= cutoff_date
        )
        total_sales_in_period = sales_velocity_query.scalar() or 0
        
        # Avoid division by zero
        if total_sales_in_period > 0:
            daily_sales_velocity = total_sales_in_period / recent_sales_period
            days_until_stockout = round(inventory.quantity / daily_sales_velocity)
        else:
            # If no sales in the period, a stockout is not imminent
            days_until_stockout = None
            # Business rule: "Only alert for products with recent sales activity"
            continue 

        # Build the final alert object
        alert = {
            "product_id": product.id,
            "product_name": product.name,
            "sku": product.sku,
            "warehouse_id": warehouse.id,
            "warehouse_name": warehouse.name,
            "current_stock": inventory.quantity,
            "threshold": inventory.low_stock_threshold,
            "days_until_stockout": days_until_stockout,
            "supplier": {
                "id": supplier.id if supplier else None,
                "name": supplier.name if supplier else "No supplier assigned",
                "contact_email": supplier.contact_email if supplier else None
            }
        }
        alerts.append(alert)

    return jsonify({
        "alerts": alerts,
        "total_alerts": len(alerts)
    })