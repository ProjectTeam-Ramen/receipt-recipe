ALTER TABLE receipt_recipe_db.user_food_transactions
    MODIFY COLUMN source_type ENUM('manual_add','manual_consume','ocr_import','sync','adjustment','recipe_cook') NOT NULL;
