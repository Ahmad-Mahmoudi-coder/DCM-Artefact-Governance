# Notes on `validation_summary.v0.2.public_extract.csv`

The extract reproduces 40 records of the authors' private validation-evidence summary
byte-for-byte (VAL-001 to VAL-032 and VAL-044 to VAL-051). The records are historical: each
describes the files that existed when the check was run. They have not been edited. Where a
record concerns a file that was later replaced, it is kept as a historical record and does
**not** validate the replacement. `validation_record_applicability.csv` gives the same
information in tabular form.

## BiomassSupplyPack (BSP): historical instance versus released instance

The BSP files were regenerated for this release. Input paths are now recorded relative to the
repository, and a context-only regional figure that no calculation uses was removed. Numerical
content is unchanged.

| | Historical instance (private record) | Released instance (this package) |
|---|---|---|
| `artefact_id` | `37c1647e-30d1-5a01-955d-076bdb40d58d` | `8b425beb-1a3f-583e-b057-2fb049b4a90b` |
| Instance SHA-256 | `3373887e6aa0e6feee9af93ecf340950b6f9f613abb35530aec89090232273ed` | `fdf369ee259bb60585c01e22583c4ea069063597877843f81e3eed9e5e00730f` |
| Formalised summary SHA-256 | `f31bd6316452a0e07d2772a358ceec056ae23bbcdd2947fc24a16c1499bef0b4` | `bb9e6597b02982cb9e6e25a9f9d5a46aefc6b2067f403764e8b7c115c1329b1c` |
| Evidence / source identifiers | 7 / 3 | 6 / 2 |

| Record | What it records | Concerns | Validates the released instance? | Current check in this package |
|---|---|---|---|---|
| VAL-044 | BSP schema structure; schema SHA-256 `2f141aa1…` | BSP schema (unchanged; hash matches the released file) | Not an instance check; applies to the released schema | S16 |
| VAL-045 | Four BSP fixtures; valid-fixture SHA-256 `28b7f064…` | Historical fixtures | **No** — historical record | S19 (×4), run on the regenerated fixtures |
| VAL-046 | Arithmetic reproducibility; **records the historical instance SHA-256 `3373887e…`** | Historical instance | **No** — historical record (the recomputed shares and assumptions-file hash it reports are numerically the same for the released instance) | S17 |
| VAL-047 | Identity and record-level provenance; **records the historical `artefact_id` `37c1647e…`** and 7 evidence / 3 source identifiers | Historical instance | **No** — historical record; identity and identifiers differ | S17 (identity and register checks are reported explicitly in its log) |
| VAL-048 | Structured-field qualification consumer | Historical instance | **No** — historical record | S18 |
| VAL-049 | Integrity of protected files and legacy bundles in the private repository; records the historical formalised-summary SHA-256 `f31bd631…` | Private repository files, most not in this package | **No**, and it cannot be re-run from this package | none |

S17 and S18 run against `Process-Heat-DCM/Output/runs/biomass_supply_pack_v1/biomass_supply_pack.v1.0.json`
(SHA-256 `fdf369ee…`). Supplementary step E2 regenerates that instance and confirms the same hashes and identity.

## Other records that cannot be re-executed from this package

- **VAL-023** records a one-off schema edit. The resulting behaviour is checked by S01.
- **VAL-025** compares the artefacts with a pre-change snapshot that was not retained. Its result table is included as `qualification_codes_canonical_field_diff.v0.1.csv`.
- **VAL-010** (deferred) and **VAL-013** (not applicable) are status records, not executable checks.
- **VAL-051** names the private consumer script. The released copy differs only in its output option and manifest wording, and S13 confirms that its result table is identical to the reference output. The reference manifest records the SHA-256 of the grid-menu file before its comments were revised for release; the menu values are unchanged.

Records VAL-001 to VAL-032 otherwise concern files that are included unchanged; the README maps them to steps S01–S15.
