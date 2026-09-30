# Data dictionary

All CSV files are UTF-8, comma-separated, with a dot as decimal separator, one header
row and LF line endings. Timestamps are ISO 8601 in UTC (`YYYY-MM-DDTHH:MM:SSZ`).
Units follow IIDM: MW, Mvar, kV, A, Ω; energy in MWh; prices in EUR/MWh.

Ids are IIDM ids of the network. They contain no whitespace (MC-4 in
[model-changes.md](model-changes.md)) and should be read as text.

## `testcase/<variant>/scenarios/`

### `generation.csv`

Active power set point of every generator in every scenario. The values follow the
placeholder dispatch of [test-case.md](test-case.md#scenarios) (RES at a share of
nominal power, other units in merit order within each AC island); losses are left to
the slack generator.

| Column          | Type   | Unit | Description                                         |
|-----------------|--------|------|-----------------------------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario                           |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`                                  |
| `scenario_name` | text   | —    | Descriptive name, e.g. `baseline`                   |
| `generator_id`  | text   | —    | IIDM generator id                                   |
| `p_mw`          | number | MW   | Active power set point                              |

### `loads.csv`

Consumption of every load in every scenario. Each scenario scales the nominal loads by
one factor (S1 1.00, S2 0.70, S3 1.08 on P and 1.50 on Q).

| Column          | Type   | Unit | Description                    |
|-----------------|--------|------|--------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario      |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`             |
| `scenario_name` | text   | —    | Descriptive name               |
| `load_id`       | text   | —    | IIDM load id                   |
| `p_mw`          | number | MW   | Active power consumption       |
| `q_mvar`        | number | Mvar | Reactive power consumption     |

### `hvdc.csv`

Active power set point of every HVDC line in every scenario. The link is the only
connection between IEEE 39 and IEEE 14; S2 sets it to its 60 MW maximum.

| Column          | Type   | Unit | Description                                            |
|-----------------|--------|------|--------------------------------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario                              |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`                                     |
| `scenario_name` | text   | —    | Descriptive name                                       |
| `hvdc_line_id`  | text   | —    | IIDM HVDC line id                                      |
| `target_p_mw`   | number | MW   | Set point at the rectifier side (IEEE 39 → IEEE 14)    |

### `battery_setpoints.csv`

Active power set point of every battery in every scenario. Every battery is idle
(0 MW) in every scenario: the network models include the batteries, and each tool
decides their dispatch.

| Column          | Type   | Unit | Description                                    |
|-----------------|--------|------|------------------------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario                      |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`                             |
| `scenario_name` | text   | —    | Descriptive name                               |
| `battery_id`    | text   | —    | IIDM battery id                                |
| `target_p_mw`   | number | MW   | Set point, positive when discharging           |

### `generators.csv`

Illustrative characteristics of every generator, shared by all scenarios. Types and
prices are synthetic values of the test case, not IEEE data; they set the merit order
of the scenario dispatch.

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

Zone of every bus-breaker bus. It is the only zone input; every other file of this
directory is derived from it.

| Column    | Type | Description                          |
|-----------|------|--------------------------------------|
| `bus_id`  | text | IIDM bus-breaker bus id, e.g. `B16`  |
| `zone_id` | text | Zone id: `Z0`, `Z1`, `Z2` or `Z3`    |

### `element_zones.csv`

Zone of every generator, load and battery, derived from the bus it connects to. Use it
to aggregate scenario set points or tool results per zone without reading the network.

| Column         | Type | Description             |
|----------------|------|-------------------------|
| `element_type` | text | `generator`, `load` or `battery` |
| `element_id`   | text | IIDM id                 |
| `bus_id`       | text | Connection bus          |
| `zone_id`      | text | Zone id                 |

### `interconnections.csv`

AC branches whose ends lie in different zones, and HVDC links: the links of a zonal
model. AC capacities are thermal limits, not net transfer capacities: they include no
N-1 margin and ignore loop flows through the third zone of the Z1–Z2–Z3 ring.

| Column               | Type   | Unit | Description                                                          |
|----------------------|--------|------|----------------------------------------------------------------------|
| `interconnection_id` | text   | —    | IIDM line, transformer or HVDC line id                               |
| `type`               | text   | —    | `ac_branch` or `hvdc`                                                |
| `zone_from`          | text   | —    | Zone of side 1 (rectifier side for HVDC)                             |
| `zone_to`            | text   | —    | Zone of side 2 (inverter side for HVDC)                              |
| `capacity_mw`        | number | MW   | AC: √3 · U_nominal · permanent current limit; HVDC: maximum power   |

### `zone_balance.csv`

Scheduled balance of each zone, from the scenario set points (before losses). Balances
sum to zero in each scenario, and the balance of Z0 is minus the HVDC set point, its
only link; tools that compute their own dispatch may use it as a reference.

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
models; energy capacity, efficiencies and states of charge are only here. Both
batteries have a 2 h duration (`energy_mwh` = 2 × `power_mw`).

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

## `testcase/<variant>/economics/`

### `parameters.csv`

Economic assumptions shared by every variant, one row per parameter. The same values
apply to every tool, so that costs computed by different tools stay comparable.

| Column        | Type   | Description                     |
|---------------|--------|---------------------------------|
| `parameter`   | text   | Parameter name, with its unit as a suffix |
| `value`       | number | Value                           |
| `unit`        | text   | Unit (`-` when dimensionless)   |
| `description` | text   | Meaning of the parameter        |

Parameters: `value_of_lost_load_eur_mwh`, `battery_cycling_cost_eur_mwh`,
`redispatch_premium_eur_mwh`, `discount_rate`, `asset_lifetime_years`,
`capital_recovery_factor` (derived: r / (1 − (1 + r)^−n)) and `line_cost_345kv_eur_km`.

### `generator_costs.csv`

Costs of every generator for market and redispatch studies. The redispatch prices are
the marginal cost plus or minus `redispatch_premium_eur_mwh`.

| Column                    | Type   | Unit    | Description                                          |
|---------------------------|--------|---------|------------------------------------------------------|
| `generator_id`            | text   | —       | IIDM generator id                                    |
| `marginal_cost_eur_mwh`   | number | EUR/MWh | Marginal cost (the price of `generators.csv`)        |
| `redispatch_up_eur_mwh`   | number | EUR/MWh | Paid to the unit per MWh of upward redispatch        |
| `redispatch_down_eur_mwh` | number | EUR/MWh | Paid back by the unit per MWh of downward redispatch; negative when the unit is paid |

### `investments.csv`

Investment in each network reinforcement. The `reinforced` case adds one line,
`L-26-27-2`, whose length is estimated from the reactance of the parallel line.

| Column             | Type   | Unit     | Description                                        |
|--------------------|--------|----------|----------------------------------------------------|
| `element_id`       | text   | —        | IIDM id of the new element                         |
| `length_km`        | number | km       | Length of the new line                             |
| `investment_eur`   | number | EUR      | Length × 345 kV line cost                          |
| `annuity_eur_year` | number | EUR/year | Investment × capital recovery factor               |

## `testcase/<variant>/contingencies/contingencies.csv`

Single-element outages to analyse on every scenario. None splits the network. They are
a small selection, quick to analyse, valid on both the `base` and `reinforced` cases.

| Column           | Type | Description                                                 |
|------------------|------|-------------------------------------------------------------|
| `contingency_id` | text | Contingency id, e.g. `N1-L-26-27`                           |
| `element_type`   | text | `line`, `two_windings_transformer` or `generator`           |
| `element_id`     | text | IIDM id of the tripped element (CGMES: see `id_mapping.csv`) |

## `testcase/<variant>/**/cgmes/id_mapping.csv`

Correspondence between IIDM ids and the CGMES identifiers of the files in the same
directory. CGMES 2.4.15 has no battery class: batteries are exported as synchronous
machines and read back as generators, and this file is the way to find them.

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

### `economics/economics.yaml`

Shared by every variant: the parameters of `parameters.csv` except
`capital_recovery_factor`, which the build derives. Every key is required and every
value must be positive.

### `contingencies/<variant>_contingencies.csv`

Same columns as the shipped `contingencies.csv`. The build stops if an id or element is
repeated, an element is unknown or of another type, or a branch outage disconnects any
bus.

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

### `network/<variant>_reinforcement.yaml`

The new line of the `reinforced` case.

| Key                    | Type   | Unit | Description                                                 |
|------------------------|--------|------|-------------------------------------------------------------|
| `new_line.id`          | text   | —    | Id of the new line                                          |
| `new_line.parallel_to` | text   | —    | Existing line whose parameters and current limit are copied |
| `new_line.length_km`   | number | km   | Length, for the investment cost                             |

The build stops if the copied line is unknown, the new id is already used or the length
is not positive.

### `network/<variant>_corrections.yaml`

Corrections applied to the source model of a variant; see
[model-changes.md](model-changes.md).

| Key                                        | Type    | Unit | Description                                   |
|--------------------------------------------|---------|------|-----------------------------------------------|
| `voltage_rescale.source_nominal_kv`        | number  | kV   | Nominal voltage of the voltage levels to move |
| `voltage_rescale.target_nominal_kv`        | number  | kV   | Nominal voltage after correction              |
| `voltage_rescale.expected_voltage_levels`  | integer | —    | Number of voltage levels that must match      |
