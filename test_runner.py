
import pandas as pd
import json
import time
from datetime import datetime
from ecommerce_app import Checkout, Customer, Cart, D, fixture


def execute_case(row):
    start = time.perf_counter()

    actual = {}
    error_message = ""

    try:
        # Tạo fixture riêng cho từng test case
        if row["fixture_key"] == "500k":
            app, user, cart = fixture("500k")
        else:
            app = Checkout()
            user = Customer("U_TEST")
            cart = Cart(app.catalog)

        data = json.loads(row["input_json"])
        operation = row["operation"]

        # REQ-01: Catalog
        if operation == "catalog_active":
            product = app.catalog.get(data["sku"])
            actual = {
                "sku": product.sku,
                "active": product.active
            }

        elif operation == "catalog_inactive":
            app.catalog.products[data["sku"]].active = False
            app.catalog.get(data["sku"])

        elif operation == "catalog_missing":
            app.catalog.get(data["sku"])

        # REQ-02: Cart
        elif operation == "cart_add":
            cart.add(data["sku"], data["quantity"])
            actual = {"quantity": cart.lines[0].quantity}

        elif operation == "cart_invalid":
            cart.add(data["sku"], data["quantity"])

        elif operation == "cart_accumulate":
            cart.add(data["sku"], data["first"])
            cart.add(data["sku"], data["second"])
            actual = {"quantity": cart.lines[0].quantity}

        # REQ-03: Pricing
        elif operation == "pricing_single":
            cart.add(data["sku"], data["quantity"])
            subtotal = cart.subtotal()
            actual = {
                "subtotal": str(subtotal),
                "type": type(subtotal).__name__
            }

        elif operation == "pricing_multi":
            for sku, quantity in data.items():
                cart.add(sku, quantity)

            subtotal = cart.subtotal()
            actual = {
                "subtotal": str(subtotal),
                "type": type(subtotal).__name__
            }

        elif operation == "pricing_decimal":
            for sku, quantity in data.items():
                cart.add(sku, quantity)

            subtotal = cart.subtotal()
            actual = {
                "subtotal": str(subtotal),
                "type": type(subtotal).__name__
            }

        # REQ-09: Shipping
        elif operation.startswith("shipping_"):
            fee = app.shipping.calculate(
                D(data["subtotal"]),
                data["area"]
            )
            actual = {"shipping": str(fee)}

        # REQ-10: Payment
        elif operation == "payment_cod":
            status = app.payments.collect(
                D(500000), "COD", True, row["test_case_id"]
            )
            actual = {"status": status}

        elif operation == "payment_approved":
            status = app.payments.collect(
                D(500000), "ONLINE", True, row["test_case_id"]
            )
            actual = {"status": status}

        elif operation == "payment_declined":
            try:
                app.place(
                    user,
                    cart,
                    method="ONLINE",
                    approved=False,
                    key=row["test_case_id"]
                )
            except ValueError as exc:
                error_message = str(exc)

            actual = {
                "error": error_message,
                "orders": len(app.orders)
            }

        else:
            raise ValueError("UNKNOWN_OPERATION")

    except ValueError as exc:
        error_message = str(exc)
        actual = {"error": error_message}

    except Exception as exc:
        error_message = str(exc)
        actual = {"exception": error_message}

    # Đọc Expected độc lập từ CSV
    expected = json.loads(row["expected_json"])

    # So sánh Expected và Actual
    if "exception" in actual:
        status = "BLOCKED"
    elif actual == expected:
        status = "PASS"
    else:
        status = "FAIL"

    elapsed = round(time.perf_counter() - start, 6)

    return {
        **row.to_dict(),
        "actual_result": json.dumps(actual, ensure_ascii=False),
        "execution_status": status,
        "error_message": error_message,
        "execution_time": elapsed,
        "executed_at": datetime.now().isoformat()
    }


def run_tests():
    # Đọc file CSV
    df = pd.read_csv("test_cases.csv", dtype=str).fillna("")

    # Kiểm tra ID trùng
    if df["test_case_id"].duplicated().any():
        raise ValueError("DUPLICATE_TEST_CASE_ID")

    results = []

    for _, row in df.iterrows():
        results.append(execute_case(row))

    result_df = pd.DataFrame(results)

    # Xuất kết quả riêng, không ghi đè CSV gốc
    result_df.to_csv(
        "test_execution.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("Total:", len(result_df))
    print("PASS:", (result_df["execution_status"] == "PASS").sum())
    print("FAIL:", (result_df["execution_status"] == "FAIL").sum())

    display(result_df[
        [
            "test_case_id",
            "requirement_id",
            "expected_json",
            "actual_result",
            "execution_status",
            "execution_time"
        ]
    ])

    return result_df
