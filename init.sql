-- 食材管理データベース
CREATE DATABASE IF NOT EXISTS ingredients_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ユーザー情報データベース
CREATE DATABASE IF NOT EXISTS users_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- レシピ情報データベース
CREATE DATABASE IF NOT EXISTS recipes_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ユーザーに権限を付与
GRANT ALL PRIVILEGES ON ingredients_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON users_db.* TO 'user'@'%';
GRANT ALL PRIVILEGES ON recipes_db.* TO 'user'@'%';

FLUSH PRIVILEGES;