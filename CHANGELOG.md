# Changelog

All result-affecting changes to the test case are listed here. Versions follow
[Semantic Versioning](https://semver.org/) applied to the test case: MAJOR for
breaking changes to ids, layout or CSV schema, MINOR for a new variant, case,
scenario or file, PATCH for corrected values.

## [Unreleased]

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
- Scenario presentation (`docs/scenarios_presentation.pptx`).
- `hynet-testcase build` command, generating `testcase/tx-full/`: the base network
  and one solved snapshot per scenario in XIIDM and CGMES 2.4.15 (with an IIDM →
  CGMES id mapping), UCY's PowerFactory model, and the scenario CSVs.
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
- Presentation notebook `notebooks/presentation.ipynb`, with plotting helpers in
  `hynet_testcase.viz`.
- Binder configuration (`binder/`) and README badge opening the presentation notebook.

### Changed

- IEEE 39 part of `tx-full` rescaled from a 1 kV base to 345 kV (MC-1 in
  `docs/model-changes.md`). Per-unit results are unchanged; values in kV, A and Ω
  become physical.
