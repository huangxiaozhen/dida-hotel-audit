# Hotel identity comparison rules

Apply these rules when interpreting `compare_hotels` output.

## Evidence priority

1. Matching trusted third-party mapping identifiers are strong same-property evidence. Conflicting identifiers require corroboration because upstream mappings can also be wrong.
2. Exact telephone plus a nearby coordinate and compatible name/address is strong evidence.
3. Coordinate distance, full address, postal code, destination, and city should agree as a group.
4. Name similarity alone is never enough. Translations, rebrands, punctuation, and nearby properties can produce similar names.
5. Room types, room counts, facilities, descriptions, images, and star ratings are supporting evidence only. Supplier coverage can differ between duplicate records.

## Distance interpretation

- Up to 100 m: strong location agreement.
- 100–500 m: nearby and generally supportive.
- 500–1,000 m: weakly supportive; inspect address and telephone.
- Over 1,000 m: material conflict, not proof by itself.
- Over 5,000 m: strong conflict unless one coordinate is demonstrably erroneous.

Distances in the gateway output are calculated with the Haversine formula from the coordinates exactly returned by Dida.

## Conclusions

- `same_hotel`: multiple independent identifiers agree and there is no unresolved hard conflict.
- `different_hotels`: multiple independent fields conflict; advise against automatic merging.
- `manual_review` or `insufficient_data`: fields are missing, mixed, or cannot support a safe binary decision.

Do not hide missing fields. Use “not returned” rather than guessing a value.
