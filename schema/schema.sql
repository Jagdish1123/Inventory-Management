-- # StockFlow Inventory Management System - Database Schema (Corrected & Best Practice)
-- #
-- # This schema is designed based on the requirements for StockFlow, a B2B inventory
-- # management platform. It includes entities for Companies, Warehouses, Products,
-- # Inventory levels, historical tracking, Suppliers, and Product Bundles.
-- #
-- # Key Design Principles:
-- # - Normalization: Avoids data redundancy and improves data integrity.
-- # - Clear Relationships: Uses Foreign Keys to define relationships between tables.
-- # - Constraints: Implements UNIQUE and CHECK constraints for data validity.
-- # - Auditability: InventoryHistory provides a complete log of stock movements.
-- # - Scalability: Designed with common B2B SaaS patterns like "SKU unique per company".

-- -----------------------------------------------------
-- Table: Companies
-- Represents a business client using the platform.
-- Each company owns its own warehouses, products, and suppliers.
-- -----------------------------------------------------
CREATE TABLE Companies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    -- Add other relevant company details here (e.g., subscription_plan, contact_info)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- -----------------------------------------------------
-- Table: Warehouses
-- Represents a physical location where products are stored.
-- Each warehouse belongs to a specific company.
-- -----------------------------------------------------
CREATE TABLE Warehouses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    location TEXT, -- Optional: Stores physical address or description
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES Companies(id) ON DELETE CASCADE,
    -- Ensures warehouse names are unique within a company
    UNIQUE KEY unique_warehouse_per_company (company_id, name)
);

-- -----------------------------------------------------
-- Table: Products
-- Represents a product defined within the system.
-- Each product belongs to a specific company.
-- Products can be "standard" or "bundles" (composed of other products).
-- -----------------------------------------------------
CREATE TABLE Products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL, -- Price can be decimal values
    -- Product type helps differentiate regular items from bundles, and potentially other types
    type ENUM('standard', 'bundle') NOT NULL DEFAULT 'standard', 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES Companies(id) ON DELETE CASCADE,
    -- Ensures SKUs are unique within a company (multi-tenancy)
    UNIQUE KEY unique_sku_per_company (company_id, sku)
);

-- -----------------------------------------------------
-- Table: Inventory
-- Represents the current stock levels for a specific product at a specific warehouse.
-- This is a join-like table, but also holds specific inventory attributes.
-- Added a single 'id' primary key for easier referencing and ORM mapping.
-- -----------------------------------------------------
CREATE TABLE Inventory (
    id INT PRIMARY KEY AUTO_INCREMENT, -- New: Single primary key
    product_id INT NOT NULL,
    warehouse_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0 CHECK (quantity >= 0), -- Quantity cannot be negative
    -- Low stock threshold can vary per product per warehouse
    low_stock_threshold INT DEFAULT 0 CHECK (low_stock_threshold >= 0),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,
    FOREIGN KEY (warehouse_id) REFERENCES Warehouses(id) ON DELETE CASCADE,
    -- Ensures only one inventory record per product-warehouse combination
    UNIQUE KEY unique_product_warehouse (product_id, warehouse_id)
);

-- -----------------------------------------------------
-- Table: InventoryHistory
-- Tracks all changes to inventory levels. This is an append-only log,
-- providing a full audit trail of stock movements.
-- References the single 'id' from the Inventory table.
-- -----------------------------------------------------
CREATE TABLE InventoryHistory (
    id INT PRIMARY KEY AUTO_INCREMENT,
    inventory_id INT NOT NULL, -- References the single PK of the Inventory table
    quantity_change INT NOT NULL, -- The delta (+ve for incoming, -ve for outgoing)
    change_type ENUM('sale', 'restock', 'adjustment', 'transfer_in', 'transfer_out') NOT NULL,
    reason TEXT, -- Optional: A short description for the change
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inventory_id) REFERENCES Inventory(id) ON DELETE CASCADE
    -- No explicit updated_at as this is a history log; timestamp captures creation.
);

-- -----------------------------------------------------
-- Table: Suppliers
-- Represents a supplier entity. Each supplier belongs to a specific company.
-- -----------------------------------------------------
CREATE TABLE Suppliers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT, -- Optional: Supplier address
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES Companies(id) ON DELETE CASCADE,
    UNIQUE KEY unique_supplier_per_company (company_id, name) -- Supplier names unique per company
);

-- -----------------------------------------------------
-- Table: ProductSuppliers
-- Maps products to their suppliers (a many-to-many relationship).
-- A product can have multiple suppliers, and a supplier can provide multiple products.
-- -----------------------------------------------------
CREATE TABLE ProductSuppliers (
    product_id INT NOT NULL,
    supplier_id INT NOT NULL,
    PRIMARY KEY (product_id, supplier_id), -- Composite primary key for the many-to-many link
    FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES Suppliers(id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Table: ProductBundles
-- Supports the "bundle" requirement, defining which products make up a bundle.
-- This is a self-referencing many-to-many relationship on the Products table.
-- 'bundle_product_id' is the product that is a bundle.
-- 'component_product_id' is a standard product that makes up the bundle.
-- -----------------------------------------------------
CREATE TABLE ProductBundles (
    bundle_product_id INT NOT NULL,
    component_product_id INT NOT NULL,
    quantity_in_bundle INT NOT NULL DEFAULT 1 CHECK (quantity_in_bundle >= 1),
    PRIMARY KEY (bundle_product_id, component_product_id),
    FOREIGN KEY (bundle_product_id) REFERENCES Products(id) ON DELETE CASCADE,
    FOREIGN KEY (component_product_id) REFERENCES Products(id) ON DELETE CASCADE,
    -- Ensures a bundle product cannot contain itself as a component
    CONSTRAINT chk_bundle_not_self_contained CHECK (bundle_product_id != component_product_id)
);

