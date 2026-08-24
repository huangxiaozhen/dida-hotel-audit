---
name: dida-hotel-audit
description: Fetch and analyze current Dida Content API static hotel records for identity, coordinates, policies, facilities, rooms, images, and other static-content questions. Use when a request includes Dida hotel IDs; do not use for prices, availability, reservations, or non-Dida IDs.
metadata:
  openclaw:
    primaryEnv: DIDA_AUDIT_ACCESS_KEY
    requires:
      anyBins:
        - python
        - python3
---

# Dida Hotel Audit

This is one reusable Dida static-data analysis Skill. Do not create another Skill merely because a user's static-data question has no specialized workflow. Unless the user explicitly asks to develop or extend tooling, fetch the relevant Dida records and let the current model analyze them against the request.

Never query Dida by constructing credentials yourself and never request credentials in chat.

## Task routing

- Two hotel IDs and a same-property or merge question: use `compare_hotels`.
- One hotel ID and an external map-coordinate check: use `audit_coordinate`.
- Any other Dida static-content question: use `fetch_hotels`, then analyze the returned records directly.

Existing specialized workflows are deterministic helpers inside this Skill, not separate Skills. Do not scaffold a new Skill or add a new named workflow during an ordinary audit request.

## General static analysis

1. Extract between 1 and 50 positive Dida hotel IDs. Ask only when an ID required by the request is missing or ambiguous.
2. Read [general static analysis rules](references/general-static-analysis.md).
3. Run the first available command, substituting all relevant IDs:

   - `python "{baseDir}/scripts/fetch_hotels.py" HOTEL_ID [HOTEL_ID ...] --language en-US`
   - `python3 "{baseDir}/scripts/fetch_hotels.py" HOTEL_ID [HOTEL_ID ...] --language en-US`

4. Treat `hotels` as the complete static records returned by the configured Dida account for that request. Give those records to the current model and answer the user's actual question from the relevant fields.
5. If external evidence is required, retrieve it from the provider requested by the user and clearly separate it from Dida data. If a record or field is missing, state that limitation instead of inventing a value.
6. Lead with the answer, then show the decisive evidence and Dida trace metadata. Do not dump the entire JSON unless the user asks for it.

## Compare two hotels

1. Extract exactly two positive Dida hotel IDs from the request. If either ID is missing or ambiguous, ask for it.
2. Read [comparison rules](references/comparison-rules.md) before interpreting the result.
3. Run the first available command, substituting the two IDs:

   - `python "{baseDir}/scripts/compare_hotels.py" HOTEL_ID_A HOTEL_ID_B --language en-US`
   - `python3 "{baseDir}/scripts/compare_hotels.py" HOTEL_ID_A HOTEL_ID_B --language en-US`

4. Treat the returned `hotels` array as the complete static records returned by the configured Dida account for that request. Use `comparison.evidence` for deterministic comparisons and inspect other returned static fields when they materially clarify identity.
5. If `ok` is false, a hotel is missing, or the gateway reports an authentication/API error, report the limitation. Do not infer or invent hotel data.

## Compare response

Lead with one of these conclusions:

- Same hotel — safe to treat as one property.
- Different hotels — do not merge automatically.
- Evidence insufficient — manual review required.

Then provide a compact comparison table covering name, address, coordinates and distance, telephone, postal code, destination, external mapping identifiers, and other decisive fields returned by Dida. Explain conflicts and missing data. Include the Dida trace ID and response timestamp when present.

The deterministic result is a conservative baseline. You may downgrade a conclusion to manual review when raw fields expose unresolved contradictions. Do not upgrade manual review to a definite match based only on similar names, rooms, facilities, or descriptions.

## Audit one hotel's coordinates

1. Extract one positive Dida hotel ID and read [coordinate audit rules](references/coordinate-audit-rules.md).
2. Fetch the Dida record with the first available command:

   - `python "{baseDir}/scripts/get_hotel.py" HOTEL_ID --language en-US`
   - `python3 "{baseDir}/scripts/get_hotel.py" HOTEL_ID --language en-US`

3. Use the returned name, address, destination, telephone, and other identity fields to locate the same property on the map provider requested by the user. Do not treat a similarly named place or a map viewport center as the hotel coordinate.
4. After independently verifying the map place and extracting its marker coordinates, run the first available command:

   - `python "{baseDir}/scripts/audit_coordinate.py" HOTEL_ID --reference-latitude LAT --reference-longitude LON --reference-provider "Google Maps" --reference-name "PLACE_NAME" --reference-url "SOURCE_URL" --threshold-meters 1000`
   - `python3 "{baseDir}/scripts/audit_coordinate.py" HOTEL_ID --reference-latitude LAT --reference-longitude LON --reference-provider "Google Maps" --reference-name "PLACE_NAME" --reference-url "SOURCE_URL" --threshold-meters 1000`

5. Report the Dida coordinate, verified reference coordinate, Haversine distance, threshold result, identity-matching evidence, source URL, and Dida trace metadata. If the map place identity or marker coordinate cannot be verified, report evidence insufficient instead of guessing.

## Security

Never display, log, copy, or ask for `DIDA_AUDIT_ACCESS_KEY`, Dida ClientID, Dida LicenseKey, Basic Authorization values, or protected-store contents. Do not pass access keys as command-line arguments. The helper reads the access key from a protected local store or runtime environment.
