from math import isclose
import pandas as pd

counts = pd.Series([2, 2, 0], index=["A", "B", "C"])
persistence = pd.Series([2/3, 2/3, 0], index=counts.index)
frequency_pct = counts.rank(method="average", pct=True)
persistence_pct = persistence.rank(method="average", pct=True)
scores = 100 * (0.60 * frequency_pct + 0.40 * persistence_pct)
scores = scores.where(counts.ne(0), 0)
assert all(isclose(x, y, abs_tol=1e-10)
           for x, y in zip(scores, [250/3, 250/3, 0]))

without_c = 100 * counts.loc[["A", "B"]].rank(method="average", pct=True)
assert all(isclose(x, 75, abs_tol=1e-10) for x in without_c)
district_0182 = 100 * (0.60 + 0.40 * (449 + (723 + 1)/2) / 1172)
assert isclose(district_0182, 87.67918088737201, abs_tol=1e-10)

print("Small case:", scores.round(6).to_dict())
print("Without C:", without_c.to_dict())
print("District 0182:", f"{district_0182:.6f}")
