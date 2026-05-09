#!/usr/bin/env python3
"""
massive_seeder.py — Generador masivo de datos de prueba para TUMOMITO S.A.

Genera 5 años de histórico (2021-05-08 → 2026-05-08) con ≥25,000 órdenes de venta.

Prerequisitos (instalar una sola vez):
    pip install faker pandas numpy

Uso:
    cd backend/
    source venv/bin/activate
    python massive_seeder.py
"""

import sys
import os
import uuid
import random
from datetime import datetime, timedelta

# --- Verificar dependencias opcionales antes de importar ---
_missing = []
for pkg in ("faker", "pandas", "numpy"):
    try:
        __import__(pkg)
    except ImportError:
        _missing.append(pkg)

if _missing:
    print(f"[ERROR] Paquetes requeridos no instalados: {', '.join(_missing)}")
    print(f"        Ejecuta: pip install {' '.join(_missing)}")
    sys.exit(1)

import numpy as np
import pandas as pd
from faker import Faker
from passlib.context import CryptContext
from sqlalchemy import text

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from app.modules.users.models import Role, Branch, Customer, User
from app.modules.products.models import (
    ProductCategory, UnitOfMeasure, Supplier, Product
)
from app.modules.orders.models import (
    SalesOrder, SalesOrderLine, Invoice, Shipment,
    PurchaseOrder, PurchaseOrderLine,
)
from app.modules.inventory.models import BranchInventory

# ---------------------------------------------------------------------------
# Configuración global
# ---------------------------------------------------------------------------
fake = Faker(["es_MX", "es_ES"])
Faker.seed(42)
random.seed(42)
np.random.seed(42)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Hash computado la primera vez que se necesita (evita warning de bcrypt al importar)
_pwd_hash_cache: str | None = None


def get_default_pwd_hash() -> str:
    global _pwd_hash_cache
    if _pwd_hash_cache is None:
        _pwd_hash_cache = pwd_ctx.hash("Test1234!")
    return _pwd_hash_cache

TODAY = datetime(2026, 5, 8)
START_DATE = datetime(2021, 5, 8)

# Volumen de catálogos
N_CUSTOMERS = 2_000
N_PRODUCTS = 500
N_SUPPLIERS = 30
N_SALESPEOPLE = 20

# Órdenes de venta por año completo (≥5000 requerido)
N_ORDERS_PER_FULL_YEAR = 5_200

# Estados donde se genera factura
WITH_INVOICE = {"paid", "confirmed", "picking", "dispatched", "delivered"}
# Estados donde se genera envío
WITH_SHIPMENT = {"dispatched", "delivered"}

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def get_max_id(conn, table: str) -> int:
    result = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}"))
    return result.scalar()


def reset_sequence(conn, table: str, column: str = "id") -> None:
    """Sincroniza la secuencia de PostgreSQL tras inserciones con ID explícito."""
    conn.execute(text(f"""
        SELECT setval(
            pg_get_serial_sequence('{table}', '{column}'),
            COALESCE((SELECT MAX({column}) FROM {table}), 1)
        )
    """))


def random_dates(start: datetime, end: datetime, n: int) -> np.ndarray:
    """n datetimes uniformes en [start, end]."""
    s, e = start.timestamp(), end.timestamp()
    return np.array([
        datetime.fromtimestamp(ts)
        for ts in np.random.uniform(s, e, n)
    ])


def assign_statuses(order_dates: np.ndarray) -> np.ndarray:
    """
    Asigna estados a las órdenes de forma vectorizada según su antigüedad.
    Distribución diseñada para que órdenes antiguas estén en su mayoría 'delivered'
    y órdenes recientes muestren el pipeline en distintas etapas.
    """
    days_ago = np.array([(TODAY - d).days for d in order_dates])
    statuses = np.empty(len(order_dates), dtype=object)

    # Órdenes muy antiguas (>365 días)
    m = days_ago > 365
    if m.any():
        statuses[m] = np.random.choice(
            ["delivered", "cancelled", "dispatched", "confirmed"],
            size=m.sum(), p=[0.87, 0.08, 0.03, 0.02],
        )

    # Órdenes de hace 90-365 días
    m = (days_ago > 90) & (days_ago <= 365)
    if m.any():
        statuses[m] = np.random.choice(
            ["delivered", "cancelled", "dispatched", "confirmed", "paid"],
            size=m.sum(), p=[0.70, 0.10, 0.08, 0.07, 0.05],
        )

    # Órdenes de hace 30-90 días
    m = (days_ago > 30) & (days_ago <= 90)
    if m.any():
        statuses[m] = np.random.choice(
            ["delivered", "cancelled", "dispatched", "confirmed", "paid", "pending_payment"],
            size=m.sum(), p=[0.50, 0.10, 0.15, 0.12, 0.10, 0.03],
        )

    # Órdenes del último mes
    m = days_ago <= 30
    if m.any():
        statuses[m] = np.random.choice(
            ["delivered", "cancelled", "dispatched", "confirmed", "paid", "pending_payment", "draft"],
            size=m.sum(), p=[0.20, 0.05, 0.20, 0.20, 0.25, 0.07, 0.03],
        )

    return statuses


# ---------------------------------------------------------------------------
# Pools de datos Faker pre-generados (evita llamadas repetidas en bucles)
# ---------------------------------------------------------------------------

def build_fake_pools() -> dict:
    print("  Pre-generando pools de datos Faker... ", end="", flush=True)
    pools = {
        "names":     [fake.name()            for _ in range(2_000)],
        "phones":    [fake.phone_number()[:20] for _ in range(1_000)],
        "addresses": [fake.address()[:200]   for _ in range(2_000)],
        "companies": [fake.company()         for _ in range(2_000)],
        "emails":    [fake.company_email()   for _ in range(2_000)],
    }
    print("listo.")
    return pools


def rnd(pool: list, size: int) -> np.ndarray:
    """Muestrea 'size' valores del pool dado."""
    return np.random.choice(pool, size=size)


# ---------------------------------------------------------------------------
# Fase 1 — Catálogos base
# ---------------------------------------------------------------------------

def _get_or_create(db, model, defaults: dict = None, **filters):
    """Retorna la instancia existente o la crea con los valores de 'defaults'."""
    obj = db.query(model).filter_by(**filters).first()
    if obj is None:
        params = {**filters, **(defaults or {})}
        obj = model(**params)
        db.add(obj)
        db.flush()
    return obj


def seed_catalogs(db, pools: dict) -> None:
    print("\n[FASE 1] Sembrando catálogos base...")

    # --- Roles (get-or-create por nombre) ---
    role_specs = [
        ("superadmin", "Administrador del sistema"),
        ("admin",      "Administrador"),
        ("vendedor",   "Vendedor"),
        ("almacenero", "Encargado de almacén"),
    ]
    created_roles = 0
    for name, desc in role_specs:
        existing = db.query(Role).filter(Role.name == name).first()
        if not existing:
            db.add(Role(name=name, description=desc))
            created_roles += 1
    if created_roles:
        db.commit()
        print(f"    ✓ Roles ({created_roles} nuevos)")
    else:
        print("    ✓ Roles (ya existían)")

    # --- Sucursales (get-or-create por nombre) ---
    branch_specs = [
        ("Sucursal Central", "Santa Cruz de la Sierra"),
        ("Sucursal Norte",   "Montero"),
        ("Sucursal Sur",     "Warnes"),
    ]
    created_branches = 0
    for name, loc in branch_specs:
        if not db.query(Branch).filter(Branch.name == name).first():
            db.add(Branch(name=name, location=loc))
            created_branches += 1
    if created_branches:
        db.commit()
        print(f"    ✓ Sucursales ({created_branches} nuevas)")
    else:
        print("    ✓ Sucursales (ya existían)")

    # --- Unidades de medida (get-or-create por nombre) ---
    uom_names = ["Unidad", "Caja", "Kilogramo", "Litro", "Metro", "Par", "Docena"]
    created_uoms = 0
    for name in uom_names:
        if not db.query(UnitOfMeasure).filter(UnitOfMeasure.name == name).first():
            db.add(UnitOfMeasure(name=name))
            created_uoms += 1
    if created_uoms:
        db.commit()
        print(f"    ✓ Unidades de medida ({created_uoms} nuevas)")
    else:
        print("    ✓ Unidades de medida (ya existían)")

    # --- Categorías de productos (solo si no existen suficientes) ---
    if db.query(ProductCategory).count() < 20:
        parent_names = [
            "Electrónica", "Hogar y Cocina", "Ropa y Calzado",
            "Alimentos y Bebidas", "Oficina y Papelería",
        ]
        parents = []
        for name in parent_names:
            p = db.query(ProductCategory).filter(ProductCategory.name == name, ProductCategory.parent_id.is_(None)).first()
            if not p:
                p = ProductCategory(name=name)
                db.add(p)
            parents.append(p)
        db.flush()

        children_specs = [
            ("Smartphones y Tablets",      parents[0].id),
            ("Computadoras y Accesorios",  parents[0].id),
            ("Audio y Video",              parents[0].id),
            ("Electrodomésticos Grandes",  parents[1].id),
            ("Electrodomésticos Pequeños", parents[1].id),
            ("Muebles y Decoración",       parents[1].id),
            ("Ropa Masculina",             parents[2].id),
            ("Ropa Femenina",              parents[2].id),
            ("Calzado Deportivo",          parents[2].id),
            ("Calzado Formal",             parents[2].id),
            ("Productos Secos",            parents[3].id),
            ("Bebidas",                    parents[3].id),
            ("Lácteos y Frescos",          parents[3].id),
            ("Material de Oficina",        parents[4].id),
            ("Impresión y Tóner",          parents[4].id),
        ]
        for child_name, pid in children_specs:
            if not db.query(ProductCategory).filter(ProductCategory.name == child_name).first():
                db.add(ProductCategory(name=child_name, parent_id=pid))
        db.commit()
        print(f"    ✓ Categorías (creadas/completadas hasta 20)")
    else:
        print("    ✓ Categorías (ya existían)")

    # --- Proveedores ---
    if db.query(Supplier).count() < N_SUPPLIERS:
        countries = ["Bolivia", "Argentina", "Brasil", "China", "USA", "Colombia", "Chile", "Perú"]
        to_add = N_SUPPLIERS - db.query(Supplier).count()
        db.add_all([
            Supplier(
                name=pools["companies"][i],
                country_of_origin=random.choice(countries),
                email=pools["emails"][i],
            )
            for i in range(to_add)
        ])
        db.commit()
        print(f"    ✓ Proveedores ({to_add} nuevos)")
    else:
        print("    ✓ Proveedores (ya existían)")

    # --- Clientes (2,000) — to_sql para velocidad ---
    existing_customers = db.query(Customer).count()
    if existing_customers < N_CUSTOMERS:
        n_to_create = N_CUSTOMERS - existing_customers
        print(f"    Generando {n_to_create:,} clientes...", end=" ", flush=True)
        segments = np.random.choice(
            ["RETAIL", "MAYORISTA", "CORPORATIVO", "GOBIERNO"],
            size=n_to_create, p=[0.50, 0.30, 0.15, 0.05],
        )
        total_days = (TODAY - START_DATE).days
        reg_dates = [START_DATE + timedelta(days=int(d)) for d in np.random.randint(0, total_days, n_to_create)]

        df = pd.DataFrame({
            "segment":           segments,
            "commercial_name":   rnd(pools["companies"], n_to_create),
            "legal_name":        [c + " S.R.L." for c in rnd(pools["companies"], n_to_create)],
            "tax_id":            [f"{random.randint(1_000_000, 9_999_999)}-{random.randint(1,9)}" for _ in range(n_to_create)],
            "credit_limit":      np.round(np.random.uniform(5_000, 100_000, n_to_create), 2),
            "pricing_profile":   np.random.randint(1, 4, n_to_create),
            "phone":             rnd(pools["phones"], n_to_create),
            "delivery_address":  rnd(pools["addresses"], n_to_create),
            "registration_date": reg_dates,
        })
        df.to_sql("customers", con=engine, if_exists="append", index=False, method="multi", chunksize=500)
        with engine.connect() as conn:
            reset_sequence(conn, "customers")
            conn.commit()
        print(f"✓ ({n_to_create:,})")
    else:
        print(f"    ✓ Clientes (ya existían: {existing_customers:,})")

    # --- Usuarios vendedores (get-or-create por email) ---
    # Asegurar que el rol "vendedor" exista (ya fue creado arriba)
    vendor_role = db.query(Role).filter(Role.name == "vendedor").first()
    if vendor_role is None:
        # Fallback: usar cualquier rol no-superadmin disponible
        vendor_role = db.query(Role).filter(Role.name != "superadmin").first()
    if vendor_role is None:
        vendor_role = Role(name="vendedor", description="Vendedor")
        db.add(vendor_role)
        db.commit()

    branches = db.query(Branch).all()
    if not branches:
        branches = [Branch(name="Principal", location="Santa Cruz")]
        db.add_all(branches)
        db.commit()

    existing_vendors = db.query(User).filter(User.role_id == vendor_role.id).count()
    if existing_vendors < N_SALESPEOPLE:
        to_create = N_SALESPEOPLE - existing_vendors
        default_hash = get_default_pwd_hash()
        db.add_all([
            User(
                role_id=vendor_role.id,
                full_name=pools["names"][i],
                email=f"seed.vendedor{i + 1 + existing_vendors:02d}@tumomito.com",
                password_hash=default_hash,
                is_active=True,
                branch_id=random.choice(branches).id,
            )
            for i in range(to_create)
        ])
        db.commit()
        print(f"    ✓ Vendedores ({to_create} nuevos)")
    else:
        print(f"    ✓ Vendedores (ya existían: {existing_vendors})")

    # --- Productos (500) — to_sql ---
    existing_prod_count = db.query(Product).count()
    if existing_prod_count < N_PRODUCTS:
        n_prod_to_create = N_PRODUCTS - existing_prod_count
        print(f"    Generando {n_prod_to_create:,} productos...", end=" ", flush=True)
        leaf_cats = (
            db.query(ProductCategory)
            .filter(ProductCategory.parent_id.isnot(None))
            .all()
        )
        # Si no hay categorías hoja, usar todas las disponibles
        if not leaf_cats:
            leaf_cats = db.query(ProductCategory).all()
        uoms = db.query(UnitOfMeasure).all()
        # Si no hay UoM, crear una por defecto
        if not uoms:
            u = UnitOfMeasure(name="Unidad")
            db.add(u)
            db.commit()
            uoms = [u]

        adjs   = ["Pro", "Ultra", "Max", "Plus", "Elite", "Standard", "Smart", "Digital", "Advanced", "Eco"]
        brands = ["TechPro", "HomePlus", "StyleMax", "FoodBest", "OfficeOne", "DataLink", "SmartHome", "GlobalTech"]
        nouns  = [
            "Procesador", "Monitor", "Teclado", "Auricular", "Cámara", "Impresora",
            "Lavadora", "Refrigerador", "Licuadora", "Silla", "Lámpara",
            "Camisa", "Pantalón", "Zapato", "Botella", "Cuaderno", "Bolígrafo",
            "Mochila", "Reloj", "Cargador",
        ]

        products = []
        for i in range(n_prod_to_create):
            uom = random.choice(uoms)
            list_price = round(random.uniform(15.0, 800.0), 2)
            std_price  = round(list_price * random.uniform(0.40, 0.70), 2)
            products.append({
                "id":               str(uuid.uuid4()),
                "default_code":     f"PROD-{existing_prod_count + i + 1:04d}",
                "name":             f"{random.choice(brands)} {random.choice(adjs)} {random.choice(nouns)} {existing_prod_count + i + 1:04d}",
                "active":           True,
                "type":             random.choice(["product", "product", "product", "service", "consu"]),
                "category_id":      random.choice(leaf_cats).id if leaf_cats else None,
                "uom_id":           uom.id,
                "uom_po_id":        uom.id,
                "list_price":       list_price,
                "standard_price":   std_price,
                "purchase_ok":      True,
                "sale_ok":          True,
                "taxes_id":         None,
                "supplier_taxes_id": None,
                "image_url":        None,
            })

        pd.DataFrame(products).to_sql(
            "products", con=engine, if_exists="append", index=False, method="multi", chunksize=500
        )
        print(f"✓ ({n_prod_to_create:,})")
    else:
        print(f"    ✓ Productos (ya existían: {existing_prod_count:,})")

    # --- Inventario inicial ---
    if db.query(BranchInventory).count() < 10:
        print("    Generando inventario inicial...", end=" ", flush=True)
        prod_ids = [row[0] for row in db.query(Product.id).all()]
        all_branches = db.query(Branch).all()
        records = [
            {
                "product_id":   pid,
                "branch_id":    br.id,
                "quantity":     random.randint(10, 500),
                "min_stock":    random.randint(5, 30),
                "last_updated": TODAY,
            }
            for pid in prod_ids
            for br in all_branches
        ]
        pd.DataFrame(records).to_sql(
            "branch_inventory", con=engine, if_exists="append", index=False, method="multi", chunksize=1_000
        )
        with engine.connect() as conn:
            reset_sequence(conn, "branch_inventory")
            conn.commit()
        print(f"✓ ({len(records):,} registros)")


# ---------------------------------------------------------------------------
# Fase 2 — Órdenes de venta por año
# ---------------------------------------------------------------------------

def generate_year_sales(
    year: int,
    product_data: list,
    customer_ids: list,
    user_ids: list,
    id_offsets: dict,
    pools: dict,
) -> dict:
    """
    Genera DataFrames de ventas, líneas, facturas y envíos para un año dado.
    Retorna los DataFrames y los nuevos offsets de ID para el siguiente año.
    """
    if year < 2026:
        yr_start = datetime(year, 1, 1)
        yr_end   = datetime(year, 12, 31, 23, 59, 59)
        n_orders = N_ORDERS_PER_FULL_YEAR
    else:
        # 2026: solo hasta la fecha actual
        yr_start = datetime(2026, 1, 1)
        yr_end   = TODAY
        days_in  = (yr_end - yr_start).days
        n_orders = max(int(N_ORDERS_PER_FULL_YEAR * days_in / 365), 1_800)

    # ---- Fechas y estados de órdenes -----------------------------------
    order_dates = random_dates(yr_start, yr_end, n_orders)
    statuses    = assign_statuses(order_dates)

    # ---- IDs explícitos ------------------------------------------------
    ord_id_base  = id_offsets["sales_orders"]
    order_ids    = np.arange(ord_id_base, ord_id_base + n_orders, dtype=np.int64)

    # ---- Atributos de la orden ----------------------------------------
    pay_methods  = np.random.choice(
        ["efectivo", "tarjeta", "transferencia", "paypal", "qr"],
        size=n_orders, p=[0.30, 0.25, 0.20, 0.15, 0.10],
    )
    src_channels = np.random.choice(
        ["presencial", "web", "telefono", "b2b", "whatsapp"],
        size=n_orders, p=[0.35, 0.30, 0.15, 0.15, 0.05],
    )
    pay_terms    = np.random.choice(
        ["contado", "15 días", "30 días", "60 días"],
        size=n_orders, p=[0.50, 0.20, 0.20, 0.10],
    )
    del_types    = np.random.choice(["delivery", "pickup"], size=n_orders, p=[0.65, 0.35])
    cust_ids_arr = np.random.choice(customer_ids, size=n_orders)
    usr_ids_arr  = np.random.choice(user_ids,     size=n_orders)

    # ---- Líneas de orden (vectorizado) ---------------------------------
    n_lines_per = np.random.randint(1, 6, size=n_orders)   # 1–5 líneas
    total_lines = int(n_lines_per.sum())

    line_id_base   = id_offsets["sales_order_lines"]
    line_ids       = np.arange(line_id_base, line_id_base + total_lines, dtype=np.int64)

    ord_ids_exp    = np.repeat(order_ids, n_lines_per)

    prod_arr       = np.array(product_data)
    prod_idx       = np.random.randint(0, len(prod_arr), size=total_lines)
    line_prod_ids  = np.array([p["id"]         for p in prod_arr])[prod_idx]
    line_prices    = np.array([p["list_price"]  for p in prod_arr], dtype=float)[prod_idx]

    # Variación de precio ±10 % sobre list_price
    line_prices    = np.round(line_prices * np.random.uniform(0.90, 1.10, total_lines), 2)
    line_qtys      = np.random.randint(1, 11, size=total_lines)
    line_subtotals = np.round(line_qtys * line_prices, 2)

    # Subtotal por orden (reducido a array alineado con order_ids)
    order_subtotals = np.zeros(n_orders, dtype=float)
    np.add.at(order_subtotals, np.repeat(np.arange(n_orders), n_lines_per), line_subtotals)
    order_subtotals = np.round(order_subtotals, 2)

    # Descuento: 20 % de las órdenes obtienen 2–10 % de descuento
    disc_mask    = np.random.random(n_orders) < 0.20
    disc_pct     = np.where(disc_mask, np.random.uniform(0.02, 0.10, n_orders), 0.0)
    discounts    = np.round(order_subtotals * disc_pct, 2)
    total_amts   = np.round(order_subtotals - discounts, 2)

    # ---- DataFrame sales_orders ----------------------------------------
    df_orders = pd.DataFrame({
        "id":               order_ids,
        "customer_id":      cust_ids_arr,
        "user_id":          usr_ids_arr,
        "order_date":       order_dates,
        "status":           statuses,
        "subtotal":         order_subtotals,
        "total_discount":   discounts,
        "total_amount":     total_amts,
        "payment_terms":    pay_terms,
        "source_channel":   src_channels,
        "payment_method":   pay_methods,
        "paypal_order_id":  None,
        "guest_email":      None,
        "delivery_type":    del_types,
        "contact_name":     rnd(pools["names"],     n_orders),
        "contact_phone":    rnd(pools["phones"],    n_orders),
        "delivery_address": rnd(pools["addresses"], n_orders),
    })

    # ---- DataFrame sales_order_lines -----------------------------------
    df_lines = pd.DataFrame({
        "id":             line_ids,
        "sales_order_id": ord_ids_exp,
        "product_id":     line_prod_ids,
        "quantity":       line_qtys,
        "unit_price":     line_prices,
        "subtotal":       line_subtotals,
    })

    # ---- Facturas (órdenes con estado pagado o superior) ---------------
    inv_mask       = np.isin(statuses, list(WITH_INVOICE))
    inv_order_ids  = order_ids[inv_mask]
    inv_ord_dates  = order_dates[inv_mask]
    inv_amounts    = total_amts[inv_mask]
    n_invoices     = int(inv_mask.sum())

    inv_id_base = id_offsets["invoices"]
    inv_ids     = np.arange(inv_id_base, inv_id_base + n_invoices, dtype=np.int64)

    inv_date_offsets = [timedelta(days=int(d)) for d in np.random.randint(0, 3, n_invoices)]
    inv_dates        = np.array([d + off for d, off in zip(inv_ord_dates, inv_date_offsets)])
    inv_numbers      = [f"INV-{d.strftime('%Y%m')}-{iid:07d}" for d, iid in zip(inv_dates, inv_ids)]

    df_invoices = pd.DataFrame({
        "id":             inv_ids,
        "sales_order_id": inv_order_ids,
        "invoice_number": inv_numbers,
        "issue_date":     inv_dates,
        "total_amount":   inv_amounts,
        "payment_status": "paid",
        "xml_file_url":   None,
        "html_file_path": None,
    })

    # ---- Envíos (órdenes despachadas o entregadas) ---------------------
    ship_mask      = np.isin(statuses, list(WITH_SHIPMENT))
    ship_ord_ids   = order_ids[ship_mask]
    ship_ord_dates = order_dates[ship_mask]
    n_shipments    = int(ship_mask.sum())

    ship_id_base = id_offsets["shipments"]
    ship_ids     = np.arange(ship_id_base, ship_id_base + n_shipments, dtype=np.int64)

    carriers          = np.random.choice(
        ["DHL", "FedEx", "UPS", "Correos Bolivia", "Estafeta", "TransBolivia"],
        size=n_shipments,
    )
    tracking_numbers  = [f"TRK{sid:010d}" for sid in ship_ids]

    dispatch_offsets  = [timedelta(days=int(d)) for d in np.random.randint(1, 4, n_shipments)]
    dispatch_dates    = np.array([d + off for d, off in zip(ship_ord_dates, dispatch_offsets)])
    est_del_offsets   = [timedelta(days=int(d)) for d in np.random.randint(2, 8, n_shipments)]
    est_del_dates     = np.array([d + off for d, off in zip(dispatch_dates, est_del_offsets)])
    delivery_statuses = np.where(
        np.isin(statuses[ship_mask], ["delivered"]), "delivered", "in_transit"
    )

    df_shipments = pd.DataFrame({
        "id":                      ship_ids,
        "sales_order_id":          ship_ord_ids,
        "carrier":                 carriers,
        "tracking_number":         tracking_numbers,
        "dispatch_date":           dispatch_dates,
        "estimated_delivery_date": est_del_dates,
        "delivery_status":         delivery_statuses,
    })

    return {
        "orders":     df_orders,
        "lines":      df_lines,
        "invoices":   df_invoices,
        "shipments":  df_shipments,
        "n_orders":   n_orders,
        "n_lines":    total_lines,
        "n_invoices": n_invoices,
        "n_shipments": n_shipments,
        "new_offsets": {
            "sales_orders":      ord_id_base  + n_orders,
            "sales_order_lines": line_id_base + total_lines,
            "invoices":          inv_id_base  + n_invoices,
            "shipments":         ship_id_base + n_shipments,
        },
    }


# ---------------------------------------------------------------------------
# Fase 3 — Órdenes de compra (~120/año)
# ---------------------------------------------------------------------------

def seed_purchase_orders(db, product_data: list, user_ids: list) -> None:
    """Genera órdenes de compra históricas para los 5 años."""
    supplier_ids = [row[0] for row in db.query(Supplier.id).all()]

    with engine.connect() as conn:
        po_id  = get_max_id(conn, "purchase_orders")  + 1
        pol_id = get_max_id(conn, "purchase_order_lines") + 1

    all_po, all_pol = [], []

    for year in range(2021, 2027):
        if year < 2026:
            yr_start, yr_end, n_po = datetime(year, 1, 1), datetime(year, 12, 31), 120
        else:
            yr_start, yr_end, n_po = datetime(2026, 1, 1), TODAY, 40

        po_dates = random_dates(yr_start, yr_end, n_po)

        for i in range(n_po):
            issue_dt  = po_dates[i]
            eta       = issue_dt + timedelta(days=random.randint(7, 30))
            days_old  = (TODAY - issue_dt).days
            status    = (
                random.choice(["received", "received", "received", "confirmed"])
                if days_old > 30
                else random.choice(["draft", "confirmed", "received"])
            )

            n_lines  = random.randint(1, 6)
            po_total = 0.0

            for _ in range(n_lines):
                prod  = random.choice(product_data)
                qty   = random.randint(5, 100)
                price = round(float(prod["standard_price"]) * random.uniform(0.80, 1.00), 2)
                sub   = round(qty * price, 2)
                po_total += sub
                all_pol.append({
                    "id":               pol_id,
                    "purchase_order_id": po_id,
                    "product_id":       prod["id"],
                    "quantity":         qty,
                    "unit_price":       price,
                    "subtotal":         sub,
                })
                pol_id += 1

            all_po.append({
                "id":                     po_id,
                "supplier_id":            random.choice(supplier_ids),
                "user_id":                random.choice(user_ids),
                "issue_date":             issue_dt,
                "estimated_arrival_date": eta,
                "status":                 status,
                "total_amount":           round(po_total, 2),
            })
            po_id += 1

    df_po  = pd.DataFrame(all_po)
    df_pol = pd.DataFrame(all_pol)

    df_po.to_sql("purchase_orders",      con=engine, if_exists="append", index=False, method="multi", chunksize=500)
    df_pol.to_sql("purchase_order_lines", con=engine, if_exists="append", index=False, method="multi", chunksize=1_000)

    with engine.connect() as conn:
        reset_sequence(conn, "purchase_orders")
        reset_sequence(conn, "purchase_order_lines")
        conn.commit()

    print(f"    ✓ {len(all_po):,} órdenes de compra | {len(all_pol):,} líneas")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 65)
    print("  TUMOMITO S.A. — Massive Data Seeder")
    print(f"  Rango: {START_DATE.strftime('%Y-%m-%d')} → {TODAY.strftime('%Y-%m-%d')}")
    print(f"  Objetivo: ≥25,000 órdenes de venta (≥5,000/año × 5 años)")
    print("=" * 65)

    pools = build_fake_pools()
    db    = SessionLocal()

    try:
        # ------------------------------------------------------------------
        # FASE 1: Catálogos
        # ------------------------------------------------------------------
        seed_catalogs(db, pools)

        # Cargar referencias en memoria para las fases siguientes
        product_data = [
            {
                "id":             p.id,
                "list_price":     float(p.list_price   or 50.0),
                "standard_price": float(p.standard_price or 25.0),
            }
            for p in db.query(Product).filter(Product.active.is_(True)).all()
        ]
        customer_ids = [row[0] for row in db.query(Customer.id).all()]
        user_ids     = [row[0] for row in db.query(User.id).filter(User.role_id.isnot(None)).all()]

        print(f"\n  Productos disponibles : {len(product_data):,}")
        print(f"  Clientes disponibles  : {len(customer_ids):,}")
        print(f"  Usuarios disponibles  : {len(user_ids):,}")

        # ------------------------------------------------------------------
        # FASE 2: Órdenes de venta año por año
        # ------------------------------------------------------------------
        print("\n[FASE 2] Generando órdenes de venta históricas...")

        with engine.connect() as conn:
            id_offsets = {
                "sales_orders":      get_max_id(conn, "sales_orders")      + 1,
                "sales_order_lines": get_max_id(conn, "sales_order_lines") + 1,
                "invoices":          get_max_id(conn, "invoices")          + 1,
                "shipments":         get_max_id(conn, "shipments")         + 1,
            }

        total_orders = 0
        total_lines  = 0

        for year in range(2021, 2027):
            print(f"\n  [{year}] Generando datos... ", end="", flush=True)

            result = generate_year_sales(year, product_data, customer_ids, user_ids, id_offsets, pools)

            # Inserción masiva por tabla
            result["orders"].to_sql(
                "sales_orders", con=engine, if_exists="append",
                index=False, method="multi", chunksize=1_000,
            )
            result["lines"].to_sql(
                "sales_order_lines", con=engine, if_exists="append",
                index=False, method="multi", chunksize=1_000,
            )
            if not result["invoices"].empty:
                result["invoices"].to_sql(
                    "invoices", con=engine, if_exists="append",
                    index=False, method="multi", chunksize=1_000,
                )
            if not result["shipments"].empty:
                result["shipments"].to_sql(
                    "shipments", con=engine, if_exists="append",
                    index=False, method="multi", chunksize=1_000,
                )

            id_offsets    = result["new_offsets"]
            total_orders += result["n_orders"]
            total_lines  += result["n_lines"]

            print(
                f"✓  {result['n_orders']:,} órdenes | "
                f"{result['n_lines']:,} líneas | "
                f"{result['n_invoices']:,} facturas | "
                f"{result['n_shipments']:,} envíos"
            )

        # Sincronizar secuencias PostgreSQL tras IDs explícitos
        print("\n  Sincronizando secuencias...", end=" ", flush=True)
        with engine.connect() as conn:
            for tbl in ["sales_orders", "sales_order_lines", "invoices", "shipments"]:
                reset_sequence(conn, tbl)
            conn.commit()
        print("✓")

        # ------------------------------------------------------------------
        # FASE 3: Órdenes de compra
        # ------------------------------------------------------------------
        print("\n[FASE 3] Generando órdenes de compra...")
        seed_purchase_orders(db, product_data, user_ids)

        # ------------------------------------------------------------------
        # Resumen final
        # ------------------------------------------------------------------
        print("\n" + "=" * 65)
        print("  PROCESO COMPLETADO EXITOSAMENTE")
        print(f"  Total órdenes de venta  : {total_orders:,}")
        print(f"  Total líneas de venta   : {total_lines:,}")
        print(f"  Promedio líneas/orden   : {total_lines / max(total_orders, 1):.1f}")
        print("=" * 65)

    except Exception:
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
