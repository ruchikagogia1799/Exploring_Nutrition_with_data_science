from pathlib import Path
import re
import numpy as np
import pandas as pd

# --------- Paths (edit if needed) ----------
SRC = Path("diet_corrected.csv")         # your messy input file
DST = Path("diet_clean.csv")             # cleaned file for the app
DST_DEBUG = Path("diet_clean_debug.csv") # cleaned + original category

# --------- Column name detection ----------
RENAME_CANDIDATES = {
    "food"          : ["food", "food_item", "item", "name", "dish"],
    "category"      : ["category", "group", "category_original", "cat"],
    "calories_kcal" : ["calories (kcal)", "kcal", "calories", "energy_kcal"],
    "protein_g"     : ["protein (g)", "protein_g", "protein"],
    "carbs_g"       : ["carbohydrates (g)", "carbs_g", "carbs", "carbohydrate"],
    "fat_g"         : ["fats (g)", "fat (g)", "fat_g", "fats", "fat"],
    "fiber_g"       : ["fibre (g)", "fiber (g)", "fibre_g", "fiber_g", "fibre", "fiber"],
    "sugar_g"       : ["sugars (g)", "sugar (g)", "sugars", "sugar_g", "total_sugars"],
}

NUMERIC_STD_COLS = ["calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g"]

# --------- Helpers ----------
def pick_col(df: pd.DataFrame, candidates):
    """Return the first matching column (case/space-insensitive) or None."""
    norm = {c: re.sub(r"\s+", "", c.strip().lower()) for c in df.columns}
    for want in candidates:
        want_n = re.sub(r"\s+", "", want.strip().lower())
        # exact after normalization
        for raw, n in norm.items():
            if n == want_n:
                return raw
        # substring fallback
        for raw, n in norm.items():
            if want_n in n:
                return raw
    return None

def coalesce_columns(df: pd.DataFrame, target: str, options: list[str]):
    """Create/overwrite df[target] from the first available option column(s)."""
    found = [c for c in options if c in df.columns]
    if not found:
        return df
    base = pd.to_numeric(df[found[0]], errors="coerce") if target in NUMERIC_STD_COLS else df[found[0]]
    for c in found[1:]:
        alt = pd.to_numeric(df[c], errors="coerce") if target in NUMERIC_STD_COLS else df[c]
        base = base.fillna(alt)
    df[target] = base
    return df

# ------- Category re-mapper (rule-based) -------
FRUIT_WORDS = set("""
apple apricot avocado banana berry blackcurrant blueberry cherry coconut cranberry custard-apple
date dragonfruit fig goava guava grape grapefruit jackfruit jamun jujube kiwi lemon lime litchi lychee
mango melon muskmelon orange papaya peach pear pineapple plum pomegranate raisin rambutan strawberry
tangerine watermelon sapodilla chikoo mulberry currant gooseberry soursop passionfruit
""".split())

VEG_WORDS = set("""
amaranth arugula asparagus beet beetroot bell-pepper bitter-gourd bottlegourd broccoli cabbage carrot
cauliflower celery chard corn cucumber eggplant brinjal french-bean garlic ginger kale leek lettuce
mushroom mustard-greens okra ladies-finger onion pea peas pepper potato pumpkin radish spinach squash
sweet-potato tomato turnip yam zucchini capsicum
""".split())

GRAIN_WORDS = set("""
atta barley bread bun burger brioche chapati cereal cornflakes couscous cracker dosa flatbread idli
millet muesli naan noodle oats pasta poha porridge quinoa rice roti semolina sev vermicelli wheat wrap
tortilla paratha puffedrice khichdi kichdi upma pulao biryani khakhra papad khichri khichuri
""".split())

PULSE_WORDS = set("""
bean beans blackgram black-eyed-pea chickpea chana chole dal daal dhuli rajma lentil moong mung masoor
pigeon-pea toor tur urad pea peas soy soya tofu tempeh hummus pea-protein
""".split())

MEAT_WORDS = set("""
chicken mutton lamb pork beef turkey ham bacon salami sausage kebab kheema keema mince liver offal
""".split())

SEAFOOD_WORDS = set("""
fish prawn shrimp crab lobster squid tuna salmon sardine mackerel anchovy hilsa pomfret rohu catla
""".split())

DAIRY_EGGS_WORDS = set("""
milk curd yogurt dahi paneer cheese ghee butter cream whey kefir buttermilk lassi egg omelet omelette
""".split())

OILS_FATS_WORDS = set("""
oil ghee butter shortening lard tallow margarine
""".split())

CONDIMENT_WORDS = set("""
chutney pickle achaar achar ketchup mayo mayonnaise mustard relish salsa sauce sriracha pesto dressing
vinegar seasoning masala spice rub gravy paste extract essence bouillon stock cube jam marmalade spread
""".split())

DESSERT_WORDS = set("""
barfi burfi laddoo laddu halwa kheer payasam rasgulla gulab jamun jalebi peda sandesh malpua ladoo
cake tart pie brownie cookie biscuit muffin pudding custard candy chocolate sweet toffee fudge ice-cream
khoya khoya khoya-khoya khoa rabri rasmalai kheer phirni basundi shrikhand
""".split())

BEVERAGE_WORDS = set("""
juice soda cola shake smoothie tea coffee latte cappuccino mocha lassi buttermilk milkshake cocoa
horlicks bournvita malt drink lemonade squash cordial beer wine alcohol cocktail mocktail
""".split())

NON_EDIBLE_TERMS = [
    "yeast", "baker", "nutritional yeast", "essence", "flavour", "flavor",
    "food color", "food colour", "coloring", "colouring", "stock cube", "bouillon",
    "premix", "mix", "seasoning", "spice mix", "masala powder", "leavening", "baking powder",
    "gelatin powder", "agar", "icing", "fondant"
]

def contains_any(text: str, words: set[str] | list[str]) -> bool:
    t = " " + re.sub(r"[^a-z0-9]+", " ", str(text).lower()) + " "
    return any((" " + w + " ") in t for w in words)

def classify(food: str, original_cat: str) -> str:
    f = str(food).lower()

    # desserts first: fruit cakes/pies should not land in Fruits
    if contains_any(f, DESSERT_WORDS):
        return "Sweets & Desserts"

    # beverages
    if contains_any(f, BEVERAGE_WORDS):
        return "Beverages"

    # condiments & spreads
    if contains_any(f, CONDIMENT_WORDS):
        return "Condiments & Spreads"

    # oils & fats (pure fats, clarified butter etc.)
    if contains_any(f, OILS_FATS_WORDS):
        return "Oils & Fats"

    # dairy & eggs
    if contains_any(f, DAIRY_EGGS_WORDS):
        return "Dairy & Eggs"

    # grains & breads
    if contains_any(f, GRAIN_WORDS):
        return "Grains & Breads"

    # pulses & legumes (incl. tofu/soya products)
    if contains_any(f, PULSE_WORDS):
        return "Pulses & Legumes"

    # seafood
    if contains_any(f, SEAFOOD_WORDS):
        return "Seafood"

    # meat & poultry
    if contains_any(f, MEAT_WORDS):
        return "Meat & Poultry"

    # vegetables (before fruits to catch tomato, cucumber etc.)
    if contains_any(f, VEG_WORDS):
        return "Vegetables"

    # fruits (strictly raw/whole fruit words)
    if contains_any(f, FRUIT_WORDS):
        # prevent “orange cake”, “lemon tart”, “pineapple juice” from going to Fruits
        if contains_any(f, DESSERT_WORDS) or contains_any(f, BEVERAGE_WORDS) or "jam" in f or "marmalade" in f:
            return "Sweets & Desserts" if contains_any(f, DESSERT_WORDS) or "jam" in f or "marmalade" in f else "Beverages"
        return "Fruits"

    # prepared meals / soups
    if any(w in f for w in ["soup", "curry", "stew", "entree", "meal", "biryani", "pulao", "pav bhaji", "khichdi"]):
        return "Prepared Meals & Soups"

    # fallback: keep original if present, else Other
    if isinstance(original_cat, str) and original_cat.strip():
        return original_cat.strip()
    return "Other"

# --------- Cleaning pipeline ----------
def main():
    if not SRC.exists():
        raise FileNotFoundError(f"CSV not found: {SRC.resolve()}")

    df = pd.read_csv(SRC, encoding_errors="ignore")
    # drop duplicate-named columns
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Build rename map dynamically
    rename_map = {}
    for std, cands in RENAME_CANDIDATES.items():
        found = pick_col(df, cands)
        if found:
            rename_map[found] = std

    df = df.rename(columns=rename_map)
    # Coalesce (handles cases with both “Sugars (g)” & “Sugars”, etc.)
    for std, cands in RENAME_CANDIDATES.items():
        cols_present = [c for c in df.columns if c.lower() in [x.lower() for x in cands]]
        if cols_present:
            df = coalesce_columns(df, std, cols_present)

    # Minimal required fields
    required = ["food","category","calories_kcal","protein_g","carbs_g","fat_g"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        # try last-chance inference for category/food
        if "category" in missing:
            guess = pick_col(df, ["category","group","type"])
            if guess:
                df["category"] = df[guess]
                missing.remove("category")
        if "food" in missing:
            guess = pick_col(df, ["food","food_item","name","item","title"])
            if guess:
                df["food"] = df[guess]
                missing.remove("food")

    still_missing = [c for c in required if c not in df.columns]
    if still_missing:
        raise ValueError(f"Missing required columns after normalization: {still_missing}\nGot: {list(df.columns)}")

    # Keep a copy of original category
    df["category_original"] = df["category"].astype(str)

    # Normalize strings
    df["food"] = df["food"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()

    # Remove obvious non-edible / ingredient-only rows
    mask_non_edible = df["food"].str.lower().str.contains("|".join([re.escape(t) for t in NON_EDIBLE_TERMS]), na=False)
    removed_non_edible = int(mask_non_edible.sum())
    df = df.loc[~mask_non_edible].copy()

    # Reclassify with rules
    df["category"] = [
        classify(f, c) for f, c in zip(df["food"].astype(str), df["category_original"].astype(str))
    ]

    # Numeric fixes
    for c in NUMERIC_STD_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).clip(lower=0)

    # sugar ≤ carbs
    if {"sugar_g","carbs_g"}.issubset(df.columns):
        df["sugar_g"] = np.minimum(df["sugar_g"], df["carbs_g"])

    # enforce totals ≤ 100 g (scale down uniformly if needed)
    p = pd.to_numeric(df.get("protein_g", 0), errors="coerce").fillna(0)
    ch = pd.to_numeric(df.get("carbs_g", 0), errors="coerce").fillna(0)
    fa = pd.to_numeric(df.get("fat_g", 0), errors="coerce").fillna(0)
    total = p + ch + fa
    scale = (100 / total.replace(0, np.nan)).where(total > 100, 1).fillna(1)
    df["protein_g"] = (p * scale).round(2)
    df["carbs_g"]   = (ch * scale).round(2)
    df["fat_g"]     = (fa * scale).round(2)

    # derived metric
    df["protein_per_100kcal"] = (df["protein_g"] / (df["calories_kcal"].replace(0, np.nan) / 100.0)).replace([np.inf, -np.inf], np.nan).fillna(0).round(4)

    # Tidy columns & order
    order = ["food","category","calories_kcal","protein_g","carbs_g","fat_g","fiber_g","sugar_g","protein_per_100kcal","category_original"]
    cols = [c for c in order if c in df.columns] + [c for c in df.columns if c not in order]
    df = df[cols]

    # Save
    df.to_csv(DST_DEBUG, index=False)
    df.drop(columns=["category_original"], inplace=True)
    df.to_csv(DST, index=False)

    # Audit report
    print("✅ Cleaned CSV saved:")
    print(f"   - {DST.resolve()}")
    print(f"   - {DST_DEBUG.resolve()}  (with category_original for auditing)")
    print()
    print("📊 Category counts (after cleaning):")
    print(df["category"].value_counts().sort_index())
    print()
    print(f"🗑️ Removed non-edible rows: {removed_non_edible}")

if __name__ == "__main__":
    main()
