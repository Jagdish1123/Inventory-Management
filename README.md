# StockFlow: Inventory Management System - Case Study

This repository contains my solutions and thought process for the **StockFlow B2B inventory management platform** case study.

---

## 📌 Part 1: Code Review & Debugging

### The Problem
The provided `create_product` API endpoint is meant to create a new product and its initial inventory count. While it compiles, it has several flaws that make it brittle in production.

### Identified Issues
1. **Lack of Atomicity**  
   - Uses two separate `db.session.commit()` calls.  
   - Risk: If the first commit succeeds but the second fails, the system will have a product without inventory (inconsistent state).

2. **Missing Input Validation**  
   - Assumes all fields (`name`, `sku`, `price`, `warehouse_id`, `initial_quantity`) exist and are valid.  
   - Risk: Malformed requests cause crashes (`KeyError`, `TypeError`).

3. **No Duplicate SKU Handling**  
   - SKUs must be unique, but no check is performed.  
   - Risk: Database errors or duplicate SKUs in the system.

4. **Poor Error Handling**  
   - No `try...except` block.  
   - Risk: Returns 500 Internal Server Error instead of meaningful messages.

5. **Warehouse Assumption**  
   - Tightly couples product creation to a single warehouse.  
   - Risk: Blocks multi-warehouse support (a core requirement).

---

### The Fix
See [api/create_product.py](api/create_product.py).

Key improvements:
-  Single atomic transaction (`db.session.add_all()` + single commit).  
-  SKU uniqueness pre-check before insertion.  
-  Input validation with default values for optional fields.  
-  Proper error handling with status codes (`400`, `409`, `201`).  
-  Product creation decoupled from inventory initialization.

---

## 📌 Part 2: Database Design

### Proposed Schema
See [schema/schema.sql](schema/schema.sql).  

**Tables:**
- **Company** → `id`, `name`  
- **Warehouse** → `id`, `company_id`, `name`, `location`  
- **Product** → `id`, `company_id`, `sku (UNIQUE per company)`, `name`, `price`, `type`  
- **Inventory** → `id`, `product_id`, `warehouse_id`, `quantity`, `low_stock_threshold`  
- **InventoryHistory** → `id`, `inventory_id`, `change`, `reason`, `created_at`  
- **Supplier** → `id`, `name`, `contact_email`  
- **SupplierProduct** → `supplier_id`, `product_id`  
- **ProductBundle** → `bundle_id`, `product_id`, `quantity`

### Design Decisions & Assumptions
- **SKU Uniqueness:** Unique per company (not globally).  
- **Many-to-Many Relationships:**  
  - Products ↔ Suppliers (`SupplierProduct`).  
  - Bundles ↔ Components (`ProductBundle`).  
- **Append-Only Inventory History:** Enables auditing and sales velocity calculations.  
- **Low Stock Threshold:** Stored per product/warehouse for flexibility.  

### Gaps & Questions
- Should SKUs be **global** or **per company**?  
- How is **low stock threshold** determined (manual vs. automated)?  
- Do we need **multi-currency** support for product price?  
- How long should **InventoryHistory** be retained (scalability)?  
- Do suppliers provide **bundles** or only individual products?  

---

## 📌 Part 3: API Implementation

### Endpoint
`GET /api/companies/{company_id}/alerts/low-stock`

### Implementation
See [api/low_stock_alerts.py](api/low_stock_alerts.py).

**Approach:**
1. **Fetch Products & Inventory** for the given `company_id`.  
2. **Filter for Low Stock** (`quantity <= low_stock_threshold`).  
3. **Calculate Sales Velocity** from `InventoryHistory` (last 30 days).  
4. **Compute Days Until Stockout** (`current_stock / avg_daily_sales`).  
   - Handle division by zero safely.  
5. **Join Supplier Info** from `SupplierProduct`.  
6. **Build JSON Response** in required format.

---

### Example Response
```json
{
  "alerts": [
    {
      "product_id": 123,
      "product_name": "Widget A",
      "sku": "WID-001",
      "warehouse_id": 456,
      "warehouse_name": "Main Warehouse",
      "current_stock": 5,
      "threshold": 20,
      "days_until_stockout": 12,
      "supplier": {
        "id": 789,
        "name": "Supplier Corp",
        "contact_email": "orders@supplier.com"
      }
    }
  ],
  "total_alerts": 1
}


