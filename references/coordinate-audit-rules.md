# Coordinate audit rules

Use these rules only for a single-hotel coordinate-quality check.

## Verify the reference property

Confirm that the external map result represents the same hotel as the Dida record. Prefer several independent matches, such as:

- distinctive hotel name or an established name variant;
- street address, city, and country;
- telephone number;
- official website or another strong property identifier.

A shared city and a similar generic name are not enough. If multiple plausible map places remain, stop with `evidence insufficient`.

## Select the reference coordinate

Use the hotel place marker or place-detail coordinate. Do not use:

- the map viewport center shown after a broad search;
- coordinates copied from the Dida record or a page that merely republishes Dida data;
- a street, neighborhood, city-center, or nearby landmark coordinate;
- coordinates inferred only from an unverified URL slug.

For Google Maps, preserve the place URL used as evidence. A coordinate embedded in a canonical place URL can be used only when the surrounding place result has been independently matched to the Dida hotel. Treat an `@latitude,longitude` map-center value cautiously because it can represent the viewport rather than the marker.

## Distance and conclusion

The bundled script computes the WGS84-like great-circle distance with the Haversine formula.

- Distance at or below the requested threshold: coordinate is within tolerance.
- Distance above the requested threshold: coordinate is outside tolerance.
- Unverified place identity or marker coordinate: evidence insufficient, regardless of the numeric distance.

Distance alone does not prove the map result is the same hotel. Always report the identity evidence and both data sources.
