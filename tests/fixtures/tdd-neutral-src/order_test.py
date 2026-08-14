import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from order import submit, side_effect_count
submit("m1")
submit("m1")
if side_effect_count() != 1:
    print("FAIL duplicate_submit: side effects =", side_effect_count())
    sys.exit(1)
print("PASS")
