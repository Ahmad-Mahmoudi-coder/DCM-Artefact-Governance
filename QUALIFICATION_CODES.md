# Qualification codes

This file defines the controlled vocabulary of the `qualification_codes` field in
IncrementalElectricityPack (IEP) artefacts. The field is optional and its values are restricted by
a closed enumeration in `schemas/artefacts/incremental_electricity_pack.v1.0-current.schema.json`.

A qualification code records an analyst's judgement about which downstream inferences the available
evidence supports for an artefact's declared fields. It is distinct from schema conformity and from
the validation-stage fields `validation_outcome` and `warning_codes`. A code does not detect the
limitation it records, does not change any value in the artefact, and does not prescribe a downstream
treatment.

The vocabulary currently has one member.

## `FIELD_INVARIANT_ACROSS_FUTURES_WITHIN_PATHWAY`

| Element | Definition |
|---|---|
| Applies to | All 42 canonical IEP artefacts in `artefacts/incremental_electricity_pack/anchor_21_canonical_continuous_v1/` (pathways 2035_EB and 2035_BB, futures 0–20). The 42 historical artefacts in `artefacts/incremental_electricity_pack/anchor_21/` do not carry the code because they predate the field (VAL-025), although they share the same construction (VAL-013). |
| How it is assigned | The adapter `tools/build_incremental_electricity_pack_anchor21_from_real_outputs.py` assigns the code to every canonical artefact (constant `QUALIFICATION_CODES`). The judgement was made once for the artefact family and applied uniformly; it was not assessed separately for each artefact. |
| Assessed use | Downstream grid-adequacy screening that takes an artefact's peak demand as the demand for its declared future. |
| Affected fields | `peak_incremental_mw` and `p95_incremental_mw`. |
| Fields not affected | `annual_incremental_mwh`, which varies across futures (sixteen distinct levels in each pathway) because future-specific multipliers are applied to the baseline trace sum. Those constructed annual values carry a separate limitation, namely that they are not independently validated against future-specific hourly traces; this code does not record that limitation. |
| Limitation | In each pathway, the affected fields are computed from one shared hourly trace and repeated unchanged in all 21 future-indexed artefacts; their values are identical across futures to full floating-point precision. The future index of an artefact therefore implies more specificity than these two fields carry. |
| Supported interpretation | The values are pathway-level statistics of the shared hourly trace. For the future_0 artefact of each pathway they were checked directly against that trace (VAL-020, VAL-021). They may be used where a pathway-level peak or p95 is the appropriate input. |
| Unsupported interpretation | Treating the values as future-specific peak or p95 demand; inferring that peak or p95 demand differs, or does not differ, between futures; attributing differences between futures in a downstream result to variation in these fields. |
| Downstream treatment | Not prescribed. A receiving analysis that needs future-specific peak demand must supply its own treatment and state its assumption. Path B in the accompanying paper, which scales the peak by the future-specific multiplier `U_inc_mult`, is one analyst-selected sensitivity and is not a consequence of this code. The retained screening wrapper (`Process-Heat-DCM/src/gxp_downstream_qualification_consumer.py`) reads the code only to report it in its output table; neither the wrapper nor the all-42 replay uses it to select a treatment. |
| Basis for the judgement | VAL-013: the source configuration has one shared hourly trace per pathway, so a future-varying peak/p95 check is not applicable. Reproduction steps S10 and S12 confirm that peak and p95 are identical across the 21 futures of each pathway. VAL-020 and VAL-021 check the baseline values against the trace. |
| Implementation records | VAL-023 (schema change adding the field), VAL-024 (regeneration of the canonical artefacts), VAL-025 (field-by-field comparison: `qualification_codes` is the only added key) and VAL-026 (fixture re-run), in `reports/validation/`. The decision record that authorised adding the field is part of the author's private research record and is not included in this archive. |
