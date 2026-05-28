import pandas as pd
import json
import os

# Path to your CSV files
DATA_DIR = "data/"

# Relationships from the Kaggle ER diagram
RELATIONSHIPS = [
    {"from_table": "orders", "from_column": "customer_id", "to_table": "customers", "to_column": "customer_id", "description": "each order belongs to one customer"},
    {"from_table": "orders", "from_column": "order_id", "to_table": "order_items", "to_column": "order_id", "description": "one order has multiple items"},
    {"from_table": "orders", "from_column": "order_id", "to_table": "order_payments", "to_column": "order_id", "description": "one order has one or more payments"},
    {"from_table": "orders", "from_column": "order_id", "to_table": "order_reviews", "to_column": "order_id", "description": "one order can have one review"},
    {"from_table": "order_items", "from_column": "product_id", "to_table": "products", "to_column": "product_id", "description": "each order item is a product"},
    {"from_table": "order_items", "from_column": "seller_id", "to_table": "sellers", "to_column": "seller_id", "description": "each order item is sold by a seller"},
    {"from_table": "products", "from_column": "product_category_name", "to_table": "product_category_name_translation", "to_column": "product_category_name", "description": "translates category name to english"},
    {"from_table": "customers", "from_column": "customer_zip_code_prefix", "to_table": "geolocation", "to_column": "geolocation_zip_code_prefix", "description": "customer location coordinates"},
    {"from_table": "sellers", "from_column": "seller_zip_code_prefix", "to_table": "geolocation", "to_column": "geolocation_zip_code_prefix", "description": "seller location coordinates"}
]

def infer_type(dtype):
    if "int" in str(dtype): return "int"
    if "float" in str(dtype): return "float"
    if "datetime" in str(dtype): return "datetime"
    return "str"

tables = []

for file in os.listdir(DATA_DIR):
    if file.endswith(".csv"):
        table_name = file.replace(".csv", "").replace("olist_", "").replace("_dataset", "")
        df = pd.read_csv(DATA_DIR + file, nrows=5)
        
        columns = []
        for col in df.columns:
            columns.append({
                "name": col,
                "type": infer_type(df[col].dtype),
                "description": col.replace("_", " ")
            })
        
        tables.append({
            "name": table_name,
            "description": f"Olist {table_name.replace('_', ' ')} data",
            "columns": columns
        })
        print(f"processed: {table_name}")

schema = {
    "data_source_type": "sql",
    "tables": tables,
    "relationships": RELATIONSHIPS
}

with open("schemas/olist_schema.json", "w") as f:
    json.dump(schema, f, indent=2)

print("\nschema generated at schemas/olist_schema.json")