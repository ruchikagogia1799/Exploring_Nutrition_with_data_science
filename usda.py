# usda_preprocess.py
import pandas as pd

# Load main tables
food = pd.read_csv("food.csv")
food_cat = pd.read_csv("food_category.csv")
food_nutrient = pd.read_csv("food_nutrient.csv")
nutrient = pd.read_csv("nutrient.csv")

# Merge food with categories
food = food.merge(food_cat, left_on="food_category_id", right_on="id", how="left", suffixes=("", "_cat"))

# Merge nutrients with nutrient info
food_nutrient = food_nutrient.merge(nutrient, left_on="nutrient_id", right_on="id", how="left", suffixes=("", "_nutrient"))

# Merge everything together
food_full = food_nutrient.merge(food, left_on="fdc_id", right_on="fdc_id", how="left")

# Keep only useful columns
food_full = food_full[[
    "fdc_id",
    "description",        # Food name
    "food_category",      # Category
    "name",               # Nutrient name
    "amount",             # Nutrient amount
    "unit_name"           # Unit
]]

# Rename columns for clarity
food_full = food_full.rename(columns={
    "description": "Food",
    "food_category": "Category",
    "name": "Nutrient",
    "amount": "Value",
    "unit_name": "Unit"
})

# Save clean CSV
food_full.to_csv("usda_clean.csv", index=False)

print("✅ Clean file saved as usda_clean.csv")
print(food_full.head(10))
