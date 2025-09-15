# (Code from Part 2)
-- See the README.md for the full explanation of this design.

-- Represents a business client using the platform
CREATE TABLE Companies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Represents a physical location where products are stored
CREATE TABLE Warehouses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    FOREIGN KEY (company_id) REFERENCES Companies(id) ON DELETE CASCADE,
    UNIQUE KEY unique_warehouse_per_company (company_id, name)
);

-- Represents a product defined within the system
CREATE TABLE Products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES Companies(id) ON DELETE CASCADE,
    UNIQUE KEY unique_sku_per_company (company_id, sku)
);

-- Represents inventory levels for a specific product at a specific warehouse
CREATE TABLE Inventory (
    product_id INT NOT NULL,
    warehouse_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    low_stock_threshold INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, warehouse_id),
    FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,
    FOREIGN KEY (warehouse_id) REFERENCES Warehouses(id) ON DELETE CASCADE
);

-- Tracks changes to inventory levels
CREATE TABLE InventoryHistory (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    warehouse_id INT NOT NULL,
    quantity_change INT NOT NULL,
    change_type ENUM('sale', 'restock', 'adjustment') NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id, warehouse_id) REFERENCES Inventory(product_id, warehouse_id)
);

-- Represents a supplier for products
CREATE TABLE Suppliers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    phone VARCHAR(20),
    FOREIGN KEY (company_id) REFERENCES Companies(id) ON DELETE CASCADE
);

-- Maps products to their suppliers (many-to-many relationship)
CREATE TABLE ProductSuppliers (
    product_id INT NOT NULL,
    supplier_id INT NOT NULL,
    PRIMARY KEY (product_id, supplier_id),
    FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES Suppliers(id) ON DELETE CASCADE
);

-- Supports the "bundle" requirement
CREATE TABLE ProductBundles (
    bundle_product_id INT NOT NULL,
    component_product_id INT NOT NULL,
    quantity_in_bundle INT NOT NULL DEFAULT 1,
    PRIMARY KEY (bundle_product_id, component_product_id),
    FOREIGN KEY (bundle_product_id) REFERENCES Products(id) ON DELETE CASCADE,
    FOREIGN KEY (component_product_id) REFERENCES Products(id) ON DELETE CASCADE,
    CONSTRAINT chk_bundle_not_self_contained CHECK (bundle_product_id != component_product_id)
);