import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base

# Import all models to ensure they are registered with Base
from app.modules.users import models as user_models  # noqa: F401
from app.modules.products import models as product_models  # noqa: F401
from app.modules.inventory import models as inventory_models  # noqa: F401
from app.modules.orders import models as order_models  # noqa: F401

from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router, roles_router, customers_router
from app.modules.products.router import router as products_router, cat_router, sup_router
from app.modules.inventory.router import router as inventory_router
from app.modules.orders.router import (
    purchase_router, sales_router,
    invoices_router, shipments_router,
    checkout_router, admin_router,
)

Base.metadata.create_all(bind=engine)

# Safe column migrations for existing tables
from sqlalchemy import text
with engine.connect() as _conn:
    for _col in [
        "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS delivery_type VARCHAR",
        "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS contact_name VARCHAR",
        "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS contact_phone VARCHAR",
        "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS delivery_address VARCHAR",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS html_file_path VARCHAR",
    ]:
        _conn.execute(text(_col))
    _conn.commit()

app = FastAPI(title="TUMOMITO S.A. ERP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
app.include_router(customers_router)
app.include_router(products_router)
app.include_router(cat_router)
app.include_router(sup_router)
app.include_router(inventory_router)
app.include_router(purchase_router)
app.include_router(sales_router)
app.include_router(checkout_router)
app.include_router(invoices_router)
app.include_router(shipments_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {"message": "TUMOMITO S.A. ERP API", "version": "1.0.0", "docs": "/docs"}
