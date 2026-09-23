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
  metadata. Timestamps are UTC.
  In S1, RES run at 50 % of nominal power and the rest is dispatched in merit order
  within each AC island (IEEE 39, IEEE 14), accounting for the HVDC transfer, as in
  S2 and S3.
- Scenario presentation (`docs/scenarios_presentation.pptx`).
