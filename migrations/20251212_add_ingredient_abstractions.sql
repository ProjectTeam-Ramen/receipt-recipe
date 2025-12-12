-- Create table to store abstracted ingredient mappings shared across users
CREATE TABLE IF NOT EXISTS receipt_recipe_db.ingredient_abstractions (
    abstraction_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    normalized_text VARCHAR(255) NOT NULL,
    original_text VARCHAR(255) NULL,
    resolved_food_name VARCHAR(255) NOT NULL,
    food_id INT NULL,
    confidence DECIMAL(5,4) NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'ocr_predict',
    metadata JSON NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    CONSTRAINT pk_ingredient_abstractions PRIMARY KEY (abstraction_id),
    CONSTRAINT uq_ingredient_abstractions_normalized UNIQUE (normalized_text),
    CONSTRAINT fk_ingredient_abstractions_food FOREIGN KEY (food_id)
        REFERENCES receipt_recipe_db.foods (food_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE INDEX idx_ingredient_abstractions_food_id
    ON receipt_recipe_db.ingredient_abstractions (food_id);

CREATE INDEX idx_ingredient_abstractions_resolved_food_name
    ON receipt_recipe_db.ingredient_abstractions (resolved_food_name);
