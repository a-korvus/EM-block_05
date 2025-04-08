"""Some test tools."""

import logging
import random
import string
from datetime import datetime
from typing import Any

lgr = logging.getLogger(__name__)


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configurate a simple logger to fast use.

    Args:
        level (int, optional): Set a level of logging. Defaults to INFO.
    """
    logging.basicConfig(
        level=level,
        datefmt="%Y-%m-%d_%H:%M:%S",
        format=(
            "%(name)s %(levelname)s [%(asctime)s.%(msecs)02d] "
            "| %(module)s:%(lineno)d (%(funcName)10s) | %(message)s"
        ),
    )


def get_str_given_len(length: int) -> str:
    """
    Generate a random string of exactly 'length' characters.

    Args:
        length (int): The length of the output string.

    Returns:
        str: A random string with the specified length.
    """
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))


def fake_result() -> dict[str, Any]:
    """
    Generate some fake result of trades.

    Returns:
        dict[str, Any]: Random values of result fields.
    """
    return {
        "exchange_product_id": get_str_given_len(11),
        "exchange_product_name": get_str_given_len(255),
        "oil_id": get_str_given_len(4),
        "delivery_basis_id": get_str_given_len(3),
        "delivery_basis_name": get_str_given_len(255),
        "delivery_type_id": get_str_given_len(1),
        "volume": random.randint(1, 21),
        "total": random.randint(1, 21),
        "count": random.randint(1, 21),
        "date": datetime.now(),
    }


def fake_result_many() -> list[list[dict[str, Any]]]:
    """
    Generate some fake result of trades.

    Returns:
        list[list[dict[str, Any]]]: Random values of result fields.
    """
    return [
        [
            {
                "exchange_product_id": get_str_given_len(11),
                "exchange_product_name": get_str_given_len(255),
                "oil_id": get_str_given_len(4),
                "delivery_basis_id": get_str_given_len(3),
                "delivery_basis_name": get_str_given_len(255),
                "delivery_type_id": get_str_given_len(1),
                "volume": random.randint(1, 21),
                "total": random.randint(1, 21),
                "count": random.randint(1, 21),
                "date": datetime.now(),
            }
            for _ in range(random.randint(10, 30))  # num rows in the file
        ]
        for _ in range(random.randint(10, 20))  # num processed files
    ]
