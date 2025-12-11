-- Adds the calories column required by the updated recipe loader
ALTER TABLE receipt_recipe_db.recipes
    ADD COLUMN calories INT NULL AFTER cooking_time;
