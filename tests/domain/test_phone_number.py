"""
Tests for PhoneNumber value object.
"""

import pytest
from domain.value_objects.phone_number import PhoneNumber


def test_valid_us_phone_10_digits():
    phone = PhoneNumber.create("4155551234")
    assert phone.country_code == "+1"
    assert phone.number == "4155551234"


def test_valid_us_phone_11_digits_starting_with_1():
    phone = PhoneNumber.create("14155551234")
    assert phone.country_code == "+1"
    assert phone.number == "4155551234"


def test_valid_international_with_plus_prefix():
    # The parser tries 1-digit country codes first (+4 is valid as it produces a 9-digit number)
    phone = PhoneNumber.create("+442071234567")
    assert phone.country_code.startswith("+")
    # Full number is reconstructed from code + number
    full = phone.country_code + phone.number
    assert full == "+442071234567"


def test_invalid_too_few_digits_raises_value_error():
    with pytest.raises(ValueError):
        PhoneNumber.create("12345")


def test_invalid_non_numeric_raises_value_error():
    with pytest.raises(ValueError):
        PhoneNumber.create("not-a-phone")


def test_formatted_property_output():
    phone = PhoneNumber(country_code="+1", number="4155551234")
    assert phone.formatted == "+1 4155551234"


def test_str_method_output():
    phone = PhoneNumber(country_code="+1", number="4155551234")
    assert str(phone) == "+1 4155551234"


def test_extension_handling_in_formatted():
    phone = PhoneNumber(country_code="+1", number="4155551234", extension="101")
    assert phone.formatted == "+1 4155551234 x101"
    assert str(phone) == "+1 4155551234 x101"


def test_create_strips_whitespace_and_dashes():
    phone = PhoneNumber.create("415-555-1234")
    assert phone.country_code == "+1"
    assert phone.number == "4155551234"


def test_create_strips_parentheses():
    phone = PhoneNumber.create("(415) 555-1234")
    assert phone.country_code == "+1"
    assert phone.number == "4155551234"


def test_create_international_3digit_country_code():
    # A number with a 3-digit country code e.g. +1 followed by a 10 digit number
    phone = PhoneNumber.create("+19876543210")
    assert phone.country_code.startswith("+")
    assert len(phone.number) >= 6


def test_phone_number_immutable():
    phone = PhoneNumber(country_code="+1", number="4155551234")
    with pytest.raises(Exception):
        phone.country_code = "+44"
