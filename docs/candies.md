# Candy economy

Candies are specific to a type; they are not a universal currency. Captures
and achievements provide candies, while evolution and Candy Shops spend them.
Two-type creatures use the candies of both types according to the listed shop
price. A balance is checked and updated atomically when a shop purchase is
confirmed.

Shop prices are initial values and may be adjusted using observed economy
metrics after release.
