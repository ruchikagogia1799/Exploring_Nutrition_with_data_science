# build_usda_clean.py
# Usage:
#   python build_usda_clean.py
#
# What it does:
# 1) Ensures USDA raw files exist in usda_raw/
#    - If missing, downloads a ZIP from Google Drive and extracts it
# 2) Builds data_out/usda_food_clean.csv

import os
import shutil
import zipfile
from pathlib import Path

import pandas as pd

# -----------------------------
# Google Drive ZIP (your link)
# -----------------------------
# https://drive.google.com/file/d/1tR6mmw-gbH7cZlHig497wC9yXNyg-kEv/view?usp=sharing
DRIVE_FILE_ID = "1tR6mmw-gbH7cZlHig497wC9yXNyg-kEv"

RAW_DIR = Path("usda_raw")
OUT_DIR = Path("data_out")
OUT_DIR.mkdir(exist_ok=True)

FOOD_PATH = RAW_DIR / "food.csv"
CAT_PATH = RAW_DIR / "food_category.csv"
NUTRIENT_PATH = RAW_DIR / "nutrient.csv"
FOOD_NUTRIENT_PATH = RAW_DIR / "food_nutrient.csv"

OUT_CSV = OUT_DIR / "usda_food_clean.csv"


# -----------------------------
# Download + Extract helpers
# -----------------------------
def _raw_files_present() -> bool:
    return all(p.exists() for p in [FOOD_PATH, CAT_PATH, NUTRIENT_PATH, FOOD_NUTRIENT_PATH])


def ensure_raw_data_from_drive():
    """
    Download a ZIP from Google Drive and extract it into usda_raw/ if raw files are missing.

    Requirements:
      pip install gdown
    """
    if _raw_files_present():
        print("✅ Raw files already present in usda_raw/. Skipping download.")
        return

    try:
        import gdown
    except ImportError:
        raise SystemExit(
            "❌ Missing dependency: gdown\n\n"
            "Install it with:\n"
            "  pip install gdown\n"
            "Then rerun:\n"
            "  python build_usda_clean.py"
        )

    RAW_DIR.mkdir(exist_ok=True)

    zip_path = Path("usda_raw.zip")
    url = f"https://drive.google.com/uc?id={DRIVE_FILE_ID}"

    print("⬇️  Downloading USDA raw ZIP from Google Drive...")
    gdown.download(url, str(zip_path), quiet=False)

    if not zip_path.exists():
        raise SystemExit("❌ Download failed: ZIP file not found after download.")

    print("📦 Extracting ZIP...")
    extract_tmp = RAW_DIR / "__extract_tmp__"
    if extract_tmp.exists():
        shutil.rmtree(extract_tmp)
    extract_tmp.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_tmp)

    # The ZIP might contain files directly OR inside a folder.
    # We search for the 4 required files anywhere under extract_tmp and move them into RAW_DIR.
    needed = {
        "food.csv": None,
        "food_nutrient.csv": None,
        "food_category.csv": None,
        "nutrient.csv": None,
    }

    for p in extract_tmp.rglob("*.csv"):
        name = p.name.lower()
        if name in needed and needed[name] is None:
            needed[name] = p

    missing = [k for k, v in needed.items() if v is None]
    if missing:
        # cleanup
        shutil.rmtree(extract_tmp, ignore_errors=True)
        zip_path.unlink(missing_ok=True)
        raise SystemExit(
            "❌ ZIP extracted but required files are missing:\n"
            f"   {missing}\n\n"
            "Make sure your ZIP contains exactly these files:\n"
            "  food.csv, food_nutrient.csv, food_category.csv, nutrient.csv"
        )

    # Move files into RAW_DIR (overwrite if present)
    for fname, src in needed.items():
        dst = RAW_DIR / fname
        shutil.move(str(src), str(dst))

    # cleanup
    shutil.rmtree(extract_tmp, ignore_errors=True)
    zip_path.unlink(missing_ok=True)

    if not _raw_files_present():
        raise SystemExit("❌ Extraction finished, but raw files are still not found in usda_raw/.")

    print("✅ Raw USDA files ready in usda_raw/.")


def read_csv_robust(path: Path) -> pd.DataFrame:
    for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="latin1", low_memory=False)


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    # 1) Ensure raw data exists (download ZIP if needed)
    ensure_raw_data_from_drive()

    print("Reading files...")
    food = read_csv_robust(FOOD_PATH)
    food_cat = read_csv_robust(CAT_PATH)
    nutrient = read_csv_robust(NUTRIENT_PATH)
    food_nutrient = read_csv_robust(FOOD_NUTRIENT_PATH)

    # --- keep only columns we need ---
    food_cols = [c for c in ["fdc_id", "description", "food_category_id"] if c in food.columns]
    food = food[food_cols].copy()

    cat_cols = [c for c in ["id", "description"] if c in food_cat.columns]
    food_cat = food_cat[cat_cols].copy()
    food_cat = food_cat.rename(columns={"id": "food_category_id", "description": "Category"})

    nut_cols = [c for c in ["id", "name", "unit_name", "nutrient_nbr"] if c in nutrient.columns]
    nutrient = nutrient[nut_cols].copy()
    nutrient = nutrient.rename(columns={"id": "nutrient_id", "name": "nutrient_name"})

    fn_cols = [c for c in ["fdc_id", "nutrient_id", "amount"] if c in food_nutrient.columns]
    food_nutrient = food_nutrient[fn_cols].copy()

    # -----------------------------
    # Force merge keys to same dtype
    # -----------------------------
    if "food_category_id" in food.columns:
        food["food_category_id"] = pd.to_numeric(food["food_category_id"], errors="coerce").astype("Int64")
    food_cat["food_category_id"] = pd.to_numeric(food_cat["food_category_id"], errors="coerce").astype("Int64")

    food["fdc_id"] = pd.to_numeric(food["fdc_id"], errors="coerce").astype("Int64")
    food_nutrient["fdc_id"] = pd.to_numeric(food_nutrient["fdc_id"], errors="coerce").astype("Int64")

    nutrient["nutrient_id"] = pd.to_numeric(nutrient["nutrient_id"], errors="coerce").astype("Int64")
    food_nutrient["nutrient_id"] = pd.to_numeric(food_nutrient["nutrient_id"], errors="coerce").astype("Int64")

    # nutrient_nbr can contain decimals like 269.3 in some FDC exports → make a safe int version
    if "nutrient_nbr" in nutrient.columns:
        nn = pd.to_numeric(nutrient["nutrient_nbr"], errors="coerce")
        nutrient["nutrient_nbr_int"] = nn.astype("Float64").floordiv(1).astype("Int64")

    # Drop rows with missing keys
    food = food.dropna(subset=["fdc_id"])
    food_nutrient = food_nutrient.dropna(subset=["fdc_id", "nutrient_id"])

    # -----------------------------
    # Join tables
    # -----------------------------
    print("Joining tables...")
    df = food_nutrient.merge(nutrient, on="nutrient_id", how="left")
    df = df.merge(food, on="fdc_id", how="left")
    df = df.merge(food_cat, on="food_category_id", how="left")

    # After merges: food.description is currently called "description"
    # Rename to "Food" (and keep Category column)
    if "description" in df.columns:
        df = df.rename(columns={"description": "Food"})

    # -----------------------------
    # USDA stable nutrient mapping (by nutrient number)
    # 208 Energy, 203 Protein, 205 Carbs, 204 Fat, 291 Fiber, 269 Total sugars
    # -----------------------------
    wanted_nbr_map = {
        208: "Calories (kcal)",
        203: "Protein (g)",
        205: "Carbs (g)",
        204: "Fat (g)",
        291: "Fiber (g)",
        269: "Sugar (g)",
    }

    print("Filtering nutrients...")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    use_nbr = "nutrient_nbr_int" in df.columns and df["nutrient_nbr_int"].notna().any()

    if use_nbr:
        df = df[df["nutrient_nbr_int"].isin(list(wanted_nbr_map.keys()))].copy()
        df["Metric"] = df["nutrient_nbr_int"].map(wanted_nbr_map)
    else:
        # fallback: name-based (less reliable across exports)
        wanted_names_map = {
            "Energy": "Calories (kcal)",
            "Protein": "Protein (g)",
            "Carbohydrate, by difference": "Carbs (g)",
            "Total lipid (fat)": "Fat (g)",
            "Fiber, total dietary": "Fiber (g)",
            "Sugars, Total": "Sugar (g)",
            "Sugars, total": "Sugar (g)",
            "Sugars, total including NLEA": "Sugar (g)",
            "Total Sugars": "Sugar (g)",
        }
        df = df[df["nutrient_name"].isin(wanted_names_map.keys())].copy()
        df["Metric"] = df["nutrient_name"].map(wanted_names_map)

    # -----------------------------
    # Pivot to wide
    # -----------------------------
    print("Pivoting to wide format...")
    wide = (
        df.pivot_table(
            index=["fdc_id", "Food", "Category"],
            columns="Metric",
            values="amount",
            aggfunc="max",
        )
        .reset_index()
    )

    expected = ["Calories (kcal)", "Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)", "Sugar (g)"]
    for col in expected:
        if col not in wide.columns:
            wide[col] = pd.NA

    wide = wide.dropna(subset=["Food"])
    wide = wide.dropna(subset=expected, how="all")

    print(f"Saving: {OUT_CSV}")
    wide.to_csv(OUT_CSV, index=False)

    print("\nDONE ✅")
    print("Output columns:", list(wide.columns))
    print("Rows:", len(wide))

    if "Sugar (g)" in wide.columns:
        print("Sugar non-null:", int(wide["Sugar (g)"].notna().sum()))
        print("Sugar max:", wide["Sugar (g)"].max())
