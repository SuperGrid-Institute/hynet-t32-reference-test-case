# Data dictionary

All CSV files are UTF-8, comma-separated, with a dot as decimal separator, one header
row and LF line endings. Timestamps are ISO 8601 in UTC (`YYYY-MM-DDTHH:MM:SSZ`).
Units follow IIDM: MW, Mvar, kV, A, Ω; energy in MWh; prices in EUR/MWh.

Ids are IIDM ids of the network. They contain no whitespace (MC-4 in
[model-changes.md](model-changes.md)) and should be read as text.

## `testcase/<variant>/scenarios/`

### `generation.csv`

Active power set point of every generator in every scenario. The values follow the
placeholder dispatch of [test-case.md](test-case.md#scenarios) (wind and solar at a
share of their rating, synchronous units at a 30 % minimum and in merit order within
each AC island, condensers at 0 MW); losses are left to the slack. Every value lies
within the active power range of its generator in the network models.

| Column          | Type   | Unit | Description                                         |
|-----------------|--------|------|-----------------------------------------------------|
| `timestamp`     | text   | UTC  | Timestamp of the scenario                           |
| `scenario_id`   | text   | —    | `S1`, `S2` or `S3`                                  |
| `scenario_name` | text   | —    | Descriptive name, e.g. `baseline`                   |
| `generator_id`  | text   | —    | IIDM generator id                                   |
| `p_mw`          | number | MW   | Active power set point                              |

### `loads.csv`

Consumption of every load in every scenario. Each scenario scales the nominal loads by
one factor (S1 1.00, S2 0.70, S3 1.08 on P and 1.80 on Q).

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
connection between IEEE 39 and IEEE 14; S2 sets it to its 50 MW maximum.

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

Characteristics of every generator, shared by all scenarios. Types of the synchronous
units follow the PowerFactory model; prices are synthetic values of the test case, not
IEEE data, and set the merit order of the scenario dispatch.

| Column          | Type    | Unit    | Description                                          |
|-----------------|---------|---------|------------------------------------------------------|
| `generator_id`  | text    | —       | IIDM generator id                                    |
| `subnetwork`    | text    | —       | `IEEE 14` or `IEEE 39`                               |
| `type`          | text    | —       | `NUCLEAR`, `COAL`, `GAS`, `HYDRO`, `WIND`, `SOLAR` or `CONDENSER` |
| `nominal_p_mw`  | number  | MW      | Rated active power (S_n · cos φ_n for synchronous units, 0 for condensers), the `max_p` of the network models |
| `price_eur_mwh` | number  | EUR/MWh | Marginal price used for the merit order              |
| `is_res`        | boolean | —       | `True` for renewable units (wind, solar, hydro)      |

Wind and solar units (`WF-*`, `PV-*`) are inverter-based; hydro (`B30-G1`) is a
synchronous unit, renewable but dispatched in merit order. `CONDENSER` units are
synchronous condensers: they produce no active power and regulate voltage.

## `testcase/<variant>/network/bus_coordinates.csv`

Illustrative geographical coordinates of every bus-breaker bus: those of its
substation, also stored in the XIIDM files as the `substationPosition` extension.
Use this file with CGMES and PowerFactory models, which do not hold them.

| Column          | Type   | Unit | Description                          |
|-----------------|--------|------|--------------------------------------|
| `bus_id`        | text   | —    | IIDM bus-breaker bus id, e.g. `B16`  |
| `substation_id` | text   | —    | IIDM substation id, e.g. `S16`       |
| `latitude`      | number | °    | WGS84 latitude                       |
| `longitude`     | number | °    | WGS84 longitude, east positive       |

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
only link, to within the 0.1 MW rounding of the dispatch; tools that compute their own dispatch may use it as a reference.

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
