# General static analysis rules

Use this fallback for Dida static-content questions that are not hotel-identity comparison or coordinate audit.

## Execution boundary

- Do not create a new Skill or specialized workflow for an ordinary question.
- Fetch the requested hotel records through `fetch_hotels.py` and analyze them with the current model.
- Modify or create tooling only when the user explicitly requests development work.

## Evidence model

Use only fields actually present in the returned Dida records. Relevant groups can include:

- hotel identity, category, chain, brand, star rating, address, telephone, destination, regions, and coordinates;
- descriptions, check-in/out policy, child and extra-bed policy, fees, notices, facilities, and services;
- room types, occupancy, bed/window/view/smoking attributes, room facilities, room policies, and images;
- hotel images, room count, opening date, review score, GIATA codes, and Vervotech codes.

Field absence means `not returned by the configured Dida account`, not `false`, `none exists`, or `the hotel does not provide it`. Dida may return different field coverage for different hotels or account configurations.

## Model analysis

- Answer the user's question rather than summarizing every field.
- Quote exact short values when useful, but summarize long HTML descriptions and policies.
- Distinguish direct Dida facts, calculations or inferences, and external-source facts.
- For comparisons, show aligned fields and explain missing data.
- For a conclusion that depends on current external facts, verify those facts with an appropriate source and cite it.
- If evidence cannot support a definite conclusion, say `evidence insufficient` and identify what is missing.

Always include the Dida trace ID and response timestamp when present so the result can be audited.
