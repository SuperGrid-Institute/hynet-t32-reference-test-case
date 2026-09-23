# Data dictionary

All CSV files are UTF-8, comma-separated, with a dot as decimal separator, one header
row and LF line endings. Timestamps are ISO 8601 in UTC (`YYYY-MM-DDTHH:MM:SSZ`).
Units follow IIDM: MW, Mvar, kV, A, Ω; energy in MWh; prices in EUR/MWh.

Ids are IIDM ids of the network and must be read as text, without trimming: most of
them end with a space (for example `"B101-G1 "`).

## `testcase/<variant>/scenarios/`

### `generation.csv`

Active power set point of every generator in every scenario.

| Column          | Type   | Unit | Description                                         |
|-----------------|--------|------|-----------------------------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario                           |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`                                  |
| `scenario_name` | text   | —    | Descriptive name, e.g. `baseline`                   |
| `generator_id`  | text   | —    | IIDM generator id                                   |
| `p_mw`          | number | MW   | Active power set point                              |

### `loads.csv`

Consumption of every load in every scenario.

| Column          | Type   | Unit | Description                    |
|-----------------|--------|------|--------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario      |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`             |
| `scenario_name` | text   | —    | Descriptive name               |
| `load_id`       | text   | —    | IIDM load id                   |
| `p_mw`          | number | MW   | Active power consumption       |
| `q_mvar`        | number | Mvar | Reactive power consumption     |

### `hvdc.csv`

Active power set point of every HVDC line in every scenario.

| Column          | Type   | Unit | Description                                            |
|-----------------|--------|------|--------------------------------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario                              |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`                                     |
| `scenario_name` | text   | —    | Descriptive name                                       |
| `hvdc_line_id`  | text   | —    | IIDM HVDC line id                                      |
| `target_p_mw`   | number | MW   | Set point at the rectifier side (IEEE 39 → IEEE 14)    |

### `generators.csv`

Illustrative characteristics of every generator, shared by all scenarios.

| Column          | Type    | Unit    | Description                                          |
|-----------------|---------|---------|------------------------------------------------------|
| `generator_id`  | text    | —       | IIDM generator id                                    |
| `subnetwork`    | text    | —       | `IEEE 14` or `IEEE 39`                               |
| `type`          | text    | —       | `NUCLEAR`, `COAL`, `GAS`, `HYDRO`, `WIND` or `SOLAR` |
| `nominal_p_mw`  | number  | MW      | Nominal active power, upper bound of the dispatch    |
| `price_eur_mwh` | number  | EUR/MWh | Marginal price used for the merit order              |
| `is_res`        | boolean | —       | `True` for renewable units (wind, solar, hydro)      |

## `testcase/<variant>/**/cgmes/id_mapping.csv`

Correspondence between IIDM ids and the CGMES identifiers of the files in the same
directory.

| Column         | Type | Description                                                              |
|----------------|------|--------------------------------------------------------------------------|
| `element_type` | text | `substation`, `voltage_level`, `generator`, `load`, `line`, `two_windings_transformer`, `shunt_compensator`, `hvdc_line` or `vsc_converter_station` |
| `iidm_id`      | text | IIDM id                                                                  |
| `cgmes_id`     | text | CGMES mRID (UUID, without the leading `_` of `rdf:ID`)                   |

## Inputs (`data/inputs/`)

Hand-edited files from which the build produces `testcase/`.

### `scenarios/`

| File                       | Shipped as                 | Schema                                                |
|----------------------------|----------------------------|-------------------------------------------------------|
| `generation_scenarios.csv` | `generation.csv`           | `timestamp, scenario, generator_id, p_mw`             |
| `load_scenarios.csv`       | `loads.csv`                | `timestamp, scenario, load_id, p_mw, q_mvar`          |
| `hvdc_setpoints.csv`       | `hvdc.csv`                 | `timestamp, scenario, hvdc_line_id, target_p_mw`      |
| `generators_metadata.csv`  | `generators.csv`           | as `generators.csv`                                   |

`scenario` holds the scenario name (`baseline`, `high_res_low_demand`,
`low_res_high_demand`). Each scenario has a single timestamp, the same in every file,
and sets every generator, load and HVDC line of the network exactly once.

### `network/<variant>_thermal_limits.csv`

Permanent current limit of every line and two-winding transformer of the variant,
applied to both sides. The build stops if a branch is missing or unknown.

| Column              | Type   | Unit | Description                          |
|---------------------|--------|------|--------------------------------------|
| `branch_id`         | text   | —    | IIDM line or transformer id          |
| `permanent_limit_a` | number | A    | Permanent current limit              |
| `basis`             | text   | —    | Origin of the value                  |

### `network/<variant>_corrections.yaml`

Corrections applied to the source model of a variant; see
[model-changes.md](model-changes.md).

| Key                                        | Type    | Unit | Description                                   |
|--------------------------------------------|---------|------|-----------------------------------------------|
| `voltage_rescale.source_nominal_kv`        | number  | kV   | Nominal voltage of the voltage levels to move |
| `voltage_rescale.target_nominal_kv`        | number  | kV   | Nominal voltage after correction              |
| `voltage_rescale.expected_voltage_levels`  | integer | —    | Number of voltage levels that must match      |
