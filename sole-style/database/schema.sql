-- MySQL 8+ reference schema. The Flask application creates the same tables via SQLAlchemy.
CREATE DATABASE IF NOT EXISTS sole_style CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sole_style;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(180) NOT NULL UNIQUE,
  phone VARCHAR(40) NOT NULL DEFAULT '',
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'customer',
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_users_role_active (role, active)
) ENGINE=InnoDB;

CREATE TABLE categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  slug VARCHAR(90) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE brands (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(180) NOT NULL,
  slug VARCHAR(200) NOT NULL UNIQUE,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  compare_at DECIMAL(10,2),
  image VARCHAR(500),
  category_id INT NOT NULL,
  brand_id INT NOT NULL,
  gender VARCHAR(30) NOT NULL DEFAULT 'Unisex',
  featured BOOLEAN NOT NULL DEFAULT FALSE,
  bestseller BOOLEAN NOT NULL DEFAULT FALSE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(id),
  CONSTRAINT fk_products_brand FOREIGN KEY (brand_id) REFERENCES brands(id),
  INDEX ix_products_active_created (active, created_at),
  INDEX ix_products_name (name)
) ENGINE=InnoDB;
CREATE TABLE variants (
  id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  size VARCHAR(20) NOT NULL,
  color VARCHAR(40) NOT NULL,
  stock INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_variants_product FOREIGN KEY (product_id) REFERENCES products(id),
  CONSTRAINT uq_variant_product_size_color UNIQUE (product_id, size, color),
  INDEX ix_variants_product (product_id)
) ENGINE=InnoDB;
CREATE TABLE cart_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  variant_id INT NOT NULL,
  quantity INT NOT NULL DEFAULT 1,
  CONSTRAINT fk_cart_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_cart_variant FOREIGN KEY (variant_id) REFERENCES variants(id),
  CONSTRAINT uq_cart_user_variant UNIQUE (user_id, variant_id),
  INDEX ix_cart_user (user_id)
) ENGINE=InnoDB;
CREATE TABLE wishlists (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  product_id INT NOT NULL,
  CONSTRAINT fk_wishlist_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_wishlist_product FOREIGN KEY (product_id) REFERENCES products(id),
  CONSTRAINT uq_wishlist_user_product UNIQUE (user_id, product_id),
  INDEX ix_wishlist_user (user_id)
) ENGINE=InnoDB;
CREATE TABLE bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(32) NOT NULL UNIQUE,
  user_id INT NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'Pending Confirmation',
  total DECIMAL(10,2) NOT NULL,
  customer_note VARCHAR(500) NOT NULL DEFAULT '',
  admin_note VARCHAR(1000) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_bookings_user FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX ix_bookings_user_created (user_id, created_at),
  INDEX ix_bookings_status_created (status, created_at)
) ENGINE=InnoDB;
CREATE TABLE booking_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  product_name VARCHAR(180) NOT NULL,
  image VARCHAR(500) NOT NULL DEFAULT '',
  size VARCHAR(20) NOT NULL,
  color VARCHAR(40) NOT NULL,
  quantity INT NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  variant_id INT NULL,
  CONSTRAINT fk_booking_item_booking FOREIGN KEY (booking_id) REFERENCES bookings(id),
  CONSTRAINT fk_booking_item_variant FOREIGN KEY (variant_id) REFERENCES variants(id) ON DELETE SET NULL
) ENGINE=InnoDB;
CREATE TABLE notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(150) NOT NULL,
  message VARCHAR(500) NOT NULL,
  `read` BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX ix_notifications_user_read_created (user_id, `read`, created_at)
) ENGINE=InnoDB;
CREATE TABLE activity (
  id INT AUTO_INCREMENT PRIMARY KEY,
  admin_id INT NOT NULL,
  action VARCHAR(240) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_activity_admin FOREIGN KEY (admin_id) REFERENCES users(id)
) ENGINE=InnoDB;
CREATE TABLE setting (
  `key` VARCHAR(80) PRIMARY KEY,
  value VARCHAR(500) NOT NULL
) ENGINE=InnoDB;
