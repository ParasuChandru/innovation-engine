#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from app import calculate_priority_score

tests = [
    ("mixed", {'proj_savings': 150000, 'complexity': 'Medium', 'hours_saved': 1200, 'users_impacted': '5 users', 'confidence': 'Medium'}),
    ("50k", {'proj_savings': 50000, 'complexity': 'Medium', 'hours_saved': 500, 'users_impacted': '10 users', 'confidence': 'Medium'}),
    ("50001", {'proj_savings': 50001, 'complexity': 'Medium', 'hours_saved': 500, 'users_impacted': '10 users', 'confidence': 'Medium'}),
    ("1000h", {'proj_savings': 1000, 'complexity': 'Medium', 'hours_saved': 1000, 'users_impacted': '10 users', 'confidence': 'Medium'}),
    ("1001h", {'proj_savings': 1000, 'complexity': 'Medium', 'hours_saved': 1001, 'users_impacted': '10 users', 'confidence': 'Medium'}),
    ("50u", {'proj_savings': 1000, 'complexity': 'Medium', 'hours_saved': 100, 'users_impacted': '50 users', 'confidence': 'Medium'}),
    ("51u", {'proj_savings': 1000, 'complexity': 'Medium', 'hours_saved': 100, 'users_impacted': '51 users', 'confidence': 'Medium'}),
]

for name, idea in tests:
    r = calculate_priority_score(idea)
    print(f"{name}: raw={r['raw_score']}, breakdown={r['breakdown']}")
