# Reproducibility matrix — manuscript Version 9

Status key: **Executed** = re-run by `python reproduce.py` and compared with the reported value or
expected outcome; **Executed (supplementary)** = re-run, not a manuscript item; **Historical** =
recorded in the validation extract, not re-executable from this release; **Not reproducible** =
upstream step whose inputs or code are not available. Step IDs refer to `reproduce.py` (27 steps: S01–S22 and E1–E2). Executed
status means the software reproduces the result from the supplied inputs, not that the underlying
model is validated.

## IncrementalElectricityPack (IEP)

| Manuscript item | Reported result | Inputs | Code | Step | Status |
|---|---|---|---|---|---|
| §4.2; Table 3 VAL-001 | Schema fixture harness passes (six fixtures at VAL-001; eight after VAL-026) | `schemas/examples/incremental_electricity_pack.*` | `tools/check_incremental_electricity_schema_fixtures.py` | S01 | Executed |
| §4.2 | Schema: eleven required fields, closed | IEP schema | — | (inspection) | Schema has 11 required and **3** optional fields; manuscript says two optional (see audit) |
| Table 3 VAL-002; §5.1 | External-validator fixtures pass ("eleven fixtures" = 6 scenarios, 11 files) | `tests/fixtures/incremental_electricity_pack_external/` | `tools/check_incremental_electricity_external_validator_fixtures.py` | S02 | Executed |
| Table 3 VAL-006/017; §5.1 | 42/42 canonical artefacts schema-valid; p95 ≤ peak | 42 canonical artefacts | `tools/check_anchor21_incremental_electricity_artifacts.py` | S04 | Executed |
| Table 3 VAL-020/021; §5.1 | future_0 baselines: EB 827,272.72 MWh, 132.998 MW, 123.784 MW; BB 480,121.21 MWh, 92.594 MW, 83.380 MW | 2 future_0 artefacts; 2 hourly traces | `tools/validate_incremental_electricity_pack_external.py` | S07, S08 | Executed |
| Table 3 VAL-022; §5.1 | future_5 diagnostic: annual field differs from unscaled trace sum (expected) | EB future_5 artefact; EB trace | external validator | S09 (expected exit 1) | Executed |
| §5.1 | future_5 annual = 868,636.3542 MWh (= unrounded baseline × 1.05) | artefacts; `rdm/futures.csv` | `scripts/recompute_baseline_and_shared_trace.py` | S10 | Executed |
| Table 3 VAL-050; §5.1 | Separate recomputation corroborates baselines; annual difference ≤ 1.16 × 10⁻¹⁰ MWh | traces; artefacts | `scripts/recompute_baseline_and_shared_trace.py` | S10 | Executed (difference obtained: 0 MWh, within the bound). The original freeze re-run is **Historical** |
| §5.1 | Annual 0.95–1.10 × future_0, sixteen levels; peak/p95 identical across 21 futures | artefacts; `futures.csv` | S10 script; `figures/scripts/verify.py` | S10, S12 | Executed |
| §5.1 (40 constructed values) | Annual values = baseline trace sum × disclosed multipliers | `futures.csv` | S10 script | S10 | Construction Executed; **multiplier draw and upstream model run Not reproducible** |
| Table 3 VAL-019; §5.1 | Historical and canonical generations coexist without identifier collision; historical files unchanged | both artefact sets | `scripts/check_generation_coexistence.py`; S05 | S05, S06 | Executed |
| Table 3 VAL-023/026 | `qualification_codes` schema change; fixtures re-run | — | — | S01 (re-run part) | VAL-026 Executed via S01; VAL-023 **Historical** |
| Table 3 VAL-025 | `qualification_codes` is the only added key | `reports/validation/` diff | — | — | **Historical** (pre-change artefacts not shipped) |
| Table 3 VAL-010 / VAL-013 | Deferred / not applicable | — | — | — | As reported |
| §4.1 (adapter) | Adapter maps canonical outputs to IEP without modifying upstream model | `rdm/rdm_summary_*.csv`, `thesis_pack/…` | `tools/build_incremental_electricity_pack_anchor21_from_real_outputs.py` | E1 | Executed (supplementary): regenerated artefacts identical |

## Downstream screening

| Manuscript item | Reported result | Inputs | Code | Step | Status |
|---|---|---|---|---|---|
| §5.2; Figure 2 | EB future_5: headroom 42.5 MW; Path A 132.998 MW → 97 MW tier; Path B 139.648 MW → 150 MW tier; threshold 139.5 MW; exceedance 0.148 MW; NZ$55.9M / NZ$75.0M | menu TOML; `futures.csv`; artefacts | `figures/scripts/verify.py` | S12 | Executed |
| §§4.3, 5.2, 6.4, 7 | Retrospective all-42 replay: four tier changes (EB futures 3, 5, 7, 18) | 42 artefacts; menu | `scripts/replay_all42_screening.py` | S14 | Executed |
| §§4.3, 5.2 | Retained wrapper reproduces six cases (both pathways × futures 0, 5, 20); one tier change | artefacts; menu; reference output | `Process-Heat-DCM/src/gxp_downstream_qualification_consumer.py` | S13 | Executed; output table identical to the reference |
| §5.2; Figure 2 | Tier thresholds 42.5/63.5/74.5/139.5/192.5 MW = 42.5 MW headroom + tier capacity; Path A → +97 MW; Path B → +150 MW; exceedance 0.148 MW; selection independent of cost | menu; `futures.csv`; EB future_5 artefact | `scripts/verify_screening_tier_mapping.py` (imports the retained wrapper) | S20 | Executed: thresholds found by bisection on the actual selection function |
| Figure 2 | Final manuscript figure | as S20 | `figures/scripts/render_fig2_screening.py` | S21, S22 | Executed: regenerated PNG and PDF byte-identical to `figures/published/`; the PNG is the image embedded in the manuscript |
| (supplementary) | Version 8 Figures 2 and 3 | artefacts; menu | `figures/scripts/render_fig2.py`, `render_fig3.py` | S11, S15 | Executed (supplementary; not in Version 9) |

## BiomassSupplyPack (BSP)

| Manuscript item | Reported result | Inputs | Code | Step | Status |
|---|---|---|---|---|---|
| §5.3 | Closed Draft 2020-12 schema, 29 required fields | BSP schema | `scripts/check_bsp_schema.py` | S16 | Executed |
| §5.3 | Four authored fixtures classified as intended (one valid; three invalid) | `schemas/examples/biomass_supply_pack.*` | `Process-Heat-DCM/src/validate_biomass_supply_pack.py` | S19 ×4 | Executed |
| §5.3 | 380,500 t/yr pool; BB1 202,615 t/yr; shares 53.25 % (mass), 53.16 % (energy); configuration checksum recomputes | BSP instance; assumptions TOML; BB1 summary | BSP validator | S17 | Executed (arithmetic only; external estimates **not independently validated**) |
| §5.3 | Structured-field consumer returns regional-screening interpretation, not site feasibility | BSP instance | BSP validator, `--mode qualification-consumer` | S18 | Executed (consumer coupled to validator; not independent) |
| §4.4 | Producer regenerates the supplied BSP files | assumptions; BB1 summary | `biomass_supply_screen.py`, `biomass_supply_pack_producer.py` | E2 | Executed (supplementary) |
| §5.3 | External resource and delivered-cost estimates | EECA (2022) | — | — | Values attributed in `DATA_SOURCES.md`; primary analyses **not available** |

## Not reproducible from any available material

- The upstream process-heat dispatch model run that produced the hourly traces (traces are supplied as inputs).
- The future-specific multiplier draw (`futures.csv`, inherited from the historical release02 ensemble).
- The primary analyses underlying the EECA (2022) resource and delivered-cost estimates.
- Independent analyst or consumer evaluation (not claimed by the manuscript).
