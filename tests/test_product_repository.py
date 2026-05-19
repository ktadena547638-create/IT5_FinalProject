"""Unit tests for ProductRepository CRUD and query operations."""

from decimal import Decimal

from main import ProductRepository, Product
from tests.conftest import DBManager


def test_product_save_and_get():
    """Test saving and retrieving product records."""
    db = DBManager()
    repo = ProductRepository(db)

    p = Product(
        sku="TST-001",
        name="Test Widget",
        brand="Acme",
        price=Decimal("9.99"),
        cost_price=Decimal("5.00"),
        quantity=10,
        category="Tools",
        supplier="Acme Co",
    )

    assert repo.save(p) is True
    fetched = repo.get_by_sku("TST-001")
    assert fetched is not None
    assert fetched.sku == "TST-001"
    assert fetched.name == "Test Widget"

    all_products = repo.get_all()
    assert any(prod.sku == "TST-001" for prod in all_products)

    assert repo.delete("TST-001") is True
    assert repo.get_by_sku("TST-001") is None
