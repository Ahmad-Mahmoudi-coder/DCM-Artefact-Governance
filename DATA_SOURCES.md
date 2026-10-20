# Data sources and attribution

No copy of any source report is included in this package. Values and method descriptions taken
from published reports are reproduced, with attribution, in the files listed below. Page numbers
are PDF page numbers of the copies used in the study; they coincide with the printed page numbers.

## 1. Energy Efficiency and Conservation Authority (EECA), 2022

EECA (2022). *Regional Energy Transition Accelerator (RETA): Southland – Phase One Report*.
Energy Efficiency and Conservation Authority, October 2022.
<https://www.eeca.govt.nz/assets/EECA-Southland-RETA-Report.pdf>
(SHA-256 of the copy used in the study: `993bc56556a56f7d6d23fe16291f833c4730166e1b07b295d2981cd9d5e97f9c`.
The URL was located on 12 October 2026; the copy behind it was not hash-checked.)

| Values or text reproduced | Location in report | Files in this package |
|---|---|---|
| Electricity connection options for Fonterra Edendale: additional 21 MW (N), 32 MW (N-1) and 97 MW (N), with their estimated capital costs | Connection-options table, p. 74 | `Process-Heat-DCM/Input/configs/grid_upgrades_southland_edendale.toml` (options 1–3). Restated in results derived from the menu: `Process-Heat-DCM/Output/runs/gxp_downstream_qualification_consumer_v1/`, `Process-Heat-DCM/Output/runs/dispatch_optimal_subset_canonical_continuous_v1/rdm/rdm_summary_2035_{EB,BB}.csv`, `figures/published/fig2_screening_sensitivity_2035EB_future5.*` (tier capacities; costs are not plotted), `figures/published/fig03_*`, `figures/expected/paper_reported_screening_values.json`, `reports/validation/validation_summary.v0.2.public_extract.csv` (VAL-032, VAL-051) |
| Near-term accessible woody biomass: total (380,500 t/yr; 2,738 TJ) and four categories, in tonnes and TJ | §7.6, p. 53 | `Process-Heat-DCM/Input/configs/biomass_supply_screen_assumptions.toml`; BSP outputs (below); VAL-046 in the validation extract |
| 55 % moisture content and net calorific value of 7.184 GJ/t | footnote 47, p. 53; footnote 51, p. 56 | assumptions file; `Process-Heat-DCM/src/biomass_supply_screen.py` (module docstring); BSP outputs |
| Delivered biomass costs by source category, in $/t and $/GJ | Table 2, p. 56, credited in the report to "PF Olsen, Ahikā" | assumptions file; BSP outputs |
| Cost-assessment method: PF Olsen analysis of the AgriHQ Forestry Log Price Report (Southern South Island 3-year average prices to September 2021); Ahikā cost analysis for processor residues; Scion, University of Canterbury and PF Olsen consultation for in-forest residues | §7.7, p. 55 | `[price_basis]` note in the assumptions file; `SOURCE_VINTAGE_NOTE` and the delivered-cost note in `biomass_supply_screen.py`; `source_vintage_note` and `price_basis_note` in the formalised summary; `evidence_source_vintage` in the BSP instance and fixtures |
| Transport-cost distances: illustrative 60 km between a central chipping site and the user's site, within a stated range of 30 km to 120 km | §7.7, p. 55 | 60 km: `transport_cost_distance_basis` in the BSP producer (`biomass_supply_pack_producer.py`), instance and fixtures; the BSP schema description; the distance check message in `validate_biomass_supply_pack.py`; notes in `biomass_supply_screen.py` and the formalised summary. 30–120 km: notes in `biomass_supply_screen.py` and the formalised summary |
| Competing-demand structure (qualitative) | §§7.8–7.9, pp. 59–62 | descriptive notes in the assumptions file and BSP outputs |

BSP outputs carrying these values: `Process-Heat-DCM/Output/runs/biomass_supply_screen_formalised_v1/`,
`Process-Heat-DCM/Output/runs/biomass_supply_pack_v1/`, `schemas/examples/biomass_supply_pack.*.json`,
and VAL-044 to VAL-049 in the validation extract.

Locator note: comments in `biomass_supply_screen_assumptions.toml` cite footnote 51 and Table 2
on p. 55; both are on p. 56. That file is not edited, because its SHA-256 is part of the
BiomassSupplyPack identity.

## 2. EECA, 2024

EECA (2024). *Regional Energy Transition Accelerator (RETA): South Island – Phase One Report*.
<https://www.eeca.govt.nz/assets/EECA-Resources/Co-funding/RETA-South-Island-Phase-One-Report.pdf>
(URL located on 12 October 2026; not hash-checked against the study copy, SHA-256
`706b04a88358a4a9f9741a44a4c0e3300d9966b7c9eaffe605713c4efe3f1411`).
Cited qualitatively only (evidence record EV-0053, inter-regional biomass trade). No numerical value is reproduced.

## 3. Upstream context, not reproduced in this package

The hourly incremental-electricity traces are outputs of the project's process-heat dispatch
model. The model is driven by a synthetic heat-demand profile anchored to an annual heat figure
from EECA's Regional Heat Demand Database (RHDD;
<https://www.eeca.govt.nz/insights/data-tools/regional-heat-demand-database/>). Neither the model
nor its inputs are included.

## 4. Project-defined values (no external source)

- **150 MW upgrade option (option 4) and its capital cost of NZ$75.0 million.** These are an
  illustrative screening assumption introduced for the proof of concept. The derivation of the
  cost is not documented in the project record; it is not an official or engineering estimate. A
  comment previously in the menu file cited a per-MW rate based on option 3, but that rate does
  not reproduce NZ$75.0 million, so the comment was replaced for this release. The value itself
  is unchanged. The option's capacity determines the tier selections reported in the paper; its
  cost appears only in Section 5.2 and Figure 2 (manuscript Version 9; Figure 3 in Version 8).
- **`[assumptions]` in the grid-upgrade menu.** The real discount rate, asset life and consents
  uplift are project screening assumptions.
- **Synthetic headroom.** A 50 MW base multiplied by `U_headroom_mult` (in `gxp_rdm_screen.py`
  and the downstream consumer).
- **100 km accessibility (eligibility) radius.** A project scoping definition for Edendale, not a
  cost input and not taken from the EECA report. It appears in `accessibility_radius` (BSP
  producer, instance and fixtures), the BSP schema description, the validator's distance check
  and the notes in `biomass_supply_screen.py`.
- **Future-specific multipliers.** `futures.csv`, inherited from the project's release02 ensemble.
- **Comparator settings.** The values in `[current_production_comparator]` and
  `[merit_order_diagnostic_inputs]` of the biomass assumptions file (flat biomass and electricity
  prices, efficiencies) are the project's production-model settings.

All other data in the package (IEP artefacts, traces, registries, fixtures, validation records,
figures) are project-generated.

## 5. Rights status of third-party values

- **What is reproduced.** Individual numerical values from EECA (2022), listed in section 1, and
  short descriptions of how they were derived. The descriptions are written for this project, except
  for one acknowledged sentence quoted in `biomass_supply_screen_assumptions.toml`. No table, figure
  or photograph of the report is reproduced, and the report itself is not included.
  `EECA_CONTENT_INVENTORY.csv` lists every file that states, restates or derives
  from these values.
- **Terms found (checked 20 October 2026).**
  - The 112-page report (copy used in the study, SHA-256 above) contains no copyright, licence or
    reuse statement.
  - The EECA website footer reads "©2026 - EECA | All rights reserved".
  - EECA publishes its separate RETA dashboard (North Island regions) under Creative Commons
    Attribution 4.0. That licence does not extend to the Southland report.
  - A companion RETA Southland network study (*Spare Capacity and Load Characteristics*) states that
    its connection capital-cost estimates are "preliminary and are only suitable for screening
    purposes".
- **Third parties.** The report credits the delivered-cost values to PF Olsen and Ahikā and the
  resource estimates to Ahikā and PF Olsen.
- **Consequence for this package.** The EECA-derived values are third-party material. They are
  included with attribution, are **not covered by any licence applied to this package**, and remain
  subject to the source's terms. Reusers should cite EECA (2022).
