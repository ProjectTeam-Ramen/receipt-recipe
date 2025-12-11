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

CREATE INDEX idx_user_recipe_history_user ON user_recipe_history(user_id, cooked_at DESC);
CREATE INDEX idx_user_recipe_history_recipe ON user_recipe_history(recipe_id);
