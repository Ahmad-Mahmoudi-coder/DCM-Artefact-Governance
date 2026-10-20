"""
Biomass Supply Screen (PoC v2 extension)

Authorised by docs/67_biomass_supply_evidence_reconciliation_and_screening_test.qmd,
Section 13 ("If ready, implement one non-mutating screen"), following the
evidence-acquisition/gate specification in docs/66 and the minimum model
specification in docs/65.

This is a POST-HOC, NON-MUTATING DIAGNOSTIC SCREEN ONLY. It is not a dispatch
constraint and is not authorised as one. It does NOT:
  - modify dispatch (site_dispatch_2020.py untouched, not imported);
  - modify grid/GXP screening (gxp_rdm_screen.py untouched, not imported);
  - modify any canonical bundle output (read-only against the canonical BB1
    dispatch summary CSV only);
  - change the production biomass price (signals_config.toml unchanged);
  - re-run dispatch, grid, or RDM;
  - regenerate win-rate/regret/satisficing (that propagation, if ever pursued,
    is a distinct future task -- see docs/67 Section 18, analogous to but not
    the same task as site_capex_impact_analysis.py's CAPEX propagation);
  - assign any probability to any supply tier or scenario.

It reads the canonical BB1 dispatch summary (annual_fuel_MWh, annual_heat_GWh,
already realised by the existing, unmodified dispatch run), and:
  1. Computes the unconditional GJ/year biomass fuel-energy requirement.
  2. Computes the conditional tonnes/year requirement (55% moisture, 7.184 GJ/t
     basis, EV-0051) -- labelled CONDITIONAL_DERIVED_REQUIREMENT throughout.
  3. Allocates that requirement against the five published Southland delivered-
     cost supply tiers (EV-0052/EV-0054), lowest-cost-first, exactly as the
     source's own MAC Optimal pathway logic does, computing the highest tier
     entered, the marginal (highest-tier) cost, and the tonnage/GJ-weighted
     average delivered cost.
  4. Compares the result against the current flat 42 NZD/MWh_fuel production
     assumption.
  5. Runs the merit-order diagnostic: compares BB1's marginal cost of heat
     (screened) against the committed EB1-3 electrode boilers' marginal cost
     of heat, using the SAME formula as site_dispatch_2020.py's
     compute_marginal_cost_heat() (fuel_price/efficiency + ets*co2/efficiency),
     reproduced here as a read-only, standalone calculation -- dispatch itself
     is not invoked or modified.

Outputs of the original docs/67 screen remain at
Output/runs/biomass_supply_screen_v1/ (frozen baseline; this script no longer
overwrites that directory). Phase 3B formalised outputs (docs/85) are written
to Output/runs/biomass_supply_screen_formalised_v1/, never inside the canonical
dispatch/RDM bundle directory. Numerical calculation functions are unchanged
from the docs/67 screen; only assembly, provenance annotation, and the write
target are extended.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from src.path_utils import resolve_path, input_root


CANONICAL_BUNDLE = 'dispatch_optimal_subset_canonical_continuous_v1'
EPOCH_BB = '2035_BB'
OUTPUT_BUNDLE_NAME = 'biomass_supply_screen_v1'
FORMALISED_BUNDLE_NAME = 'biomass_supply_screen_formalised_v1'
BUNDLE_VERSION = 'biomass_supply_screen_formalised_v1'
GEOGRAPHIC_BOUNDARY_LABEL = 'Southland-only'
AUTHORISING_DOCUMENT = (
    'docs/85_phase3b_biomass_supply_representation_formalisation_authorisation.qmd'
)
SCRIPT_IDENTITY = 'Process-Heat-DCM/src/biomass_supply_screen.py'
MODULE_VERSION = 'UNAVAILABLE_no_independent_module_version'

# Provenance identifiers copied from existing registers (not invented):
# references/evidence_register.csv, references/source_register.csv,
# inputs/model_input_register.csv.
# Release staging edit: the context-only broader regional estimate (EV-0056 / INP-0028) and
# its third-party source ID were removed; that figure was not used in any calculation.
EVIDENCE_IDS = [
    'EV-0050',
    'EV-0051',
    'EV-0052',
    'EV-0053',
    'EV-0054',
    'EV-0055',
]
SOURCE_IDS = [
    'SRC-NZ-EECA-RETASOUTHLANDPHASE1-2022',
    'SRC-NZ-EECA-RETASOUTHISLANDPHASE1-2024',
]
MODEL_INPUT_IDS = [
    'INP-0020',
    'INP-0021',
    'INP-0022',
    'INP-0023',
    'INP-0024',
    'INP-0025',
    'INP-0026',
    'INP-0027',
]
SOURCE_VINTAGE_NOTE = (
    'EECA Southland RETA Phase One Report dated 2022-10 '
    '(SRC-NZ-EECA-RETASOUTHLANDPHASE1-2022); EV-0052 delivered-cost tiers use '
    'PF Olsen analysis of AgriHQ Forestry Log Price Report (Southern South Island '
    '3-year average prices to September 2021).'
)
ACCESSIBILITY_RADIUS_NOTE = (
    '100 km is an Edendale accessibility/eligibility radius (SM-5.3-A; '
    'docs/01a_boundary_register.csv row 5). It is a scoping statement, not a '
    'cost-calculation input, and is not used computationally by this screen '
    '(docs/84 Section 3; docs/85 Section 4).'
)
ILLUSTRATIVE_TRANSPORT_DISTANCE_NOTE = (
    '60 km is the illustrative transport-distance assumption embedded in '
    'EV-0052 published delivered-cost tiers (within EV-0052 stated 30-120 km '
    'transport-component range). Phase 3B does not rewrite or replace those '
    'published tier costs with a transport model (docs/85 Section 4).'
)
DELIVERED_COST_DISTANCE_QUALIFICATION = (
    'The delivered-cost figures the screen produces are only demonstrated to '
    'be internally consistent for biomass sourced within an illustrative ~60 km '
    'radius; the wider ~100 km accessibility framing used elsewhere in the '
    'project is not shown to carry the same cost basis, and any future extension '
    'that treats the full 100 km radius as cost-equivalent to the 60 km-based '
    'tiers would need this reconciled first, not assumed. The full relationship '
    'between the 100 km eligible pool and the 60 km cost basis has not been '
    'independently reconciled because the underlying PF Olsen/Ahika primary '
    'reports are not held (docs/84 Section 3; docs/85 Section 4).'
)
REGIONAL_RESOURCE_QUANTITY_CHARACTER = (
    'STATIC_EXTERNALLY_SOURCED_MULTI_YEAR_AVERAGE_not_computed_or_rederived'
)
PF_OLSEN_AHIKA_PRIMARY_REPORTS_HELD = 'NOT_HELD'

NUMERICAL_SUMMARY_FIELDS = [
    'canonical_bb1_annual_heat_GWh',
    'canonical_bb1_annual_fuel_MWh',
    'canonical_bb1_annual_fuel_GJ',
    'requirement_classification',
    'conditional_tonnes_per_year',
    'moisture_fraction_basis',
    'ncv_gj_per_tonne_basis',
    'regional_pool_total_tonnes_per_year',
    'regional_pool_total_tj_per_year',
    'bb1_share_of_regional_pool_energy_basis_pct',
    'bb1_share_of_regional_pool_mass_basis_pct',
    'highest_supply_tier_entered',
    'reached_unresolved_tier_5',
    'unmet_gj_after_all_tiers',
    'weighted_delivered_cost_nzd_per_gj_low',
    'weighted_delivered_cost_nzd_per_gj_mid',
    'weighted_delivered_cost_nzd_per_gj_high',
    'weighted_delivered_cost_nzd_per_mwh_fuel_low',
    'weighted_delivered_cost_nzd_per_mwh_fuel_mid',
    'weighted_delivered_cost_nzd_per_mwh_fuel_high',
    'current_flat_cost_nzd_per_mwh_fuel',
    'difference_from_flat_nzd_per_mwh_fuel_mid',
    'current_annual_biomass_fuel_cost_nzd',
    'screened_annual_biomass_fuel_cost_nzd_low',
    'screened_annual_biomass_fuel_cost_nzd_mid',
    'screened_annual_biomass_fuel_cost_nzd_high',
    'annual_cost_difference_nzd_mid',
    'physical_limit_binding_indicator',
    'mc_heat_EB_nzd_per_mwh_heat',
    'mc_heat_BB1_current_flat_nzd_per_mwh_heat',
    'mc_heat_BB1_screened_weighted_mid_nzd_per_mwh_heat',
    'mc_heat_BB1_screened_marginal_high_nzd_per_mwh_heat',
    'merit_order_intact_at_weighted_mid',
    'merit_order_intact_at_marginal_high',
    'crossover_biomass_price_nzd_per_mwh_fuel',
    'crossover_biomass_price_nzd_per_gj',
    'comparison_relevance_indicator',
]


def _portable(path) -> str:
    """Release staging edit: path relative to the workspace root (parent of Process-Heat-DCM), '/'-separated."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT.parent).as_posix()
    except ValueError:
        return resolved.name


def load_screen_assumptions(config_path: Path = None) -> dict:
    if config_path is None:
        config_path = Path(input_root()) / 'configs' / 'biomass_supply_screen_assumptions.toml'
    if not config_path.exists():
        raise FileNotFoundError(f"Biomass supply screen assumptions config not found: {config_path}")
    with open(config_path, 'rb') as f:
        return tomllib.load(f)


def load_canonical_bb1_requirement() -> dict:
    """
    Read-only: reproduces the canonical BB1 fuel-energy requirement directly
    from the existing, unmodified canonical dispatch bundle. Does not run
    dispatch. Raises if the canonical bundle is not present -- this script
    never fabricates a substitute value.
    """
    output_root = Path(resolve_path('Output'))
    summary_path = (
        output_root / 'runs' / CANONICAL_BUNDLE / f'epoch{EPOCH_BB}' / 'dispatch'
        / 'optimal_subset_run' / f'site_dispatch_{EPOCH_BB}_summary_opt.csv'
    )
    if not summary_path.exists():
        raise FileNotFoundError(
            f"Canonical BB1 dispatch summary not found at {summary_path}. "
            f"This script reads existing dispatch output only; it does not run dispatch."
        )
    df = pd.read_csv(summary_path)
    bb1_row = df[df['unit_id'] == 'BB1']
    if bb1_row.empty:
        raise ValueError(f"No BB1 row found in {summary_path}")
    bb1_row = bb1_row.iloc[0]
    return {
        'annual_heat_GWh': float(bb1_row['annual_heat_GWh']),
        'annual_fuel_MWh': float(bb1_row['annual_fuel_MWh']),
        'annual_fuel_cost_nzd': float(bb1_row['annual_fuel_cost_nzd']),
        'source_path': _portable(summary_path),
    }


def compute_requirement(canonical: dict, basis: dict) -> dict:
    annual_fuel_mwh = canonical['annual_fuel_MWh']
    gj_per_mwh = basis['gj_per_mwh']
    annual_fuel_gj = annual_fuel_mwh * gj_per_mwh  # unconditional unit conversion

    ncv = basis['ncv_gj_per_tonne']
    moisture = basis['moisture_fraction']
    conditional_tonnes = annual_fuel_gj / ncv  # CONDITIONAL_DERIVED_REQUIREMENT

    return {
        'annual_heat_GWh': canonical['annual_heat_GWh'],
        'annual_fuel_MWh': annual_fuel_mwh,
        'annual_fuel_GJ': annual_fuel_gj,
        'moisture_fraction_basis': moisture,
        'ncv_gj_per_tonne_basis': ncv,
        'conditional_tonnes_per_year': conditional_tonnes,
        'requirement_classification': 'CONDITIONAL_DERIVED_REQUIREMENT',
    }


def allocate_to_tiers(requirement_gj: float, tiers: list) -> dict:
    """
    Lowest-cost-first allocation of the BB1 GJ requirement across the published
    supply tiers, consistent with the source's own MAC Optimal merit-order logic
    (EECA RETA Section 7.8-7.9). Tier 5 (pruned sawlogs) has an UNRESOLVED
    quantity and is treated as an unbounded tail only if reached -- it is NOT
    included in the regional-pool total and is flagged, not silently used,
    if the allocation reaches it.
    """
    # Sort tiers by low-end cost ascending (merit order)
    numeric_tiers = [t for t in tiers if isinstance(t.get('tj_per_year'), (int, float))]
    unresolved_tiers = [t for t in tiers if not isinstance(t.get('tj_per_year'), (int, float))]
    numeric_tiers = sorted(numeric_tiers, key=lambda t: t['cost_nzd_per_gj_low'])

    remaining_gj = requirement_gj
    allocation = []
    highest_tier_entered = None
    reached_unresolved_tier = False

    for tier in numeric_tiers:
        tier_gj = tier['tj_per_year'] * 1000.0  # TJ -> GJ
        if remaining_gj <= 0:
            break
        draw_gj = min(remaining_gj, tier_gj)
        if draw_gj > 0:
            allocation.append({
                'tier_id': tier['tier_id'],
                'label': tier['label'],
                'tier_capacity_gj': tier_gj,
                'drawn_gj': draw_gj,
                'cost_nzd_per_gj_low': tier['cost_nzd_per_gj_low'],
                'cost_nzd_per_gj_high': tier['cost_nzd_per_gj_high'],
                'fully_drawn': draw_gj >= tier_gj,
            })
            highest_tier_entered = tier['tier_id']
        remaining_gj -= draw_gj

    if remaining_gj > 1e-6 and unresolved_tiers:
        reached_unresolved_tier = True
        tier = unresolved_tiers[0]
        allocation.append({
            'tier_id': tier['tier_id'],
            'label': tier['label'] + ' [QUANTITY UNRESOLVED -- flagged, not fabricated]',
            'tier_capacity_gj': None,
            'drawn_gj': remaining_gj,
            'cost_nzd_per_gj_low': tier['cost_nzd_per_gj_low'],
            'cost_nzd_per_gj_high': tier['cost_nzd_per_gj_high'],
            'fully_drawn': None,
        })
        highest_tier_entered = tier['tier_id']
        remaining_gj = 0.0

    unmet_gj = max(remaining_gj, 0.0)

    # Weighted cost (low/mid/high)
    def weighted_total(cost_key):
        total = 0.0
        for a in allocation:
            total += a['drawn_gj'] * a[cost_key]
        return total

    total_drawn_gj = sum(a['drawn_gj'] for a in allocation)
    total_cost_low = weighted_total('cost_nzd_per_gj_low')
    total_cost_high = weighted_total('cost_nzd_per_gj_high')
    total_cost_mid = (total_cost_low + total_cost_high) / 2.0

    weighted_avg_low = total_cost_low / total_drawn_gj if total_drawn_gj else 0.0
    weighted_avg_high = total_cost_high / total_drawn_gj if total_drawn_gj else 0.0
    weighted_avg_mid = total_cost_mid / total_drawn_gj if total_drawn_gj else 0.0

    marginal_tier = allocation[-1] if allocation else None
    marginal_cost_low = marginal_tier['cost_nzd_per_gj_low'] if marginal_tier else None
    marginal_cost_high = marginal_tier['cost_nzd_per_gj_high'] if marginal_tier else None

    return {
        'allocation': allocation,
        'highest_tier_entered': highest_tier_entered,
        'reached_unresolved_tier': reached_unresolved_tier,
        'unmet_gj': unmet_gj,
        'total_drawn_gj': total_drawn_gj,
        'weighted_avg_cost_nzd_per_gj_low': weighted_avg_low,
        'weighted_avg_cost_nzd_per_gj_mid': weighted_avg_mid,
        'weighted_avg_cost_nzd_per_gj_high': weighted_avg_high,
        'marginal_cost_nzd_per_gj_low': marginal_cost_low,
        'marginal_cost_nzd_per_gj_high': marginal_cost_high,
        'total_cost_nzd_low': total_cost_low,
        'total_cost_nzd_mid': total_cost_mid,
        'total_cost_nzd_high': total_cost_high,
    }


def merit_order_diagnostic(gj_per_mwh: float, screen_cfg: dict, allocation_result: dict) -> dict:
    """
    Read-only reproduction of compute_marginal_cost_heat()'s formula from
    site_dispatch_2020.py, applied to (a) the current flat biomass price,
    (b) the screened weighted-average biomass price, and (c) the screened
    marginal (highest-tier) biomass price -- compared against EB1-3's
    marginal cost of heat under current signals. Dispatch itself is not
    invoked; this is a standalone, parallel calculation for diagnostic
    purposes only, per docs/67 Section 22 ("without modifying dispatch").
    """
    m = screen_cfg['merit_order_diagnostic_inputs']
    comp = screen_cfg['current_production_comparator']

    def mc_heat_biomass(price_nzd_per_mwh_fuel):
        return (price_nzd_per_mwh_fuel / m['bb1_efficiency_th']
                + (m['ets_price_nzd_per_tco2'] * m['bb1_co2_factor_t_per_mwh_fuel']) / m['bb1_efficiency_th'])

    def mc_heat_eb():
        return (m['elec_price_flat_nzd_per_mwh'] / m['eb_efficiency_th']
                + (m['ets_price_nzd_per_tco2'] * m['eb_co2_factor_t_per_mwh_fuel']) / m['eb_efficiency_th'])

    flat_price_mwh = comp['flat_price_nzd_per_mwh_fuel']
    weighted_mid_mwh = allocation_result['weighted_avg_cost_nzd_per_gj_mid'] * gj_per_mwh
    weighted_low_mwh = allocation_result['weighted_avg_cost_nzd_per_gj_low'] * gj_per_mwh
    weighted_high_mwh = allocation_result['weighted_avg_cost_nzd_per_gj_high'] * gj_per_mwh
    marginal_low_mwh = (allocation_result['marginal_cost_nzd_per_gj_low'] or 0.0) * gj_per_mwh
    marginal_high_mwh = (allocation_result['marginal_cost_nzd_per_gj_high'] or 0.0) * gj_per_mwh

    mc_eb = mc_heat_eb()
    mc_bb_flat = mc_heat_biomass(flat_price_mwh)
    mc_bb_weighted_mid = mc_heat_biomass(weighted_mid_mwh)
    mc_bb_weighted_low = mc_heat_biomass(weighted_low_mwh)
    mc_bb_weighted_high = mc_heat_biomass(weighted_high_mwh)
    mc_bb_marginal_low = mc_heat_biomass(marginal_low_mwh)
    mc_bb_marginal_high = mc_heat_biomass(marginal_high_mwh)

    # Crossover biomass fuel price (NZD/MWh_fuel) at which mc_bb == mc_eb
    crossover_price_nzd_per_mwh_fuel = (mc_eb) * m['bb1_efficiency_th'] - (
        m['ets_price_nzd_per_tco2'] * m['bb1_co2_factor_t_per_mwh_fuel']
    )
    crossover_price_nzd_per_gj = crossover_price_nzd_per_mwh_fuel / gj_per_mwh

    return {
        'mc_heat_EB_nzd_per_mwh_heat': mc_eb,
        'mc_heat_BB1_current_flat_nzd_per_mwh_heat': mc_bb_flat,
        'mc_heat_BB1_screened_weighted_mid_nzd_per_mwh_heat': mc_bb_weighted_mid,
        'mc_heat_BB1_screened_weighted_low_nzd_per_mwh_heat': mc_bb_weighted_low,
        'mc_heat_BB1_screened_weighted_high_nzd_per_mwh_heat': mc_bb_weighted_high,
        'mc_heat_BB1_screened_marginal_low_nzd_per_mwh_heat': mc_bb_marginal_low,
        'mc_heat_BB1_screened_marginal_high_nzd_per_mwh_heat': mc_bb_marginal_high,
        'merit_order_intact_at_weighted_mid': bool(mc_bb_weighted_mid < mc_eb),
        'merit_order_intact_at_marginal_high': bool(mc_bb_marginal_high < mc_eb),
        'crossover_biomass_price_nzd_per_mwh_fuel': crossover_price_nzd_per_mwh_fuel,
        'crossover_biomass_price_nzd_per_gj': crossover_price_nzd_per_gj,
    }


def assemble_numerical_summary(
    canonical: dict,
    requirement: dict,
    pool: dict,
    allocation_result: dict,
    basis: dict,
    comp: dict,
    diag: dict,
) -> dict:
    """Assemble the original docs/67 numerical summary fields. Formulas are
    unchanged from the previous main() write step; this only names that step.
    """
    share_of_pool_energy_pct = (requirement['annual_fuel_GJ'] / (pool['total_tj_per_year'] * 1000.0)) * 100.0
    share_of_pool_mass_pct = (requirement['conditional_tonnes_per_year'] / pool['total_tonnes_per_year']) * 100.0

    weighted_mwh_mid = allocation_result['weighted_avg_cost_nzd_per_gj_mid'] * basis['gj_per_mwh']
    weighted_mwh_low = allocation_result['weighted_avg_cost_nzd_per_gj_low'] * basis['gj_per_mwh']
    weighted_mwh_high = allocation_result['weighted_avg_cost_nzd_per_gj_high'] * basis['gj_per_mwh']

    current_annual_fuel_cost_nzd = canonical['annual_fuel_cost_nzd']
    screened_annual_fuel_cost_nzd_mid = allocation_result['total_cost_nzd_mid']
    screened_annual_fuel_cost_nzd_low = allocation_result['total_cost_nzd_low']
    screened_annual_fuel_cost_nzd_high = allocation_result['total_cost_nzd_high']

    physical_limit_binding = allocation_result['reached_unresolved_tier'] or allocation_result['unmet_gj'] > 0

    return {
        'canonical_bb1_annual_heat_GWh': requirement['annual_heat_GWh'],
        'canonical_bb1_annual_fuel_MWh': requirement['annual_fuel_MWh'],
        'canonical_bb1_annual_fuel_GJ': requirement['annual_fuel_GJ'],
        'requirement_classification': requirement['requirement_classification'],
        'conditional_tonnes_per_year': requirement['conditional_tonnes_per_year'],
        'moisture_fraction_basis': requirement['moisture_fraction_basis'],
        'ncv_gj_per_tonne_basis': requirement['ncv_gj_per_tonne_basis'],
        'regional_pool_total_tonnes_per_year': pool['total_tonnes_per_year'],
        'regional_pool_total_tj_per_year': pool['total_tj_per_year'],
        'bb1_share_of_regional_pool_energy_basis_pct': share_of_pool_energy_pct,
        'bb1_share_of_regional_pool_mass_basis_pct': share_of_pool_mass_pct,
        'highest_supply_tier_entered': allocation_result['highest_tier_entered'],
        'reached_unresolved_tier_5': allocation_result['reached_unresolved_tier'],
        'unmet_gj_after_all_tiers': allocation_result['unmet_gj'],
        'weighted_delivered_cost_nzd_per_gj_low': allocation_result['weighted_avg_cost_nzd_per_gj_low'],
        'weighted_delivered_cost_nzd_per_gj_mid': allocation_result['weighted_avg_cost_nzd_per_gj_mid'],
        'weighted_delivered_cost_nzd_per_gj_high': allocation_result['weighted_avg_cost_nzd_per_gj_high'],
        'weighted_delivered_cost_nzd_per_mwh_fuel_low': weighted_mwh_low,
        'weighted_delivered_cost_nzd_per_mwh_fuel_mid': weighted_mwh_mid,
        'weighted_delivered_cost_nzd_per_mwh_fuel_high': weighted_mwh_high,
        'current_flat_cost_nzd_per_mwh_fuel': comp['flat_price_nzd_per_mwh_fuel'],
        'difference_from_flat_nzd_per_mwh_fuel_mid': weighted_mwh_mid - comp['flat_price_nzd_per_mwh_fuel'],
        'current_annual_biomass_fuel_cost_nzd': current_annual_fuel_cost_nzd,
        'screened_annual_biomass_fuel_cost_nzd_low': screened_annual_fuel_cost_nzd_low,
        'screened_annual_biomass_fuel_cost_nzd_mid': screened_annual_fuel_cost_nzd_mid,
        'screened_annual_biomass_fuel_cost_nzd_high': screened_annual_fuel_cost_nzd_high,
        'annual_cost_difference_nzd_mid': screened_annual_fuel_cost_nzd_mid - current_annual_fuel_cost_nzd,
        'physical_limit_binding_indicator': physical_limit_binding,
        'mc_heat_EB_nzd_per_mwh_heat': diag['mc_heat_EB_nzd_per_mwh_heat'],
        'mc_heat_BB1_current_flat_nzd_per_mwh_heat': diag['mc_heat_BB1_current_flat_nzd_per_mwh_heat'],
        'mc_heat_BB1_screened_weighted_mid_nzd_per_mwh_heat': diag['mc_heat_BB1_screened_weighted_mid_nzd_per_mwh_heat'],
        'mc_heat_BB1_screened_marginal_high_nzd_per_mwh_heat': diag['mc_heat_BB1_screened_marginal_high_nzd_per_mwh_heat'],
        'merit_order_intact_at_weighted_mid': diag['merit_order_intact_at_weighted_mid'],
        'merit_order_intact_at_marginal_high': diag['merit_order_intact_at_marginal_high'],
        'crossover_biomass_price_nzd_per_mwh_fuel': diag['crossover_biomass_price_nzd_per_mwh_fuel'],
        'crossover_biomass_price_nzd_per_gj': diag['crossover_biomass_price_nzd_per_gj'],
        'comparison_relevance_indicator': (
            'PLAUSIBLE_MAGNITUDE_COMPARABLE_TO_CAPEX_EFFECT_NOT_QUANTIFIED_THROUGH_ROBUSTNESS_METRICS_IN_THIS_TASK'
        ),
        'canonical_source_path': canonical['source_path'],
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble_formalised_summary(
    numerical: dict,
    assumptions_path: Path,
    assumptions_sha256: str,
    price_basis: dict,
) -> dict:
    record = {
        'output_bundle_version': BUNDLE_VERSION,
        'output_run_id': FORMALISED_BUNDLE_NAME,
        'geographic_boundary': GEOGRAPHIC_BOUNDARY_LABEL,
        'canonical_source_bundle': CANONICAL_BUNDLE,
        'canonical_bb1_source_path': numerical['canonical_source_path'],
        'assumptions_toml_path': _portable(assumptions_path),
        'assumptions_toml_sha256': assumptions_sha256,
        'authorising_document': AUTHORISING_DOCUMENT,
        'script_identity': SCRIPT_IDENTITY,
        'module_version': MODULE_VERSION,
        'evidence_ids': ';'.join(EVIDENCE_IDS),
        'source_ids': ';'.join(SOURCE_IDS),
        'model_input_ids': ';'.join(MODEL_INPUT_IDS),
        'source_vintage_note': SOURCE_VINTAGE_NOTE,
        'price_basis_status': price_basis.get('status', 'UNAVAILABLE'),
        'price_basis_note': price_basis.get('note', 'UNAVAILABLE'),
        'accessibility_radius_note': ACCESSIBILITY_RADIUS_NOTE,
        'illustrative_transport_distance_note': ILLUSTRATIVE_TRANSPORT_DISTANCE_NOTE,
        'delivered_cost_distance_qualification': DELIVERED_COST_DISTANCE_QUALIFICATION,
        'regional_resource_quantity_character': REGIONAL_RESOURCE_QUANTITY_CHARACTER,
        'pf_olsen_ahika_primary_reports_held': PF_OLSEN_AHIKA_PRIMARY_REPORTS_HELD,
    }
    record.update(numerical)
    return record


def write_formalised_bundle(
    out_dir: Path,
    formalised_summary: dict,
    allocation_result: dict,
    assumptions_path: Path,
    assumptions_sha256: str,
    created_utc: str,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    allocation_path = out_dir / 'biomass_supply_tier_allocation.csv'
    summary_path = out_dir / 'biomass_supply_screen_summary.csv'
    manifest_path = out_dir / 'manifest.json'

    allocation_df = pd.DataFrame(allocation_result['allocation'])
    summary_df = pd.DataFrame([formalised_summary])
    allocation_df.to_csv(allocation_path, index=False, lineterminator='\n')
    summary_df.to_csv(summary_path, index=False, lineterminator='\n')

    manifest = {
        'bundle_version': BUNDLE_VERSION,
        'output_run_id': FORMALISED_BUNDLE_NAME,
        'created_utc': created_utc,
        'authorising_document': AUTHORISING_DOCUMENT,
        'script_identity': SCRIPT_IDENTITY,
        'module_version': MODULE_VERSION,
        'geographic_boundary': GEOGRAPHIC_BOUNDARY_LABEL,
        'canonical_upstream_dispatch_bundle': CANONICAL_BUNDLE,
        'canonical_bb1_summary_input_path': formalised_summary['canonical_bb1_source_path'],
        'assumptions_toml_path': _portable(assumptions_path),
        'assumptions_toml_sha256': assumptions_sha256,
        'evidence_ids': list(EVIDENCE_IDS),
        'source_ids': list(SOURCE_IDS),
        'model_input_ids': list(MODEL_INPUT_IDS),
        'source_vintage_note': SOURCE_VINTAGE_NOTE,
        'legacy_baseline_bundle': OUTPUT_BUNDLE_NAME,
        'legacy_baseline_bundle_not_modified_by_this_write': True,
        'output_files': [
            'biomass_supply_screen_summary.csv',
            'biomass_supply_tier_allocation.csv',
            'manifest.json',
        ],
        'output_file_sha256': {
            'biomass_supply_screen_summary.csv': sha256_file(summary_path),
            'biomass_supply_tier_allocation.csv': sha256_file(allocation_path),
        },
        'note_schema': (
            'Standalone provenance sidecar for the formalised biomass supply '
            'screen. Not a BiomassSupplyPack JSON Schema. No schema file is '
            'created by Phase 3B (docs/85 Section 8). SHA-256 is recorded for '
            'the two numerical CSVs; this manifest is excluded from its own '
            'hash set because it contains a creation timestamp.'
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return {
        'out_dir': out_dir,
        'allocation_path': allocation_path,
        'summary_path': summary_path,
        'manifest_path': manifest_path,
        'manifest': manifest,
    }


def main():
    assumptions_path = Path(input_root()) / 'configs' / 'biomass_supply_screen_assumptions.toml'
    screen_cfg = load_screen_assumptions(assumptions_path)
    basis = screen_cfg['moisture_and_energy_basis']
    pool = screen_cfg['regional_pool_near_term']
    tiers = screen_cfg['supply_tiers']
    comp = screen_cfg['current_production_comparator']
    price_basis = screen_cfg.get('price_basis', {})

    canonical = load_canonical_bb1_requirement()
    requirement = compute_requirement(canonical, basis)
    allocation_result = allocate_to_tiers(requirement['annual_fuel_GJ'], tiers)
    diag = merit_order_diagnostic(basis['gj_per_mwh'], screen_cfg, allocation_result)

    numerical = assemble_numerical_summary(
        canonical, requirement, pool, allocation_result, basis, comp, diag,
    )
    assumptions_sha256 = sha256_file(assumptions_path)
    formalised_summary = assemble_formalised_summary(
        numerical, assumptions_path, assumptions_sha256, price_basis,
    )

    output_root = Path(resolve_path('Output'))
    out_dir = output_root / 'runs' / FORMALISED_BUNDLE_NAME
    created_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    written = write_formalised_bundle(
        out_dir,
        formalised_summary,
        allocation_result,
        assumptions_path,
        assumptions_sha256,
        created_utc,
    )

    print(f"[OK] Wrote tier allocation: {written['allocation_path']}")
    print(f"[OK] Wrote formalised summary: {written['summary_path']}")
    print(f"[OK] Wrote manifest: {written['manifest_path']}")
    print(f"[INFO] Source (read-only, unmodified): {canonical['source_path']}")
    print(f"[INFO] Assumptions SHA-256: {assumptions_sha256}")
    print(f"[INFO] Geographic boundary: {GEOGRAPHIC_BOUNDARY_LABEL}")
    print(f"[INFO] Highest supply tier entered: {allocation_result['highest_tier_entered']}")
    print(f"[INFO] Merit order intact at weighted-mid cost: {diag['merit_order_intact_at_weighted_mid']}")
    print(f"[INFO] Merit order intact at marginal-high cost: {diag['merit_order_intact_at_marginal_high']}")
    print(f"[INFO] Legacy baseline bundle not written: {OUTPUT_BUNDLE_NAME}")


if __name__ == '__main__':
    main()
