import pandas as pd
import json

# Load the dataset
print("Loading dataset...")
df = pd.read_csv('/home/ubuntu/upload/recipe-backend/src/data/recipes_full.csv')

print(f"Dataset shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print("\nColumn data types:")
print(df.dtypes)

print("\nSample data for key columns:")
sample_row = df.iloc[0]

print(f"\nRecipeId: {sample_row['RecipeId']}")
print(f"Name: {sample_row['Name']}")
print(f"Images: {sample_row['Images']}")
print(f"RecipeIngredientQuantities: {sample_row['RecipeIngredientQuantities'][:200]}...")
print(f"RecipeIngredientParts: {sample_row['RecipeIngredientParts'][:200]}...")
print(f"RecipeInstructions: {sample_row['RecipeInstructions'][:200]}...")

print("\nChecking for null values in key columns:")
key_columns = ['Images', 'RecipeIngredientQuantities', 'RecipeIngredientParts', 'RecipeInstructions']
for col in key_columns:
    null_count = df[col].isnull().sum()
    print(f"{col}: {null_count} null values ({null_count/len(df)*100:.1f}%)")

print("\nSample of non-null Images:")
non_null_images = df[df['Images'].notna()]['Images'].head(5)
for i, img in enumerate(non_null_images):
    print(f"{i+1}: {img}")

print("\nSample of RecipeIngredientParts:")
sample_ingredients = df[df['RecipeIngredientParts'].notna()]['RecipeIngredientParts'].head(3)
for i, ing in enumerate(sample_ingredients):
    print(f"{i+1}: {ing[:300]}...")

