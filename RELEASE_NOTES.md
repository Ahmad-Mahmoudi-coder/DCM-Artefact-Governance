# Release notes

## v1.0.0 (prepared 21 October 2026)

First release of the research-software and artefact archive accompanying the DCM Artefact
Governance paper, *An Artefact-Level Governance Pattern for Model Outputs Under Deep Uncertainty*
(in preparation for *Environmental Modelling & Software*). The manuscript is not included. The
publication date is the date of the GitHub release.

- Content as release candidate rc.3, with final metadata: repository URL, the final Figure 2
  caption in `figures/FIGURES.md`, and the public archive name "DCM Artefact Governance".
- Licences added:
  - `LICENSE`: MIT for code;
  - `LICENSE-DATA.md`: CC BY 4.0 for original data and documentation;
  - EECA-derived values excluded.
- README states the archive's purpose and its relationship to the wider research.
- `CITATION.cff` cites this archive as software; the preferred article citation added in rc.3 was
  removed because the paper is still in preparation.
- `python reproduce.py`: 27 steps (25 manuscript steps, 2 supplementary), all passing in a clean
  CPython 3.12 environment.
- Not deposited in Zenodo; no DOI.
- No calculation, input, expected value or figure changed since rc.2.

Earlier, unpublished release candidates are listed below for traceability.

## v1.0.0-rc.3 — release candidate (20 October 2026, unpublished)

- Figure 2 caption in `figures/FIGURES.md` replaced with the author's final V9 wording; the figure
  and its script are unchanged.
- `CITATION.cff` finalised for v1.0.0 (author and ORCID, preferred article citation); README
  citation section added.
- `DATA_SOURCES.md` §5 updated with the rights evidence checked on 20 October 2026.
- No calculation, input, expected value or figure changed.

## v1.0.0-rc.2 — release candidate (20 October 2026, unpublished)

- Final manuscript Figure 2: `figures/scripts/render_fig2_screening.py` renders a capacity-threshold step plot from the screening code and supplied inputs; the published PNG/PDF are byte-identical to the regenerated files (S21, S22).
- `scripts/verify_screening_tier_mapping.py` (S20) derives the tier thresholds and Path A/Path B selections from the screening implementation and checks the reported values.
- `python reproduce.py`: 27 steps (25 manuscript steps, 2 supplementary), all passing in a fresh CPython 3.12 environment.
- Rights: EECA-derived values documented as third-party material excluded from any licence grant (`DATA_SOURCES.md`).
- No calculation, input or expected value changed.

## v1.0.0-rc.1 — release candidate (20 October 2026, unpublished)

First release candidate of the paper-specific software and data package for "An Artefact-Level
Governance Pattern for Model Outputs Under Deep Uncertainty" (manuscript Version 9, prepared for
*Environmental Modelling & Software*).

- Contents: IEP and BSP schemas, fixtures, adapter, validators and harnesses; 42 canonical and 42
  historical IEP artefacts; hourly 2035_EB and 2035_BB traces; future-specific multipliers; grid-upgrade
  menu; retained six-case wrapper; all-42 replay; BSP screen, producer, validator, instance and
  consumer; figure scripts; validation-record extract.
- `python reproduce.py`: 24 steps (22 manuscript steps, 2 supplementary), all passing in a fresh
  CPython 3.12 environment.
- Changes from the v8 staging draft (12 Oct 2026): manuscript numbering updated for Version 9;
  `REPRODUCIBILITY_MATRIX.md`, `CITATION.cff` and this file added; no calculation, input or expected
  value changed.
- Known limitations: upstream model run and multiplier draw not regenerable; BSP external estimates
  not independently validated; VAL-023, VAL-025, the original VAL-050 freeze re-run and VAL-045–049
  are historical records; the image embedded as Figure 2 in Version 9 was not produced by a retained script (resolved in rc.2).
- Not yet assigned: software licence, data licence, repository URL, archive DOI.

Proposed tag for the archived submission release: `v1.0.0`. Revisions after peer review would be
released as later versions under the same Zenodo concept DOI.
