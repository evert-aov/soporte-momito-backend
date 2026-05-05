# TUMOMITO Backend

FastAPI + PostgreSQL backend para el sistema ERP y e-commerce de TUMOMITO S.A.

## Requisitos del sistema

- Python 3.11+
- PostgreSQL 14+
- `pip` y `venv`

## Dependencias Python

```
fastapi>=0.115.0
uvicorn[standard]>=0.29.0
sqlalchemy>=2.0.30
psycopg2-binary>=2.9.9
pydantic[email]>=2.10.0
pydantic-settings>=2.3.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
bcrypt==4.2.1
python-dotenv>=1.0.1
python-multipart>=0.0.9
alembic>=1.13.1
httpx>=0.27.0
```

## Configuración

Crear un archivo `.env` en la carpeta `backend/`:

```env
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/tumomito
JWT_SECRET=tu_secreto_jwt_aqui

# PayPal (opcional, sandbox por defecto)
PAYPAL_CLIENT_ID=
PAYPAL_SECRET=
PAYPAL_MODE=sandbox
```

## Instalación y ejecución

```bash
# 1. Crear y activar el entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno (ver sección anterior)
cp .env.example .env            # si existe, o crear manualmente

# 4. Iniciar el servidor de desarrollo
uvicorn main:app --reload --port 8000
```

La API quedará disponible en `http://localhost:8000`.  
Documentación interactiva en `http://localhost:8000/docs`.

## Datos iniciales (seed)

Para poblar la base de datos con datos de prueba:

```bash
python seed.py
```

## Verificar endpoints

```bash
python test_endpoints.py
```

## Estructura del proyecto

```
backend/
├── main.py              # Punto de entrada, registro de routers y creación de tablas
├── database.py          # Sesión SQLAlchemy y clase Base
├── requirements.txt
├── seed.py
├── test_endpoints.py
└── app/
    ├── core/
    │   └── config.py    # Variables de entorno (pydantic-settings)
    └── modules/
        ├── auth/        # JWT login → /api/auth/token
        ├── users/       # Usuarios, roles, permisos, clientes, sucursales
        ├── products/    # Productos, categorías, proveedores
        ├── inventory/   # Stock por sucursal (BranchInventory)
        └── orders/      # Pedidos de venta/compra, facturas, envíos, PayPal
```

## Flujos de estado de pedidos

```
Venta:    draft → pending_payment → paid → confirmed → picking → dispatched → delivered
Compra:   draft → confirmed → received
```

- El stock se **descuenta** cuando la venta llega a `dispatched`.
- El stock se **incrementa** cuando la compra llega a `received`.
- Las facturas se generan automáticamente cuando el pedido alcanza el estado `paid`.
