# (Code from Part 1, the corrected version)
# See the README.md for the full explanation.

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError, DataError # Added DataError for type issues
# from datetime import datetime # Not strictly used in this specific endpoint logic

# Assuming these models are defined
# from models import db, Product, Inventory, Companies, Warehouses # Assuming Warehouses also exists for validation
from your_app_models import db, Product, Inventory # Replace 'your_app_models' with actual import path

product_bp = Blueprint('products', __name__)

@product_bp.route('/api/products', methods=['POST'])
def create_product():
    """
    API endpoint to create a new product and its initial inventory in an atomic transaction.
    """
    try:
        data = request.get_json()
    except Exception as e: # Catch specific exception for clarity, e.g., BadRequest
        return jsonify({"error": "Invalid JSON format", "details": str(e)}), 400

    # 1. Input Validation for required fields
    required_fields = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity']
    if not all(field in data for field in required_fields):
        missing_fields = [field for field in required_fields if field not in data]
        return jsonify({"error": "Missing required fields", "fields": missing_fields}), 400

    # 2. Extract company_id from a secure source (e.g., authentication context)
    # IMPORTANT: In a real application, DO NOT get company_id directly from the request body.
    # It should come from the authenticated user's session or token.
    company_id = 1 # Placeholder for demonstration. Replace with actual logic.
    # If company_id MUST be in the payload for *some* reason, it should also be in required_fields.
    # Example: company_id = request.headers.get('X-Company-ID') or from a JWT token.

    # 3. Type Validation for numeric fields
    try:
        price = float(data['price'])
        warehouse_id = int(data['warehouse_id'])
        initial_quantity = int(data['initial_quantity'])
        if initial_quantity < 0:
            return jsonify({"error": "Initial quantity cannot be negative"}), 400
        # Optional: Validate warehouse_id actually exists for the company
        # warehouse = Warehouses.query.filter_by(id=warehouse_id, company_id=company_id).first()
        # if not warehouse:
        #     return jsonify({"error": "Warehouse not found or does not belong to your company"}), 404
        
    except (ValueError, TypeError) as e:
        return jsonify({"error": "Invalid data type for price, warehouse_id, or initial_quantity", "details": str(e)}), 400
    
    # 4. Check for existing SKU within the company BEFORE starting transaction
    try:
        existing_product = Product.query.filter_by(sku=data['sku'], company_id=company_id).first()
        if existing_product:
            return jsonify({"error": f"SKU '{data['sku']}' already exists for this company"}), 409
    except Exception as e:
        # Catch potential database query issues for existing product check
        return jsonify({"error": "Failed to check for existing SKU", "details": str(e)}), 500

    # 5. Create new product and inventory records in a single atomic transaction
    try:
        new_product = Product(
            company_id=company_id,
            name=data['name'],
            sku=data['sku'],
            price=price # Use the type-validated price
            # Removed 'warehouse_id' from Product, as it's linked via Inventory
        )
        
        # SQLAlchemy typically handles the dependency and assigns an ID when 'new_inventory'
        # references 'new_product' directly. `db.session.flush()` is generally not needed
        # when using a direct object relationship, but would be necessary if using `product_id=new_product.id`.
        # For robustness, `add_all` is often sufficient.
        
        new_inventory = Inventory(
            product=new_product, # Link directly to the new_product object
            warehouse_id=warehouse_id, # Use the type-validated warehouse_id
            quantity=initial_quantity # Use the type-validated quantity
        )
        
        db.session.add_all([new_product, new_inventory])
        db.session.commit()

        return jsonify({
            "message": "Product and initial inventory created successfully",
            "product_id": new_product.id,
            "sku": new_product.sku # Include SKU in success for confirmation
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        # More specific error messages could be parsed from 'e' if needed
        return jsonify({"error": "Database integrity constraint violation (e.g., product/warehouse ID not found, or unique constraint issue).", "details": str(e)}), 400
    except DataError as e: # Catch errors for data that doesn't fit column type/size
        db.session.rollback()
        return jsonify({"error": "Data provided does not match database column types or length.", "details": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error creating product: {e}") # Log the error for debugging
        return jsonify({"error": "Failed to create product due to an unexpected server error", "details": str(e)}), 500