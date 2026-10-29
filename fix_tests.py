import re

with open('tests/unit/test_parameter_robustness.py', 'r') as f:
    content = f.read()

# Replace sortino=Decimal("1.4") with sortino=Decimal("1.5")
content = content.replace('sortino=Decimal("1.4")', 'sortino=Decimal("1.5")')

with open('tests/unit/test_parameter_robustness.py', 'w') as f:
    f.write(content)

print("Done")