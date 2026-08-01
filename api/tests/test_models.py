import pytest
from pydantic import ValidationError

from ecommerce_api.models import CheckoutIn


def test_checkout_normalizes_phone() -> None:
    value = CheckoutIn.model_validate(
        {
            "cart_token": "a" * 32,
            "customer": {
                "name": " Matías ",
                "email": "test@example.com",
                "phone": "+54 9 (11) 5555-0000",
            },
        }
    )
    assert value.customer.name == "Matías"
    assert value.customer.phone == "+5491155550000"


def test_checkout_rejects_unknown_payment_method() -> None:
    with pytest.raises(ValidationError):
        CheckoutIn.model_validate(
            {
                "cart_token": "a" * 32,
                "customer": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "phone": "+5491155550000",
                },
                "payment_method": "cash_on_delivery",
            }
        )
