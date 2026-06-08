from pathlib import Path
import sqlite3


SOURCE_DB = Path("data/olist.sqlite/olist.sqlite")
TARGET_DB = Path("demo_data/olist_demo.sqlite")
TARGET_DB.parent.mkdir(parents=True, exist_ok=True)


def copy_table_schema(src_conn: sqlite3.Connection, dst_conn: sqlite3.Connection) -> None:
    cur = src_conn.cursor()
    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    for (sql,) in cur.fetchall():
        if sql:
            dst_conn.execute(sql)


def table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table_name}")')
    return [row[1] for row in cur.fetchall()]


def fetch_rows(conn: sqlite3.Connection, query: str, params=()):
    cur = conn.cursor()
    cur.execute(query, params)
    return cur.fetchall()


def insert_rows(dst_conn: sqlite3.Connection, table_name: str, rows: list[tuple]) -> None:
    if not rows:
        return
    cols = table_columns(dst_conn, table_name)
    placeholders = ",".join(["?"] * len(cols))
    col_sql = ",".join([f'"{c}"' for c in cols])
    dst_conn.executemany(
        f'INSERT INTO "{table_name}" ({col_sql}) VALUES ({placeholders})',
        rows,
    )


def main():
    if not SOURCE_DB.exists():
        raise FileNotFoundError(f"Source DB not found: {SOURCE_DB}")

    if TARGET_DB.exists():
        TARGET_DB.unlink()

    src_conn = sqlite3.connect(str(SOURCE_DB))
    dst_conn = sqlite3.connect(str(TARGET_DB))

    try:
        copy_table_schema(src_conn, dst_conn)

        orders = fetch_rows(
            src_conn,
            """
            SELECT *
            FROM orders
            ORDER BY order_purchase_timestamp DESC
            LIMIT 250
            """,
        )
        insert_rows(dst_conn, "orders", orders)
        order_ids = [row[0] for row in orders]
        customer_ids = [row[1] for row in orders]

        order_id_placeholders = ",".join(["?"] * len(order_ids))
        customer_id_placeholders = ",".join(["?"] * len(customer_ids))

        order_items = fetch_rows(
            src_conn,
            f"""
            SELECT *
            FROM order_items
            WHERE order_id IN ({order_id_placeholders})
            """,
            order_ids,
        )
        insert_rows(dst_conn, "order_items", order_items)

        order_payments = fetch_rows(
            src_conn,
            f"""
            SELECT *
            FROM order_payments
            WHERE order_id IN ({order_id_placeholders})
            """,
            order_ids,
        )
        insert_rows(dst_conn, "order_payments", order_payments)

        order_reviews = fetch_rows(
            src_conn,
            f"""
            SELECT *
            FROM order_reviews
            WHERE order_id IN ({order_id_placeholders})
            """,
            order_ids,
        )
        insert_rows(dst_conn, "order_reviews", order_reviews)

        customers = fetch_rows(
            src_conn,
            f"""
            SELECT *
            FROM customers
            WHERE customer_id IN ({customer_id_placeholders})
            """,
            customer_ids,
        )
        insert_rows(dst_conn, "customers", customers)

        product_ids = sorted({row[2] for row in order_items})
        seller_ids = sorted({row[3] for row in order_items})
        product_placeholders = ",".join(["?"] * len(product_ids)) if product_ids else "NULL"
        seller_placeholders = ",".join(["?"] * len(seller_ids)) if seller_ids else "NULL"

        if product_ids:
            products = fetch_rows(
                src_conn,
                f"""
                SELECT *
                FROM products
                WHERE product_id IN ({product_placeholders})
                """,
                product_ids,
            )
            insert_rows(dst_conn, "products", products)

            categories = sorted({row[1] for row in products if row[1]})
            if categories:
                category_placeholders = ",".join(["?"] * len(categories))
                translation = fetch_rows(
                    src_conn,
                    f"""
                    SELECT *
                    FROM product_category_name_translation
                    WHERE product_category_name IN ({category_placeholders})
                    """,
                    categories,
                )
                insert_rows(dst_conn, "product_category_name_translation", translation)

        if seller_ids:
            sellers = fetch_rows(
                src_conn,
                f"""
                SELECT *
                FROM sellers
                WHERE seller_id IN ({seller_placeholders})
                """,
                seller_ids,
            )
            insert_rows(dst_conn, "sellers", sellers)

        customer_zip_prefixes = sorted({row[2] for row in customers if row[2] is not None})
        seller_zip_prefixes = sorted({row[1] for row in sellers if row[1] is not None}) if seller_ids else []
        zip_prefixes = sorted(set(customer_zip_prefixes) | set(seller_zip_prefixes))
        if zip_prefixes:
            zip_placeholders = ",".join(["?"] * len(zip_prefixes))
            geolocation = fetch_rows(
                src_conn,
                f"""
                SELECT *
                FROM geolocation
                WHERE geolocation_zip_code_prefix IN ({zip_placeholders})
                LIMIT 2000
                """,
                zip_prefixes,
            )
            insert_rows(dst_conn, "geolocation", geolocation)

        leads_qualified = fetch_rows(
            src_conn,
            """
            SELECT *
            FROM leads_qualified
            LIMIT 120
            """,
        )
        insert_rows(dst_conn, "leads_qualified", leads_qualified)

        leads_closed = fetch_rows(
            src_conn,
            """
            SELECT *
            FROM leads_closed
            LIMIT 120
            """,
        )
        insert_rows(dst_conn, "leads_closed", leads_closed)

        dst_conn.commit()
    finally:
        src_conn.close()
        dst_conn.close()

    print(f"Created demo database at {TARGET_DB}")


if __name__ == "__main__":
    main()
