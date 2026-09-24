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

### `battery_setpoints.csv`

Active power set point of every battery in every scenario.

| Column          | Type   | Unit | Description                                    |
|-----------------|--------|------|------------------------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario                      |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`                             |
| `scenario_name` | text   | —    | Descriptive name                               |
| `battery_id`    | text   | —    | IIDM battery id                                |
| `target_p_mw`   | number | MW   | Set point, positive when discharging           |

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

## `testcase/<variant>/zones/`

### `bus_zones.csv`

| Column    | Type | Description                          |
|-----------|------|--------------------------------------|
| `bus_id`  | text | IIDM bus-breaker bus id, e.g. `B16`  |
| `zone_id` | text | Zone id: `Z0`, `Z1`, `Z2` or `Z3`    |

### `element_zones.csv`

Zone of every generator and load, derived from the bus it connects to.

| Column         | Type | Description             |
|----------------|------|-------------------------|
| `element_type` | text | `generator`, `load` or `battery` |
| `element_id`   | text | IIDM id                 |
| `bus_id`       | text | Connection bus          |
| `zone_id`      | text | Zone id                 |

### `interconnections.csv`

AC branches whose ends lie in different zones, and HVDC links.

| Column               | Type   | Unit | Description                                                          |
|----------------------|--------|------|----------------------------------------------------------------------|
| `interconnection_id` | text   | —    | IIDM line, transformer or HVDC line id                               |
| `type`               | text   | —    | `ac_branch` or `hvdc`                                                |
| `zone_from`          | text   | —    | Zone of side 1 (rectifier side for HVDC)                             |
| `zone_to`            | text   | —    | Zone of side 2 (inverter side for HVDC)                              |
| `capacity_mw`        | number | MW   | AC: √3 · U_nominal · permanent current limit; HVDC: maximum power   |

### `zone_balance.csv`

Scheduled balance of each zone, from the scenario set points (before losses).

| Column          | Type   | Unit | Description                                 |
|-----------------|--------|------|---------------------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario                   |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`                          |
| `zone_id`       | text   | —    | Zone id                                     |
| `generation_mw` | number | MW   | Sum of generator set points                 |
| `storage_mw`    | number | MW   | Sum of battery set points (positive: discharging) |
| `load_mw`       | number | MW   | Sum of load active power                    |
| `balance_mw`    | number | MW   | Generation plus storage minus load (positive: exporting) |

## `testcase/<variant>/storage/batteries.csv`

Characteristics of the batteries. Their power capability is also in the network
models; energy capacity, efficiencies and states of charge are only here.

| Column                 | Type   | Unit | Description                                           |
|------------------------|--------|------|-------------------------------------------------------|
| `battery_id`           | text   | —    | Battery id                                            |
| `bus_id`               | text   | —    | Connection bus (IIDM bus-breaker bus id)              |
| `zone_id`              | text   | —    | Zone of the connection bus                            |
| `power_mw`             | number | MW   | Maximum charging and discharging power; also the reactive range (± Mvar) in the network |
| `energy_mwh`           | number | MWh  | Energy capacity                                       |
| `charge_efficiency`    | number | —    | Fraction of the absorbed energy that is stored        |
| `discharge_efficiency` | number | —    | Fraction of the released stored energy that is delivered |
| `initial_soc`          | number | —    | State of charge at the start, fraction of `energy_mwh` |
| `final_soc`            | number | —    | Required state of charge at the end, fraction of `energy_mwh` |

## `testcase/<variant>/**/cgmes/id_mapping.csv`

Correspondence between IIDM ids and the CGMES identifiers of the files in the same
directory.

| Column         | Type | Description                                                              |
|----------------|------|--------------------------------------------------------------------------|
| `element_type` | text | `substation`, `voltage_level`, `generator`, `load`, `line`, `two_windings_transformer`, `shunt_compensator`, `hvdc_line`, `vsc_converter_station` or `battery` |
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
| `battery_setpoints.csv`    | `battery_setpoints.csv`    | `timestamp, scenario, battery_id, target_p_mw`        |
| `generators_metadata.csv`  | `generators.csv`           | as `generators.csv`                                   |

`scenario` holds the scenario name (`baseline`, `high_res_low_demand`,
`low_res_high_demand`). Each scenario has a single timestamp, the same in every file,
and sets every generator, load, HVDC line and battery of the network exactly once.

### `zones/<variant>_bus_zones.csv`

Zone of every bus-breaker bus, with the same columns as the shipped `bus_zones.csv`.
The build stops if a bus is missing, unknown or listed twice, or if a zone is not
connected through its own branches.

### `storage/<variant>_batteries.csv`

Same columns as the shipped `batteries.csv`, without `zone_id`, which the build derives
from the zone mapping. The build adds each battery to the network models at its bus.
The build stops if a bus is unknown, an id is repeated or already used, power or
energy is not positive, an efficiency is outside (0, 1] or a state of charge outside
[0, 1].

### `network/<variant>_thermal_limits.csv`

Permanent current limit of every line and two-winding transformer of the variant,
applied to both sides. The build stops if a branch is missing or unknown.

| Column              | Type   | Unit | Description                          |
|---------------------|--------|------|--------------------------------------|
| `branch_id`         | text   | —    | IIDM line or transformer id          |
| `permanent_limit_a` | number | A    | Permanent current limit              |
| `basis`             | text   | —    | Origin of the value                  |

### `scenarios/validation.yaml`

Rules each scenario must satisfy on the base network case. Each top-level key is a
scenario id (`S1`, `S2`, `S3`); every rule is optional.

| Key                       | Type          | Unit | Rule                                                        |
|---------------------------|---------------|------|-------------------------------------------------------------|
| `max_branch_loading_pct`  | number        | %    | No branch loaded above this                                 |
| `voltage_band_pu`         | [number, number] | p.u. | Every bus voltage within the band                        |
| `hvdc_at_max`             | boolean       | —    | Every HVDC line carries its maximum power                   |
| `min_voltage_rise_pu`     | number        | p.u. | Some bus at least this much above its S1 voltage            |
| `min_voltage_drop_pu`     | number        | p.u. | Some bus at least this much below its S1 voltage            |
| `min_overloaded_branches` | integer       | —    | At least this many branches above 100 %                     |

### `network/<variant>_corrections.yaml`

Corrections applied to the source model of a variant; see
[model-changes.md](model-changes.md).

| Key                                        | Type    | Unit | Description                                   |
|--------------------------------------------|---------|------|-----------------------------------------------|
| `voltage_rescale.source_nominal_kv`        | number  | kV   | Nominal voltage of the voltage levels to move |
| `voltage_rescale.target_nominal_kv`        | number  | kV   | Nominal voltage after correction              |
| `voltage_rescale.expected_voltage_levels`  | integer | —    | Number of voltage levels that must match      |
