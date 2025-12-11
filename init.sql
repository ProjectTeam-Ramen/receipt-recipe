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
    status ENUM('unused','used','deleted') NOT NULL DEFAULT 'unused',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(food_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE user_food_transactions (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    food_id INT NOT NULL,
    user_food_id INT NULL,
    delta_g DECIMAL(10,2) NOT NULL,
    quantity_after_g DECIMAL(10,2) NOT NULL,
    source_type ENUM('manual_add','manual_consume','ocr_import','sync','adjustment','recipe_cook') NOT NULL,
    source_reference VARCHAR(255) NULL,
    note VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(food_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (user_food_id) REFERENCES user_foods(user_food_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE recipes (
    recipe_id INT PRIMARY KEY AUTO_INCREMENT,
    recipe_name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    instructions TEXT NULL,
    cooking_time INT UNSIGNED NULL,
    calories INT NULL,
    image_url VARCHAR(1000) NULL,
    is_japanese TINYINT(1) NOT NULL DEFAULT 0,
    is_western TINYINT(1) NOT NULL DEFAULT 0,
    is_chinese TINYINT(1) NOT NULL DEFAULT 0,
    is_main_dish TINYINT(1) NOT NULL DEFAULT 0,
    is_side_dish TINYINT(1) NOT NULL DEFAULT 0,
    is_soup TINYINT(1) NOT NULL DEFAULT 0,
    is_dessert TINYINT(1) NOT NULL DEFAULT 0,
    type_meat TINYINT(1) NOT NULL DEFAULT 0,
    type_seafood TINYINT(1) NOT NULL DEFAULT 0,
    type_vegetarian TINYINT(1) NOT NULL DEFAULT 0,
    type_composite TINYINT(1) NOT NULL DEFAULT 0,
    type_other TINYINT(1) NOT NULL DEFAULT 0,
    flavor_sweet TINYINT(1) NOT NULL DEFAULT 0,
    flavor_spicy TINYINT(1) NOT NULL DEFAULT 0,
    flavor_salty TINYINT(1) NOT NULL DEFAULT 0,
    texture_stewed TINYINT(1) NOT NULL DEFAULT 0,
    texture_fried TINYINT(1) NOT NULL DEFAULT 0,
    texture_stir_fried TINYINT(1) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE recipe_foods (
    recipe_food_id INT PRIMARY KEY AUTO_INCREMENT,
    recipe_id INT NOT NULL,
    food_id INT NOT NULL,
    quantity_g DECIMAL(10,2) NOT NULL DEFAULT 0.00 CHECK (quantity_g >= 0),
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (food_id) REFERENCES foods(food_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE user_recipe_history (
    history_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    recipe_id INT NOT NULL,
    servings DECIMAL(6,2) NOT NULL DEFAULT 1.00 CHECK (servings > 0),
    calories_total INT NULL,
    cooked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note VARCHAR(255) NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE ON UPDATE CASCADE
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

CREATE TABLE refresh_tokens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    token VARCHAR(512) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);

CREATE INDEX idx_foods_category_id ON foods(category_id);
CREATE INDEX idx_user_foods_user_id ON user_foods(user_id);
CREATE INDEX idx_user_foods_food_id ON user_foods(food_id);
CREATE INDEX idx_user_food_transactions_user_food ON user_food_transactions(user_id, food_id, created_at);
CREATE INDEX idx_user_food_transactions_user_food_id ON user_food_transactions(user_food_id);
CREATE INDEX idx_recipe_foods_recipe_id ON recipe_foods(recipe_id);
CREATE INDEX idx_recipe_foods_food_id ON recipe_foods(food_id);
CREATE INDEX idx_user_recipe_history_user ON user_recipe_history(user_id, cooked_at DESC);
CREATE INDEX idx_user_recipe_history_recipe ON user_recipe_history(recipe_id);
CREATE INDEX idx_receipts_user_id ON receipts(user_id);
CREATE INDEX idx_raw_food_mappings_food_id ON raw_food_mappings(food_id);

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