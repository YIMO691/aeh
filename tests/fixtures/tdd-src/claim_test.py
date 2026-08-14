import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from reward import claim, side_effect_count
claim("m1")
claim("m1")
if side_effect_count() != 1:
    print("FAIL duplicate_reward: side effects =", side_effect_count())
    sys.exit(1)
print("PASS")
