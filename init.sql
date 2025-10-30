-- 食材管理データベース
CREATE DATABASE IF NOT EXISTS ingredients_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ユーザー情報データベース
CREATE DATABASE IF NOT EXISTS users_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 食材カテゴリデータベース
CREATE DATABASE IF NOT EXISTS food_categories_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 食材マスターデータベース
CREATE DATABASE IF NOT EXISTS foods_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ユーザー所有食材データベース
CREATE DATABASE IF NOT EXISTS user_foods_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- レシピデータベース
CREATE DATABASE IF NOT EXISTS recipes_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- レシピ材料データベース
CREATE DATABASE IF NOT EXISTS recipe_foods_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- レシートデータベース
CREATE DATABASE IF NOT EXISTS receipts_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 読み取り食材辞書データベース
CREATE DATABASE IF NOT EXISTS raw_food_mappings_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- レシート明細データベース
CREATE DATABASE IF NOT EXISTS receipt_details_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ユーザーに権限を付与
GRANT ALL PRIVILEGES ON users_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON food_categories_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON foods_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON user_foods_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON recipes_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON recipe_foods_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON receipts_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON raw_food_mappings_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON receipt_details_db.* TO 'user'@'%';

FLUSH PRIVILEGES;