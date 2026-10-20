# DCM Artefact Governance: research-software and artefact archive

> **Release v1.0.0.** Research-software and artefact archive accompanying the DCM Artefact Governance paper. The manuscript is not included.
>
> | Field | Value |
> |---|---|
> | Author | Seyed Ahmad Mahmoudi Lahijani, Auckland University of Technology, ORCID [0000-0002-5086-5745](https://orcid.org/0000-0002-5086-5745) |
> | Repository | <https://github.com/Ahmad-Mahmoudi-coder/DCM-Artefact-Governance> |
> | Release tag | `v1.0.0` |
> | Archive DOI | None. This release has not been deposited in Zenodo or any other archive |
> | Licence | Code: MIT (`LICENSE`). Original data and documentation: CC BY 4.0 (`LICENSE-DATA.md`). Third-party values excluded (see *Licensing*) |

This repository is the research-software and artefact archive accompanying the DCM Artefact
Governance paper, *An Artefact-Level Governance Pattern for Model Outputs Under Deep Uncertainty*,
which is in preparation for *Environmental Modelling & Software*. It contains the schemas, code, fixtures,
governed artefacts, input data and figure scripts needed to re-run the paper's governance checks,
recomputations, screening calculations and Figure 2. **The manuscript itself is not included.**

## Purpose and relationship to the wider research

The archive lets a reader inspect and re-run the paper's demonstration. The paper examines how a
model output exchanged between analytical components can carry its contract, validation evidence,
identity, provenance and use-specific qualification, using two artefact families:

- the IncrementalElectricityPack (IEP), passed from process-heat analysis to a grid-adequacy screen;
- the BiomassSupplyPack (BSP), a narrower regional resource-screening example.

Both come from the author's doctoral research on Decision-Centred Modelling (DCM) and its
industrial process-heat proof of concept for the Edendale dairy site, New Zealand (Auckland
University of Technology). This repository is a curated, paper-specific extract of that work. It
does not contain the full proof-of-concept model, the dispatch model that produced the hourly
traces, or other parts of the research environment. `PROVENANCE.csv` gives the origin, source commit
and SHA-256 of every file taken from the author's private research repositories. Values taken from
published reports are attributed in `DATA_SOURCES.md`; no source report is included.

## What this release does and does not show

The release lets a reader re-execute **software checks and calculations on supplied inputs**. A
passing step means the code reproduces the reported number or check from those inputs. It is not
validation of the underlying process-heat, dispatch or biomass-resource models.

- **42 canonical IncrementalElectricityPack (IEP) artefacts** pass the declared closed-schema checks (S04).
- **Direct real-trace checking** covers three fields (annual energy, peak, p95) in each of the two
  `future_0` baseline artefacts, one per pathway (S07, S08, S10).
- **The other 40 annual values** are constructed by applying disclosed future-specific multipliers
  (`rdm/futures.csv`) to the baseline trace sum. The release checks that construction (S10); it
  **cannot regenerate the upstream model run or the multiplier draw**, which are supplied as inputs.
- **Peak and p95 repeat across futures** within each pathway because they derive from one shared
  hourly trace per pathway (S04, S10).
- **The retrospective Path A/Path B screening calculation** gives four tier changes among the 42
  artefacts (2035_EB futures 3, 5, 7, 18) (S14).
- **The retained wrapper** reproduces six specified cases (both pathways, futures 0, 5, 20), with one
  tier change (S13). Its author knew the governance record; this is **not an independent consumer evaluation**.
- **The future_5 screening result** (Figure 2; S20–S22) is a modelled consequence under configured synthetic assumptions
  (50 MW synthetic headroom base; configured upgrade menu including an illustrative 150 MW tier). It is
  not an infrastructure decision or an approved investment estimate.
- **BiomassSupplyPack (BSP)** is a second, narrower implementation. Its arithmetic and configuration
  checksum recompute from declared inputs (S17); the external resource and delivered-cost estimates
  were **not independently validated** from primary analyses, which the project does not hold.
- Nothing here establishes general transferability, full DCM validation, independent analyst
  agreement, improved decision quality, or automated prevention of unsupported interpretation.

## Contents

| Path | Contents |
|---|---|
| `schemas/artefacts/` | IEP and BSP JSON Schemas (Draft 2020-12, closed) |
| `schemas/examples/` | 8 IEP schema fixtures; 4 BSP fixtures |
| `tests/fixtures/incremental_electricity_pack_external/` | External-validator fixtures: 6 scenarios in 11 files |
| `tools/` | IEP adapter, external trace validator, and the schema-fixture, validator-fixture, artefact and registry checkers |
| `registry/future_sets/` | Future-set registry |
| `artefacts/incremental_electricity_pack/anchor_21_canonical_continuous_v1/` | The 42 canonical IEP artefacts analysed in the paper |
| `artefacts/incremental_electricity_pack/anchor_21/` | The 42 historical IEP artefacts they supersede (identity-coexistence check) |
| `Process-Heat-DCM/Output/runs/dispatch_optimal_subset_canonical_continuous_v1/` | Hourly incremental-electricity traces (2035_EB, 2035_BB), future-specific multipliers (`rdm/futures.csv`), adapter inputs, and the BB1 dispatch summary used by the biomass screen |
| `Process-Heat-DCM/Input/configs/` | Grid-upgrade screening menu; biomass supply-screen assumptions |
| `Process-Heat-DCM/Output/runs/gxp_downstream_qualification_consumer_v1/` | Reference output of the six-case retained wrapper |
| `Process-Heat-DCM/Output/runs/biomass_supply_screen_formalised_v1/`, `…/biomass_supply_pack_v1/` | Formalised biomass screen and the BSP instance |
| `Process-Heat-DCM/src/` | Grid-adequacy screening functions, retained wrapper, BSP screen, producer and validator, utilities |
| `references/` | Identifier-only evidence and source registers used by the BSP validator |
| `reports/validation/` | Shared-trace reference values, `qualification_codes` field diff, public extract of the validation-evidence summary with applicability notes |
| `figures/` | Figure scripts, published figure files, captions (`FIGURES.md`), manuscript-reported screening values |
| `scripts/` | Reproduction helpers added for this release |
| `reproduce.py` | Single reproduction entry point |
| `REPRODUCIBILITY_MATRIX.md` | Each manuscript result → inputs, code, command, expected output, status |
| `LICENSE`, `LICENSE-DATA.md` | Licences: MIT for code; CC BY 4.0 for original data and documentation; third-party exclusions |
| `DATA_SOURCES.md` | Attribution of all values taken from published reports |
| `EECA_CONTENT_INVENTORY.csv` | Every file that states, restates or derives from EECA (2022) values |
| `PROVENANCE.csv`, `MANIFEST.sha256` | Per-file origin and integrity |
| `CITATION.cff` | Citation metadata (draft) |
| `RELEASE_NOTES.md` | Release note |

`Process-Heat-DCM/` keeps the name of the source repository because the scripts locate files relative
to it and recorded producer identities use that name. Only the files listed in `PROVENANCE.csv` are
included; the source repository itself is not part of this release.

## Installation

Tested with CPython 3.12 (3.12.3 and 3.12.14) on Linux x86_64. No network access, credentials or
environment variables are needed after installation.

```bash
python3.12 -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -r requirements-paper.txt
```

## Reproduction

```bash
python reproduce.py --list        # steps, manuscript items, inputs
python reproduce.py               # run all 27 steps (under a minute)
sha256sum -c MANIFEST.sha256      # optional: confirm no package file changed
```

Outputs, regenerated figures and per-step logs are written only to `reproduction_outputs/`. A step
reports `PASS` only when its exit status matches the expected one (S09 and three BSP fixtures are
expected to fail). Expected result: 27 passed, 0 failed, 0 skipped. See `REPRODUCIBILITY_MATRIX.md`
for the manuscript item each step supports.

Manuscript numbering (Version 9): the evidence-status table is **Table 3**. **Figure 2** is produced
by `figures/scripts/render_fig2_screening.py` (S21) from the screening code and supplied inputs, and
S22 checks that the regenerated PNG and PDF are byte-identical to
`figures/published/fig2_screening_sensitivity_2035EB_future5.{png,pdf}`; the PNG is the image placed
in the manuscript. S20 derives the tier thresholds and the Path A/Path B selections directly from the
screening implementation and compares them with the reported values.

`render_fig2.py` and `render_fig3.py` (S11, S15) render the two data figures of manuscript Version 8.
They are kept as supplementary checks and are not in Version 9; their published files were rendered
with Matplotlib 3.10.9 and are not expected to be byte-identical to the regenerated ones.

## Executed checks versus historical records

`reproduce.py` executes every check listed in `REPRODUCIBILITY_MATRIX.md`. Some validation records
cited in the manuscript are **historical only** and are reported, not re-executed:

- VAL-023 and VAL-025 (schema change and field-by-field comparison when `qualification_codes` was
  added) — the pre-change artefacts are not shipped; the comparison output is in `reports/validation/`.
- VAL-050 freeze re-run — the release re-runs the separate baseline recomputation (S10), but not the
  original freeze re-run. The manuscript's bound of 1.16 × 10⁻¹⁰ MWh is historical; S10 obtains a
  difference of 0 MWh with numpy summation, which satisfies the bound.
- VAL-045 to VAL-049 concern the historical BSP instance; the released instance is validated by S16–S19
  and regenerated by E2 (see `reports/validation/PUBLIC_EXTRACT_NOTES.md`).
- VAL-010 (registry-backed validation) is deferred and VAL-013 is not applicable, as stated in Table 3.

## Grid-upgrade screening menu

The menu (`Process-Heat-DCM/Input/configs/grid_upgrades_southland_edendale.toml`) combines three
connection options published by EECA (2022, p. 74) with a 150 MW option. The 150 MW option and its
NZ$75.0 million capital cost are an illustrative screening assumption whose derivation is not
documented; they are not an official or engineering estimate. Tier selection depends on capacity
adequacy, not cost. See `DATA_SOURCES.md`.

## Changes made when assembling this package

`PROVENANCE.csv` records each file's status (`copied_unchanged`, `modified_in_staging`,
`regenerated_in_staging`, `derived_in_staging` or `new_in_staging`), source repository, path, commit
and SHA-256. Source commits: DCM-Research `c172eb0`, Process-Heat-DCM `266d7f5` (both private).

- **Figure scripts** use repository-relative paths and an output directory and contain no hard-coded
  result values; `verify.py` reads the manuscript values from `figures/expected/`.
- **Retained wrapper** gains an `--out-dir` option and an optional menu-path override; manifest paths are
  repository-relative. The calculation is unchanged and its output table is identical to the reference.
- **BSP chain**: input paths are recorded relative to the workspace instead of as absolute local paths,
  and one context-only regional figure from a third report (unused in any calculation or in the paper)
  was removed. Every numerical value is unchanged. The released instance therefore has `artefact_id`
  `8b425beb-1a3f-583e-b057-2fb049b4a90b`; the historical instance (`37c1647e-…`) is recorded in VAL-047.
- **Grid-upgrade menu**: comments only (attribution header; option 4 described as illustrative).
- **Version 9 alignment**: manuscript-item labels in `reproduce.py` and docstrings in
  four scripts were renumbered for Version 9; the description string in
  `figures/expected/paper_reported_screening_values.json` was updated.
- **Final Figure 2**: added `figures/scripts/render_fig2_screening.py`,
  `scripts/verify_screening_tier_mapping.py`, `scripts/check_figure2_matches_published.py` and the
  published Figure 2 files, and registered S20–S22 in `reproduce.py`.
- No calculation, tolerance, input or expected value was changed in either step.
- **Line endings**: IEP artefacts keep the line endings on which validation hashes were computed;
  `.gitattributes` disables conversion.

Comments and docstrings in some scripts refer to decision records (`docs/NN…`) in the author's
private research record; those documents are not part of this release.

## Licensing

- **Code** (Python files, JSON Schemas, test fixtures, `reproduce.py`, requirements and build
  configuration): MIT licence, in `LICENSE`.
- **Original data and documentation** (IEP artefacts, traces, multipliers, configuration files,
  run outputs, registries, validation extract, figures and documentation): Creative Commons
  Attribution 4.0 International (CC BY 4.0), in `LICENSE-DATA.md`.
- **Third-party material is not licensed by this repository.** Values reproduced from EECA (2022),
  *Regional Energy Transition Accelerator (RETA): Southland – Phase One Report*, are attributed in
  `DATA_SOURCES.md` and located file by file in `EECA_CONTENT_INVENTORY.csv`. They remain subject to
  their source's terms. Where they appear inside a file that is otherwise licensed, the licence
  covers the rest of that file only.

## Citation

Please cite this release. Machine-readable metadata are in `CITATION.cff`.

- **This archive:** Mahmoudi Lahijani, S. A. (2026). *DCM Artefact Governance: research-software
  and artefact archive* (Version 1.0.0) [Software]. GitHub.
  https://github.com/Ahmad-Mahmoudi-coder/DCM-Artefact-Governance/releases/tag/v1.0.0
- **Associated paper:** the DCM Artefact Governance paper, *An Artefact-Level Governance Pattern for
  Model Outputs Under Deep Uncertainty*, is in preparation. Its full reference will be added here
  on publication.

Cite the release tag you used.
Cite EECA (2022) for the third-party values listed in `DATA_SOURCES.md`.
