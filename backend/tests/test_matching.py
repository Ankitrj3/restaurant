import pytest
from services.matching_service import matching_service

def test_normalize_name():
    assert matching_service.normalize_name("Chicken Biryani (2pc)") == "chicken biryani"
    assert matching_service.normalize_name("  Paneer   Tikka  Masala ") == "paneer tikka masala"
    assert matching_service.normalize_name("Mutton Dum Biryani (Large)") == "mutton dum biryani"
    
def test_similarity_score():
    score_exact = matching_service.similarity_score("Chicken Biryani", "Chicken Biryani")
    assert score_exact == 1.0
    
    score_fuzzy = matching_service.similarity_score("Chicken Biryani", "Chkn Briyani")
    assert score_fuzzy > 0.5  # Should be reasonably high

    score_diff = matching_service.similarity_score("Chicken Biryani", "Samosa")
    assert score_diff < 0.4
    
def test_find_best_match():
    candidates = [
        {"item_name": "Goat Curry", "category": "Curry"},
        {"item_name": "Chicken Tikka", "category": "Starters"},
        {"item_name": "Chicken Biryani", "category": "Biryani"}
    ]
    match, score = matching_service.find_best_match("Chkn Briyani", candidates)
    assert match is not None
    assert match["item_name"] == "Chicken Biryani"
    assert score > matching_service.threshold

def test_match_menus():
    menu_a = [{"item_name": "Chicken Biryani", "price": 15}]
    menu_b = [{"item_name": "Chkn Biryani", "price": 16}, {"item_name": "Samosa", "price": 5}]
    
    matches = matching_service.match_menus(menu_a, menu_b)
    
    # One matched, one unmatched from b
    assert len(matches) == 2
    matched_pair = next(m for m in matches if m['item_a'] is not None and m['item_b'] is not None)
    assert matched_pair['item_a']['item_name'] == "Chicken Biryani"
    assert matched_pair['item_b']['item_name'] == "Chkn Biryani"
