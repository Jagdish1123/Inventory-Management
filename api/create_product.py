# (Code from Part 1, the corrected version)
# See the README.md for the full explanation.

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# Assuming these models are defined
from models import db, Product, Inventory, Companies

product_bp = Blueprint('products', __name__)

@product_bp.route('/api/products', methods=['POST'])
def create_product():
    """
    API endpoint to create a new product and its initial inventory in an atomic transaction.
    """
    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid JSON format"}), 400

    required_fields = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity']
    if not all(field in data for field in required_fields):
        missing_fields = [field for field in required_fields if field not in data]
        return jsonify({"error": "Missing required fields", "fields": missing_fields}), 400

    try:
        # Assuming we need to get company_id from the user's session or header
        company_id = data.get('company_id') # Placeholder for a real-world scenario

        # Check for existing SKU within the company
        existing_product = Product.query.filter_by(sku=data['sku'], company_id=company_id).first()
        if existing_product:
            return jsonify({"error": f"SKU '{data['sku']}' already exists for this company"}), 409

        # Create new product and inventory records in a single transaction
        new_product = Product(
            company_id=company_id,
            name=data['name'],
            sku=data['sku'],
            price=data['price']
        )
        new_inventory = Inventory(
            product=new_product,
            warehouse_id=data['warehouse_id'],
            quantity=data['initial_quantity']
        )
        
        db.session.add_all([new_product, new_inventory])
        db.session.commit()

        return jsonify({
            "message": "Product created successfully",
            "product_id": new_product.id
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "A product with this SKU already exists for this company."}), 409
    except Exception as e:
        db.session.rollback()
        print(f"Error creating product: {e}")
        return jsonify({"error": "Failed to create product", "details": str(e)}), 500