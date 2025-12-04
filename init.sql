-- レシートOCR読み取り・食材管理・レシピ提案アプリ用データベーススキーマ

CREATE DATABASE IF NOT EXISTS receipt_recipe_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE receipt_recipe_db;

CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    birthday DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE food_categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE foods (
    food_id INT PRIMARY KEY AUTO_INCREMENT,
    food_name VARCHAR(200) NOT NULL UNIQUE,
    category_id INT NOT NULL,
    is_trackable TINYINT(1) NOT NULL DEFAULT 1,
    FOREIGN KEY (category_id) REFERENCES food_categories(category_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE user_foods (
    user_food_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    food_id INT NOT NULL,
    quantity_g DECIMAL(10,2) NOT NULL DEFAULT 0.00 CHECK (quantity_g >= 0),
    expiration_date DATE NULL,
    purchase_date DATE NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(food_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE recipes (
    recipe_id INT PRIMARY KEY AUTO_INCREMENT,
    recipe_name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    instructions TEXT NULL,
    cooking_time INT UNSIGNED NULL,
    image_url VARCHAR(1000) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE recipe_foods (
    recipe_food_id INT PRIMARY KEY AUTO_INCREMENT,
    recipe_id INT NOT NULL,
    food_id INT NOT NULL,
    quantity_g DECIMAL(10,2) NOT NULL DEFAULT 0.00 CHECK (quantity_g >= 0),
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(food_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE receipts (
    receipt_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    store_name VARCHAR(255) NULL,
    purchase_datetime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE raw_food_mappings (
    mapping_id INT PRIMARY KEY AUTO_INCREMENT,
    raw_name VARCHAR(255) NOT NULL UNIQUE,
    food_id INT NULL,
    status VARCHAR(50) NOT NULL DEFAULT '未処理',
    FOREIGN KEY (food_id) REFERENCES foods(food_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE receipt_details (
    detail_id INT PRIMARY KEY AUTO_INCREMENT,
    receipt_id INT NOT NULL,
    mapping_id INT NOT NULL,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00 CHECK (price >= 0),
    quantity DECIMAL(10,2) NOT NULL DEFAULT 1.00 CHECK (quantity >= 0),
    FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (mapping_id) REFERENCES raw_food_mappings(mapping_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_foods_category_id ON foods(category_id);
CREATE INDEX idx_user_foods_user_id ON user_foods(user_id);
CREATE INDEX idx_user_foods_food_id ON user_foods(food_id);
CREATE INDEX idx_recipe_foods_recipe_id ON recipe_foods(recipe_id);
CREATE INDEX idx_recipe_foods_food_id ON recipe_foods(food_id);
CREATE INDEX idx_receipts_user_id ON receipts(user_id);
CREATE INDEX idx_raw_food_mappings_food_id ON raw_food_mappings(food_id);
CREATE INDEX idx_receipt_details_receipt_id ON receipt_details(receipt_id);
CREATE INDEX idx_receipt_details_mapping_id ON receipt_details(mapping_id);

DELIMITER //

CREATE TRIGGER check_trackable_before_insert_user_foods
BEFORE INSERT ON user_foods
FOR EACH ROW
BEGIN
    DECLARE trackable TINYINT(1);
    SELECT is_trackable INTO trackable FROM foods WHERE food_id = NEW.food_id;
    IF trackable = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cannot insert non-trackable food into user_foods';
    END IF;
END//

CREATE TRIGGER check_trackable_before_update_user_foods
BEFORE UPDATE ON user_foods
FOR EACH ROW
BEGIN
    DECLARE trackable TINYINT(1);
    SELECT is_trackable INTO trackable FROM foods WHERE food_id = NEW.food_id;
    IF trackable = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cannot update to non-trackable food in user_foods';
    END IF;
END//

DELIMITER ;

GRANT ALL PRIVILEGES ON receipt_recipe_db.* TO 'user'@'%';
FLUSH PRIVILEGES;