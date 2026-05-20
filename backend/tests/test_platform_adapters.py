import pytest
from services.platform_adapters.base_adapter import BasePlatformAdapter
from services.platform_adapters.instore_adapter import instore_adapter
from services.platform_adapters.ubereats_adapter import ubereats_adapter
from services.platform_adapters.doordash_adapter import doordash_adapter
from services.platform_adapters.grubhub_adapter import grubhub_adapter

@pytest.fixture
def test_restaurant_name():
    return "Test Restaurant"

def test_instore_adapter_interface(test_restaurant_name):
    assert isinstance(instore_adapter, BasePlatformAdapter)
    assert instore_adapter.is_available() is True
    
    # In-store shouldn't crash if nothing is found
    menu = instore_adapter.fetch_menu(test_restaurant_name)
    assert isinstance(menu, list)
    
    fees = instore_adapter.fetch_delivery_fees(test_restaurant_name)
    assert isinstance(fees, dict)
    assert fees['delivery_fee'] == 0.0

def test_ubereats_adapter_interface(test_restaurant_name):
    assert isinstance(ubereats_adapter, BasePlatformAdapter)
    # Check fallback generation
    menu = ubereats_adapter.fetch_menu(test_restaurant_name)
    assert isinstance(menu, list)
    
    fees = ubereats_adapter.fetch_delivery_fees(test_restaurant_name)
    assert isinstance(fees, dict)
    assert 'delivery_fee' in fees
    assert 'service_fee' in fees

def test_doordash_adapter_interface(test_restaurant_name):
    assert isinstance(doordash_adapter, BasePlatformAdapter)
    # Check fallback generation
    menu = doordash_adapter.fetch_menu(test_restaurant_name)
    assert isinstance(menu, list)
    
    fees = doordash_adapter.fetch_delivery_fees(test_restaurant_name)
    assert isinstance(fees, dict)
    assert 'delivery_fee' in fees

def test_grubhub_adapter_interface(test_restaurant_name):
    assert isinstance(grubhub_adapter, BasePlatformAdapter)
    # Check fallback generation
    menu = grubhub_adapter.fetch_menu(test_restaurant_name)
    assert isinstance(menu, list)
    
    fees = grubhub_adapter.fetch_delivery_fees(test_restaurant_name)
    assert isinstance(fees, dict)
    assert 'delivery_fee' in fees
