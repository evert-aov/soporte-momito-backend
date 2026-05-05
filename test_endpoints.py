import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root():
    print("\nTesting root endpoint...")
    response = client.get("/")
    assert response.status_code == 200, f"Root failed: {response.status_code}"
    data = response.json()
    assert data["version"] == "1.0.0"
    print(f"   OK - {data['message']}")


def test_login():
    print("\nTesting login...")
    response = client.post("/api/auth/login", json={
        "email": "admin@tumomito.com",
        "password": "password123"
    })
    assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
    data = response.json()
    assert "access_token" in data
    print(f"   OK - token: {data['access_token'][:30]}...")
    return data["access_token"]


def test_login_bad_password():
    print("\nTesting login with bad password (expect 401)...")
    response = client.post("/api/auth/login", json={
        "email": "admin@tumomito.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401, f"Expected 401, got: {response.status_code}"
    print("   OK - 401 returned as expected")


def test_register(token: str):
    import time
    print("\nTesting register new user...")
    unique_email = f"testuser_{int(time.time())}@tumomito.com"
    response = client.post("/api/auth/register", json={
        "full_name": "Test User",
        "email": unique_email,
        "password": "testpass123"
    })
    assert response.status_code == 200, f"Register failed: {response.status_code} - {response.text}"
    data = response.json()
    assert "id" in data
    print(f"   OK - user created with id: {data['id']} ({unique_email})")


def test_list_products(token: str):
    print("\nTesting list products...")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/products/", headers=headers)
    assert response.status_code == 200, f"List products failed: {response.status_code} - {response.text}"
    products = response.json()
    print(f"   OK - Found {len(products)} products")
    return products


def test_create_product(token: str):
    import time
    print("\nTesting create product...")
    headers = {"Authorization": f"Bearer {token}"}
    ts = int(time.time())
    product_id = f"TEST-PROD-{ts}"
    response = client.post("/api/products/", json={
        "id": product_id,
        "default_code": f"TEST-SKU-{ts}",
        "name": "Test Product",
        "type": "Storable",
        "list_price": 10.99,
        "standard_price": 5.00,
        "active": True
    }, headers=headers)
    assert response.status_code == 200, f"Create product failed: {response.status_code} - {response.text}"
    product = response.json()
    print(f"   OK - Product created: {product['name']} (ID: {product['id']})")
    return product["id"]


def test_get_product(token: str, product_id: str):
    print(f"\nTesting get product {product_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get(f"/api/products/{product_id}", headers=headers)
    assert response.status_code == 200, f"Get product failed: {response.status_code} - {response.text}"
    product = response.json()
    print(f"   OK - Product retrieved: {product['name']}")


def test_update_product(token: str, product_id: str):
    print(f"\nTesting update product {product_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.put(f"/api/products/{product_id}", json={
        "name": "Test Product Updated",
        "list_price": 15.99
    }, headers=headers)
    assert response.status_code == 200, f"Update product failed: {response.status_code} - {response.text}"
    product = response.json()
    assert product["name"] == "Test Product Updated"
    print(f"   OK - Product updated: {product['name']}, price: {product['list_price']}")


def test_list_categories():
    print("\nTesting list categories (no auth)...")
    response = client.get("/api/categories/")
    assert response.status_code == 200, f"List categories failed: {response.status_code}"
    cats = response.json()
    print(f"   OK - Found {len(cats)} categories")


def test_list_suppliers():
    print("\nTesting list suppliers (no auth)...")
    response = client.get("/api/suppliers/")
    assert response.status_code == 200, f"List suppliers failed: {response.status_code}"
    sups = response.json()
    print(f"   OK - Found {len(sups)} suppliers")


def test_list_inventory(token: str):
    print("\nTesting list inventory...")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/inventory/", headers=headers)
    assert response.status_code == 200, f"List inventory failed: {response.status_code} - {response.text}"
    inv = response.json()
    print(f"   OK - Found {len(inv)} inventory records")


def test_create_sales_order(token: str):
    print("\nTesting create sales order...")
    headers = {"Authorization": f"Bearer {token}"}
    # Get the first customer
    customers_resp = client.get("/api/customers/", headers=headers)
    customers = customers_resp.json()
    if not customers:
        print("   SKIP - No customers available")
        return None

    customer_id = customers[0]["id"]
    response = client.post("/api/sales-orders/", json={
        "customer_id": customer_id,
        "payment_terms": "30 days",
        "source_channel": "web",
        "total_discount": "0",
        "lines": [
            {"product_id": "PROD001", "quantity": 5, "unit_price": "8.50"},
            {"product_id": "PROD002", "quantity": 3, "unit_price": "7.50"},
        ]
    }, headers=headers)
    assert response.status_code == 200, f"Create sales order failed: {response.status_code} - {response.text}"
    order = response.json()
    print(f"   OK - Sales order created: ID {order['id']}, total: {order['total_amount']}")
    return order["id"]


def test_create_purchase_order(token: str):
    print("\nTesting create purchase order...")
    headers = {"Authorization": f"Bearer {token}"}
    suppliers_resp = client.get("/api/suppliers/", headers=headers)
    suppliers = suppliers_resp.json()
    if not suppliers:
        print("   SKIP - No suppliers available")
        return None

    supplier_id = suppliers[0]["id"]
    response = client.post("/api/purchase-orders/", json={
        "supplier_id": supplier_id,
        "lines": [
            {"product_id": "PROD001", "quantity": 100, "unit_price": "5.00"},
            {"product_id": "PROD003", "quantity": 50, "unit_price": "2.50"},
        ]
    }, headers=headers)
    assert response.status_code == 200, f"Create purchase order failed: {response.status_code} - {response.text}"
    order = response.json()
    print(f"   OK - Purchase order created: ID {order['id']}, total: {order['total_amount']}")
    return order["id"]


def test_list_users(token: str):
    print("\nTesting list users...")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/users/", headers=headers)
    assert response.status_code == 200, f"List users failed: {response.status_code}"
    users = response.json()
    print(f"   OK - Found {len(users)} users")


def test_list_roles(token: str):
    print("\nTesting list roles...")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/roles/", headers=headers)
    assert response.status_code == 200, f"List roles failed: {response.status_code}"
    roles = response.json()
    print(f"   OK - Found {len(roles)} roles")


def test_protected_without_token():
    print("\nTesting protected endpoint without token (expect 401)...")
    response = client.get("/api/products/")
    assert response.status_code == 401, f"Expected 401, got: {response.status_code}"
    print("   OK - 401 returned as expected")


if __name__ == "__main__":
    print("TUMOMITO S.A. - API Tests")
    print("=" * 50)
    try:
        test_root()
        token = test_login()
        test_login_bad_password()
        test_register(token)
        test_list_products(token)
        product_id = test_create_product(token)
        test_get_product(token, product_id)
        test_update_product(token, product_id)
        test_list_categories()
        test_list_suppliers()
        test_list_inventory(token)
        test_list_users(token)
        test_list_roles(token)
        test_create_sales_order(token)
        test_create_purchase_order(token)
        test_protected_without_token()

        print("\n" + "=" * 50)
        print("ALL TESTS PASSED!")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
