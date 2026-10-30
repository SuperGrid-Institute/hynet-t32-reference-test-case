# Changelog

All result-affecting changes to the test case are listed here. Versions follow
[Semantic Versioning](https://semver.org/) applied to the test case: MAJOR for
breaking changes to ids, layout or CSV schema, MINOR for a new variant, case,
scenario or file, PATCH for corrected values.

## [0.2.0] - 2026-10-30

### Added

- Project skeleton, licences (MIT for code, CC-BY-4.0 for data and documentation)
  and citation metadata.
- `tx-full` source models from UCY (XIIDM, CGMES, PowerFactory) with their
  provenance and checksums.
- Scenario inputs for S1 (`baseline`), S2 (`high_res_low_demand`) and S3
  (`low_res_high_demand`): generator dispatch, loads, HVDC set points and generator
  metadata. Timestamps are UTC. S3 loads are the baseline loads × 1.08 on active and
  × 1.50 on reactive power, so that S3 shows a voltage drop as well as thermal stress.
  In S1, RES run at 50 % of nominal power and the rest is dispatched in merit order
  within each AC island (IEEE 39, IEEE 14), accounting for the HVDC transfer, as in
  S2 and S3.
- Scenario presentation (`docs/scenarios_presentation.pptx`): tools, shipped
  formats, generator metadata and, for S1–S3, how each scenario is built and the
  results of its validation load flow.
- `hynet-testcase build` command, generating `testcase/tx-full/`: the base network
  and one solved snapshot per scenario in XIIDM and CGMES 2.4.15 (with an IIDM →
  CGMES id mapping), UCY's PowerFactory model, and the scenario CSVs.
- `reinforced` network case of `tx-full`: a second circuit parallel to L-26-27
  (`L-26-27-2`) in `testcase/tx-full/network/reinforced/` (XIIDM and CGMES), with its
  investment in `testcase/tx-full/economics/investments.csv`; the build reports the
  change in N and N-1 violations against `base`.
- Economic assumptions shared by every variant (value of lost load, battery cycling
  cost, redispatch premium, discount rate, asset lifetime, 345 kV line cost) in
  `testcase/tx-full/economics/`, with redispatch prices per generator.
- Contingency list for `tx-full` (six lines, one generator, one transformer, none
  splitting the network) in `testcase/tx-full/contingencies/contingencies.csv`, with
  post-contingency loadings in the build report and the presentation notebook.
- Scenario checks in the build (`data/inputs/scenarios/validation.yaml`): S1 is a
  clean reference, S2 shows the HVDC at its maximum and a voltage rise, S3 shows a
  voltage drop and overloads; the build stops otherwise.
- Documentation: `docs/test-case.md`, `docs/data-dictionary.md`,
  `docs/model-changes.md`.

- Permanent current limits on every line and transformer of `tx-full` (MC-2 in
  `docs/model-changes.md`), in XIIDM and CGMES, and branch loadings in the build
  report.
- Four bidding zones for `tx-full` (IEEE 14 and the three classic IEEE 39 areas):
  bus and element mappings, interconnections with capacities, and scheduled zone
  balances per scenario, in `testcase/tx-full/zones/`.
- Two batteries, 100 MW / 200 MWh at bus 6 (Z3) and 10 MW / 20 MWh at bus 106 (Z0):
  in the network models (XIIDM and CGMES, idle in every snapshot, MC-3 in
  `docs/model-changes.md`), with their set points in
  `testcase/tx-full/scenarios/battery_setpoints.csv` and their energy, efficiency and
  state-of-charge data in `testcase/tx-full/storage/batteries.csv`.
- Illustrative geographical coordinates for every `tx-full` substation (MC-5 in
  `docs/model-changes.md`): IEEE 14 in south-east England, IEEE 39 in northern France
  (Z1), Belgium (Z2) and the Netherlands (Z3). Stored in XIIDM as the
  `substationPosition` extension and per bus in
  `testcase/tx-full/network/bus_coordinates.csv`; the presentation notebook gains a
  geographical network-area diagram.
- Seven inverter-based wind and solar units in `tx-full` (MC-11 in
  `docs/model-changes.md`), 1500 MW in IEEE 39 and 80 MW in IEEE 14, as IIDM
  generators in XIIDM and CGMES, with their scenario output in
  `testcase/tx-full/scenarios/generation.csv`.
- Presentation notebook `notebooks/presentation.ipynb`, with plotting helpers in
  `hynet_testcase.viz`.
- Binder configuration (`binder/`) and README badge opening the presentation notebook.

### Changed

- IEEE 39 part of `tx-full` rescaled from a 1 kV base to 345 kV (MC-1 in
  `docs/model-changes.md`). Per-unit results are unchanged; values in kV, A and Ω
  become physical.
- Whitespace removed from the ids of `tx-full` (MC-4 in `docs/model-changes.md`):
  `"B101-G1 "` becomes `B101-G1`, `"B4-SH 1"` becomes `B4-SH-1`. Every id in the
  network models and CSVs changes accordingly, as do the CGMES UUIDs derived from
  them; values and load-flow results are unchanged.
- `tx-full` element data aligned with UCY's PowerFactory model, read from its DGS
  export (MC-6 to MC-10 in `docs/model-changes.md`): generator ratings, reactive
  limits and voltage set points, with B101-G1 now regulating at 1.06 p.u.;
  transformer impedances from their nameplate data, `T-20-34-1` as two units in
  parallel and `T-31-6-1` at a fixed ratio of 1.07; a second circuit of IEEE 14 line
  1-2 (`L-101-102-2`); the loads at buses 1, 16 and 20 (+45.2 MW in IEEE 39, also in
  every scenario); HVDC line at 320 kV and 0.75 Ω, `VSC_Station_16` at 0 Mvar instead
  of regulating bus 16, `VSC_Station_113` regulating bus 113 at 1.01 p.u., both within
  ±25 Mvar. Scenario voltages, loadings and post-contingency results change
  accordingly; every scenario check still passes.
- Units of `tx-full` rated and typed as in the PowerFactory model (MC-6): active power
  range 0 to S_n · cos φ_n (751.5 MW for most IEEE 39 units, 865.45 MW for B38-G1,
  819.9 MW for B39-G1), B103-G1, B106-G1 and B108-G1 as synchronous condensers at
  0 MW, types `NUCLEAR`, `COAL`, `HYDRO` and the new `CONDENSER` following
  PowerFactory; the base case runs the PowerFactory dispatch. `nominal_p_mw` in
  `generators.csv` is the rated active power, and the build stops if a scheduled
  output lies outside a unit's range.
- Thermal limits of `tx-full` are the PowerFactory ratings (MC-2): IEEE 39 lines
  unchanged except L-6-11 (480 MVA), step-up transformers 900–1000 MVA (`T-20-34`
  2 × 900 MVA), IEEE 14 lines 20, 50 or 100 MVA and transformers 50 or 100 MVA.
- HVDC link rated 50 MW (60 MW before), sized for IEEE 14; S1 and S3 run it at
  40 MW, S2 at its 50 MW maximum.
- S1–S3 rebuilt with a new dispatch rule: wind and solar at 50 / 100 / 10 % of their
  rating, every other synchronous unit at least at 30 % of its rating, the rest in
  merit order within each AC island, condensers at 0 MW. S3 reactive demand is the
  base case × 1.80 (× 1.50 before). S1 peaks at 91 % (L-113-114), S2 raises voltages
  by up to 0.035 p.u., S3 overloads L-2-3 and L-113-114 and lowers voltages by up to
  0.050 p.u.; post-contingency results and the zone balances change accordingly.
- `L-26-27-2` of the `reinforced` case is 58.3 km long, the length of line 26-27 in
  the PowerFactory model (47 km estimated before): investment 70.0 M EUR, annuity
  4.08 M EUR/year.
- The repository is split into two branches. `main` holds only the test case, its user
  documentation and the presentation notebook with its Binder configuration; it is
  generated from `dev` by the new `hynet-testcase publish` command, and its Binder
  installs the package from the `dev` commit it was published from. `dev` keeps the
  source models, the inputs and the build code. The schemas of the build inputs move
  from `docs/data-dictionary.md` to the new `docs/build.md`, together with the
  rebuilding and publishing instructions.
