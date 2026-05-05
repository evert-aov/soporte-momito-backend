import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
from app.modules.users.models import Role, Permission, RolePermission, User, Branch, Customer
from app.modules.products.models import ProductCategory, UnitOfMeasure, Product, Supplier, ProductSupplier
from app.core.security import get_password_hash
from datetime import datetime

# Import all models so Base knows about all tables
from app.modules.users import models as user_models  # noqa: F401
from app.modules.products import models as product_models  # noqa: F401
from app.modules.inventory import models as inventory_models  # noqa: F401
from app.modules.orders import models as order_models  # noqa: F401


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clean in dependency order (children first)
        from app.modules.orders.models import (
            SalesOrderLine, SalesOrder, PurchaseOrderLine,
            PurchaseOrder, Invoice, Shipment
        )
        from app.modules.inventory.models import BranchInventory
        from app.modules.users.models import CrmInteraction

        db.query(Invoice).delete()
        db.query(Shipment).delete()
        db.query(SalesOrderLine).delete()
        db.query(SalesOrder).delete()
        db.query(PurchaseOrderLine).delete()
        db.query(PurchaseOrder).delete()
        db.query(BranchInventory).delete()
        db.query(CrmInteraction).delete()
        db.query(User).delete()
        db.query(RolePermission).delete()
        db.query(Permission).delete()
        db.query(Role).delete()
        db.query(ProductSupplier).delete()
        db.query(Product).delete()
        db.query(Supplier).delete()
        db.query(ProductCategory).delete()
        db.query(UnitOfMeasure).delete()
        db.query(Customer).delete()
        db.query(Branch).delete()
        db.commit()

        # Roles
        roles = [
            Role(name="SUPER_ADMIN", description="Full system access"),
            Role(name="VENDEDOR", description="Sales representative"),
            Role(name="CLIENTE", description="Customer portal access"),
        ]
        for r in roles:
            db.add(r)
        db.commit()
        for r in roles:
            db.refresh(r)

        # Permissions
        perms = [
            Permission(name="view_inventory"),
            Permission(name="create_order"),
            Permission(name="approve_po"),
            Permission(name="manage_users"),
            Permission(name="view_reports"),
        ]
        for p in perms:
            db.add(p)
        db.commit()
        for p in perms:
            db.refresh(p)

        # Assign all permissions to SuperAdmin
        for perm in perms:
            rp = RolePermission(role_id=roles[0].id, permission_id=perm.id)
            db.add(rp)
        db.commit()

        # Branch
        branch = Branch(name="Sucursal Principal", location="Santa Cruz, Bolivia")
        db.add(branch)
        db.commit()
        db.refresh(branch)

        # SuperAdmin user
        admin = User(
            role_id=roles[0].id,
            full_name="Super Admin",
            email="admin@tumomito.com",
            password_hash=get_password_hash("password123"),
            is_active=True,
            branch_id=branch.id,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

        # Vendedor user
        vendedor = User(
            role_id=roles[1].id,
            full_name="Juan Vendedor",
            email="vendedor@tumomito.com",
            password_hash=get_password_hash("password123"),
            is_active=True,
            branch_id=branch.id,
        )
        db.add(vendedor)
        db.commit()

        # UOM
        uom_unit = UnitOfMeasure(name="Unidad")
        uom_dozen = UnitOfMeasure(name="Docena")
        db.add_all([uom_unit, uom_dozen])
        db.commit()
        db.refresh(uom_unit)
        db.refresh(uom_dozen)

        # Categories
        cat1 = ProductCategory(name="Bebidas")
        cat2 = ProductCategory(name="Snacks")
        db.add_all([cat1, cat2])
        db.commit()
        db.refresh(cat1)
        db.refresh(cat2)

        # Supplier
        supplier = Supplier(
            name="Proveedor Alfa S.R.L.",
            country_of_origin="Bolivia",
            email="ventas@alfa.com"
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)

        # Products
        products = [
            Product(
                id="PROD001", default_code="SKU-001",
                name="Coca Cola 2L", type="Storable",
                category_id=cat1.id, uom_id=uom_unit.id, uom_po_id=uom_dozen.id,
                list_price=8.50, standard_price=5.00, active=True
            ),
            Product(
                id="PROD002", default_code="SKU-002",
                name="Pepsi 1.5L", type="Storable",
                category_id=cat1.id, uom_id=uom_unit.id, uom_po_id=uom_dozen.id,
                list_price=7.50, standard_price=4.50, active=True
            ),
            Product(
                id="PROD003", default_code="SKU-003",
                name="Chips Lay's", type="Storable",
                category_id=cat2.id, uom_id=uom_unit.id, uom_po_id=uom_unit.id,
                list_price=5.00, standard_price=2.50, active=True
            ),
        ]
        for p in products:
            db.add(p)
        db.commit()

        # Product-Supplier links
        for prod in products:
            ps = ProductSupplier(
                product_id=prod.id,
                supplier_id=supplier.id,
                supplier_product_name=prod.name,
                min_qty=10,
                delay=3,
            )
            db.add(ps)
        db.commit()

        # Customer
        customer = Customer(
            segment="B2B",
            commercial_name="Distribuidora El Buen Sabor",
            legal_name="El Buen Sabor S.R.L.",
            tax_id="1234567890",
            credit_limit=50000,
            phone="+591 70012345",
            delivery_address="Av. Roca y Coronado, Santa Cruz",
            registration_date=datetime.utcnow(),
        )
        db.add(customer)
        db.commit()

        # Branch inventory
        from app.modules.inventory.models import BranchInventory
        for prod in products:
            inv = BranchInventory(
                product_id=prod.id,
                branch_id=branch.id,
                quantity=100,
                min_stock=10,
                last_updated=datetime.utcnow(),
            )
            db.add(inv)
        db.commit()

        print("Seed completed successfully!")
        print(f"   - Roles: {len(roles)}")
        print(f"   - Branch: {branch.name}")
        print(f"   - Admin: admin@tumomito.com / password123")
        print(f"   - Vendedor: vendedor@tumomito.com / password123")
        print(f"   - Products: {len(products)}")
        print(f"   - Supplier: {supplier.name}")
        print(f"   - Customer: {customer.commercial_name}")

    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
