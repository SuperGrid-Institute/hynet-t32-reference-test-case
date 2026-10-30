# HYNET Task 3.2 reference test case

Common reference test case of HYNET Task 3.2, used to validate tool behaviour before
the demonstrations, to compare similar tools and to investigate tool complementarity.
This page describes what `testcase/` contains and how it is produced. File schemas
are in [data-dictionary.md](data-dictionary.md), corrections to the source models in
[model-changes.md](https://github.com/SuperGrid-Institute/hynet-t32-reference-test-case/blob/82c6cc830d20427c9041c314d7e74fd9d3dd820e/docs/model-changes.md) and the build and its inputs in
[build.md](https://github.com/SuperGrid-Institute/hynet-t32-reference-test-case/blob/82c6cc830d20427c9041c314d7e74fd9d3dd820e/docs/build.md).

## Content

| Variant   | Content                                      | Status    |
|-----------|----------------------------------------------|-----------|
| `tx-full` | IEEE 39-bus + VSC HVDC link + IEEE 14-bus    | Available |

`tx-full` comes in two network cases: `base`, and `reinforced` (see below).
Planned: a reduced variant (`tx-reduced`).

### `tx-full`

The IEEE 39-bus (345 kV) and IEEE 14-bus (138 kV) systems are two separate AC
islands, joined only by the VSC HVDC link `HVDC_Link_16_113` from IEEE 39 bus 16 to
IEEE 14 bus 13 (maximum 60 MW, rectifier on the IEEE 39 side).

### Geography

Every substation has illustrative coordinates (WGS84) that place the test case
around the southern North Sea, following the bidding zones:

| Zone | Network               | Area                                       |
|------|-----------------------|--------------------------------------------|
| Z0   | IEEE 14               | South-east England (Kent, Sussex, Surrey)  |
| Z1   | IEEE 39               | Northern France (Nord, Pas-de-Calais)      |
| Z2   | IEEE 39               | Belgium                                    |
| Z3   | IEEE 39               | Netherlands                                |

The HVDC link crosses the Strait of Dover, from bus 16 near Gravelines to bus 113 near
Folkestone (about 80 km). Line lengths on the map broadly follow the line
reactances, but the coordinates are not those of real substations and the network does
not represent the real grids of these countries. Zones Z1 and Z3 touch only through
L-14-15, drawn along the Belgian coast, since France and the Netherlands share no
border. Buses of one substation share its coordinates, so L-107-109, inside substation
S104, has no length on the map.

The XIIDM files hold the coordinates as the IIDM `substationPosition` extension, which
pypowsybl uses for geographical diagrams and the network map. The CGMES files do not
hold them, nor does the PowerFactory model; `network/bus_coordinates.csv` gives them
for every bus.

### Changes to the source model

The build corrects the source model from UCY before shipping it. In short (reasons and
effects in [model-changes.md](https://github.com/SuperGrid-Institute/hynet-t32-reference-test-case/blob/82c6cc830d20427c9041c314d7e74fd9d3dd820e/docs/model-changes.md)):

- **MC-1.** The IEEE 39 part is rescaled from a 1 kV base to 345 kV, its nominal
  voltage. Per-unit results are unchanged; values in kV, A and Ω become physical.
- **MC-2.** Every line and transformer gets a permanent current limit, which the source
  lacks: IEEE 39 from the ratings of the IEEE 39 data set, five of them raised for the
  larger units and dispatch of this test case, and IEEE 14 from typical 138 kV
  conductor classes. The
  limits are part of this test case, not of the original data sets.
- **MC-3.** The two batteries (see [Storage](#storage)) are added.
- **MC-4.** Whitespace is removed from ids: for example `B101-G1` for the source's
  `"B101-G1 "` and `B4-SH-1` for `"B4-SH 1"`.
- **MC-5.** Every substation gets geographical coordinates (see
  [Geography](#geography)).

None of them applies to the PowerFactory model, shipped as received (see
[PowerFactory](#powerfactory)).

## Bidding zones

Four bidding zones overlay the network; they do not change it. IEEE 39 follows its
classic three-area partition and IEEE 14 forms a zone of its own.

| Zone | Buses                                    | Generators                         |
|------|------------------------------------------|------------------------------------|
| Z0   | IEEE 14: 101–114                         | B101 to B108 (5 units)             |
| Z1   | 15, 16, 19–24, 33–36                     | B33, B34, B35, B36                 |
| Z2   | 1, 2, 3, 17, 18, 25–30, 37, 38           | B30, B37, B38                      |
| Z3   | 4–14, 31, 32, 39                         | B31, B32, B39                      |

Each zone is connected through its own branches. Zones are linked by:

| Interconnection | Type      | Zones   | Capacity |
|-----------------|-----------|---------|----------|
| L-1-39          | AC line   | Z2 – Z3 | 1000 MVA |
| L-3-4           | AC line   | Z2 – Z3 | 500 MVA  |
| L-14-15         | AC line   | Z3 – Z1 | 600 MVA  |
| L-16-17         | AC line   | Z1 – Z2 | 600 MVA  |
| HVDC_Link_16_113| VSC HVDC  | Z1 → Z0 | 60 MW    |

AC capacities are the apparent power matching each line's permanent current limit at
nominal voltage; a zonal model may use them as transfer limits. `zones/zone_balance.csv`
gives the scheduled generation, storage, load and balance of each zone in each
scenario.

## Storage

Two batteries are part of the network models and of the adequacy data:

| Battery      | Bus  | Zone | Power  | Energy  | Charge / discharge efficiency | Initial and final SoC |
|--------------|------|------|--------|---------|-------------------------------|-----------------------|
| `BAT-B6-1`   | B6   | Z3   | 100 MW | 200 MWh | 0.95 / 0.95                   | 50 %                  |
| `BAT-B106-1` | B106 | Z0   | 10 MW  | 20 MWh  | 0.95 / 0.95                   | 50 %                  |

Each has a two-hour duration and about 10 % of the renewable capacity near it: bus 6
is next to the 570 MW solar unit at bus 31, bus 106 hosts the 30 MW solar unit of
IEEE 14.

- **In the network models** (XIIDM and CGMES, base case and every snapshot), each
  battery is an IIDM battery with an active power range of ± its power and a reactive
  range of ± its power in Mvar, a typical converter rating. The batteries are idle
  (0 MW, 0 Mvar) in every snapshot: security, OPF and adequacy tools decide their
  dispatch. `scenarios/battery_setpoints.csv` holds the set points.
- **In `storage/batteries.csv`**, with what IIDM does not hold: energy capacity,
  efficiencies and states of charge, used by the adequacy tools (Tool#3 and Tool#4).

The load flow shares losses between units in proportion to their output, so an idle
battery keeps its set point. The build stops if a load flow moves a battery off its
set point.

## Scenarios

| Id | Name                  | Timestamp (UTC)      | Loads (P / Q)   | RES output       | HVDC  |
|----|-----------------------|----------------------|-----------------|------------------|-------|
| S1 | `baseline`            | 2025-01-01T00:00:00Z | × 1.00 / × 1.00 | 50 % of nominal  | 50 MW |
| S2 | `high_res_low_demand` | 2025-01-01T01:00:00Z | × 0.70 / × 0.70 | 100 % of nominal | 60 MW |
| S3 | `low_res_high_demand` | 2025-01-01T02:00:00Z | × 1.08 / × 1.50 | 10 % of nominal  | 50 MW |

Load factors apply to the active (P) and reactive (Q) power of the loads of the source
model. S3 raises reactive demand more than active demand, as at a low power factor
peak, so that it shows a voltage drop: the IEEE 39 units have large reactive reserves,
while the small units of IEEE 14 reach their limits. RES are the wind, solar and hydro
units. The other units are dispatched in merit order (ties in file order) within each
AC island, so that each island balances its load plus or minus the HVDC transfer.
This dispatch is a simple, reproducible starting point: adequacy and market tools
compute their own.

Security and dynamic studies use each scenario as an independent snapshot. Adequacy
studies use the three timestamps as a series of three consecutive hourly steps.

The scenarios are introduced in
[scenarios_presentation.pptx](scenarios_presentation.pptx).

## Network states and load flow

The build solves every shipped network state with an AC load flow (OpenLoadFlow
through pypowsybl) before export:

- distributed slack, in proportion to the active power of the dispatched units, so
  losses are shared without changing the dispatch pattern;
- one result per AC island; the build stops if either island does not converge.

The build reports voltages, the HVDC flow, battery power and branch loadings for each
state, and checks that each scenario exhibits the phenomena it is designed for.

### Scenario checks

The rules are an input of the build (see
[build.md](https://github.com/SuperGrid-Institute/hynet-t32-reference-test-case/blob/82c6cc830d20427c9041c314d7e74fd9d3dd820e/docs/build.md#scenariosvalidationyaml)). The build stops, without
writing anything, if a scenario breaks one. Voltage rises and drops are measured bus by
bus against S1.

| Scenario | Rules                                                                   | Value at the current state |
|----------|-------------------------------------------------------------------------|----------------------------|
| S1       | No branch above 100 %; every voltage within 0.90–1.10 p.u.              | 92 %; 0.98–1.09 p.u.       |
| S2       | HVDC at its maximum; some bus at least 0.015 p.u. above S1              | 60 MW; +0.021 p.u.         |
| S3       | At least one branch above 100 %; some bus at least 0.03 p.u. below S1   | 4 overloads; −0.070 p.u.   |

The S1 band is wider than the usual 0.95–1.05 p.u. because the IEEE 14 generator set
points reach 1.09 p.u.

The base case keeps the operating point of the source model. Each scenario snapshot
is the base case with the scenario's generation, loads and HVDC set point applied.
These load flows validate the data; they are not results of any HYNET tool.

Voltages at the solved states range from about 0.94 to 1.09 p.u.: IEEE 14 generator
set points reach 1.09 p.u., and S3 drops the lowest IEEE 14 voltage to 0.94 p.u.
Voltage control (for example with a reactive optimal power flow) is left to the tools.

### Branch loadings

Every line and transformer has a permanent current limit (see
[model-changes.md](https://github.com/SuperGrid-Institute/hynet-t32-reference-test-case/blob/82c6cc830d20427c9041c314d7e74fd9d3dd820e/docs/model-changes.md), MC-2). Loadings at the solved states, in % of
the limit:

| State | Highest loading         | Overloaded branches                                         |
|-------|-------------------------|-------------------------------------------------------------|
| base  | 88 % (L-101-102)        | —                                                           |
| S1    | 92 % (T-10-32)          | —                                                           |
| S2    | 95 % (L-28-29)          | —                                                           |
| S3    | 162 % (L-16-19)         | L-16-19 162 %, L-101-102 118 %, L-6-11 106 %, L-10-11 103 % |

S3 is meant to stress thermal limits. L-16-19 is the only connection of buses 19, 20,
33 and 34 to the rest of the system, so it carries the output of units B33 and B34
minus the load at bus 20.

## Economic assumptions

Shared by every variant, so that results stay comparable across tools. They are common
values for a European test case, in `economics/parameters.csv`:

| Parameter                        | Value           |
|----------------------------------|-----------------|
| Value of lost load               | 10 000 EUR/MWh  |
| Battery cycling cost             | 2 EUR/MWh discharged |
| Redispatch premium               | 10 EUR/MWh      |
| Discount rate                    | 5 %             |
| Asset lifetime                   | 40 years        |
| Capital recovery factor          | 0.0583 per year (from the two above) |
| 345 kV overhead line cost        | 1.2 M EUR/km    |

Generator marginal costs are the prices of `scenarios/generators.csv`.
`economics/generator_costs.csv` adds redispatch prices: a unit increased by redispatch
is paid its marginal cost plus the premium; a unit decreased pays back its marginal cost
minus the premium, so a negative value means the unit is paid to reduce its output.

## Contingencies

`contingencies/contingencies.csv` lists eight single outages, a small selection that is
quick to analyse. None splits the network, so post-contingency results do not depend on
how a tool handles islands; the build checks this and stops otherwise.

| Contingency    | Element                   | Why                                                      |
|----------------|---------------------------|----------------------------------------------------------|
| `N1-L-26-27`   | line L-26-27              | corridor reinforced in the `reinforced` case             |
| `N1-L-26-29`   | line L-26-29              | its loss overloads L-28-29                               |
| `N1-L-6-11`    | line L-6-11               | next to battery `BAT-B6-1`                               |
| `N1-L-21-22`   | line L-21-22              | inside zone Z1                                           |
| `N1-L-16-17`   | line L-16-17              | tie line between zones Z1 and Z2                         |
| `N1-L-104-105` | line L-104-105            | central IEEE 14 line; deep voltage drop in S3            |
| `N1-B38-G1`    | generator B38-G1 (1245 MW)| largest unit whose loss converges in every scenario      |
| `N1-T-104-107` | transformer T-104-107     | IEEE 14 transformer that does not isolate any bus        |

Highest branch loading after each outage (% of the permanent limit), from AC load flows
with the settings above; a lost generator's output is taken up by the other units in
proportion to their output:

| Contingency    | S1    | S2    | S3    |
|----------------|-------|-------|-------|
| `N1-L-26-27`   | 121 % | 134 % | 163 % |
| `N1-L-26-29`   | 165 % | 186 % | 163 % |
| `N1-L-6-11`    | 161 % | 95 %  | 180 % |
| `N1-L-21-22`   | 145 % | 106 % | 162 % |
| `N1-L-16-17`   | 92 %  | 94 %  | 162 % |
| `N1-L-104-105` | 92 %  | 95 %  | 162 % |
| `N1-B38-G1`    | 117 % | 141 % | 228 % |
| `N1-T-104-107` | 92 %  | 95 %  | 162 % |

The build reports these post-contingency overloads; it does not enforce them. IEEE 39
is not N-1 secure, even in S1.

## Reinforced case

The `reinforced` network case is the `base` case plus a second circuit parallel to
L-26-27, `L-26-27-2`, with the same impedance, admittance and current limit (600 MVA).
It is shipped as a network only (`network/reinforced/`, XIIDM and CGMES): tools apply
the scenario set points of `scenarios/` to it.

| New line    | Length  | Investment  | Annuity (5 %, 40 years) |
|-------------|---------|-------------|-------------------------|
| `L-26-27-2` | 47 km   | 56.4 M EUR  | 3.29 M EUR/year         |

The length is estimated from the reactance of L-26-27 (17.5 Ω) at 0.37 Ω/km, typical
of a single-circuit 345 kV overhead line; the cost uses the 1.2 M EUR/km of the economic
assumptions. The build compares both cases on every scenario and reports, without
enforcing it, how violations change:

| Scenario | Overloads with all lines in service | Post-contingency overloads | Outage of L-26-27 (highest loading) |
|----------|-------------------------------------|----------------------------|-------------------------------------|
| S1       | 0 → 0                               | 13 → 13                    | 121 % → 92 %                        |
| S2       | 0 → 0                               | 10 → 7                     | 134 % → 95 %                        |
| S3       | 4 → 4                               | 44 → 43                    | 163 % → 162 %                       |

Post-contingency overloads count (contingency, overloaded branch) pairs. The
reinforcement secures the L-26-27 corridor in S1 and S2; it does not relieve the S3
bottlenecks, which lie elsewhere.

## Formats

| Format     | Shipped for                  | Notes                                            |
|------------|------------------------------|--------------------------------------------------|
| XIIDM      | base and reinforced cases, each snapshot | IIDM 1.17, sorted. Reference format. |
| CGMES      | base and reinforced cases, each snapshot | CGMES 2.4.15: EQ, TP, SSH and SV profiles. |
| PowerFactory (`.pfd`) | base case only    | UCY's model, shipped unchanged.                  |

### CGMES

- CGMES identifiers (mRID) are UUIDs derived from the IIDM ids, some of which (such
  as the network id) are not valid CGMES identifiers. Each CGMES directory holds an
  `id_mapping.csv`, and each element's `IdentifiedObject.name` is its IIDM id.
- `Model.scenarioTime` is the scenario timestamp (the source case date for the base
  case).
- CGMES 2.4.15 does not carry the HVDC maximum power. Tools reading CGMES see the
  set point but not the 60 MW limit, which is in XIIDM.
- CGMES 2.4.15 has no battery class. Each battery is exported as a synchronous
  machine on a hydro generating unit with a negative minimum power, and is read back
  as a generator. Its `RotatingMachine.ratedS` is a placeholder (the largest double):
  IIDM batteries have no rated power.
- Bus-view ids generated by pypowsybl (such as `VL6_0`) are not stable between
  formats; use substation, voltage level or bus-breaker bus ids (such as `B6`).

### PowerFactory

The `.pfd` file is UCY's model, used for dynamic studies. pypowsybl can neither
read nor write it, so it holds none of the corrections in
[model-changes.md](https://github.com/SuperGrid-Institute/hynet-t32-reference-test-case/blob/82c6cc830d20427c9041c314d7e74fd9d3dd820e/docs/model-changes.md), none of the scenario states and no batteries.
Its element names are those of the source model, before MC-4: applying the MC-4
rule to them gives the ids of the other formats.

## Layout of `testcase/`

```
testcase/tx-full/
├── network/bus_coordinates.csv
├── network/base/
│   ├── xiidm/tx-full_base.xiidm
│   ├── cgmes/tx-full_base_{EQ,TP,SSH,SV}.xml, id_mapping.csv
│   └── pfd/TestCase.pfd
├── network/reinforced/
│   ├── xiidm/tx-full_reinforced.xiidm
│   └── cgmes/tx-full_reinforced_{EQ,TP,SSH,SV}.xml, id_mapping.csv
├── zones/
│   └── bus_zones.csv, element_zones.csv, interconnections.csv, zone_balance.csv
├── storage/
│   └── batteries.csv
├── contingencies/
│   └── contingencies.csv
├── economics/
│   └── parameters.csv, generator_costs.csv, investments.csv
└── scenarios/
    ├── generation.csv, loads.csv, hvdc.csv, battery_setpoints.csv, generators.csv
    └── snapshots/S1..S3/
        ├── xiidm/tx-full_base_S<n>.xiidm
        └── cgmes/tx-full_base_S<n>_{EQ,TP,SSH,SV}.xml, id_mapping.csv
```

## Reproducibility

`testcase/` is generated by a build from the source models and hand-edited inputs; it
is never edited by hand. Rebuilding from an unchanged commit reproduces it byte for
byte. The build stops, without writing anything, if an input file is malformed, if an
id does not resolve in the network, if a network element is not covered by every
scenario, if a load flow does not converge or moves a battery, or if a scenario check
fails. [build.md](https://github.com/SuperGrid-Institute/hynet-t32-reference-test-case/blob/82c6cc830d20427c9041c314d7e74fd9d3dd820e/docs/build.md) describes the build and its inputs.

## Presentation notebook

[`notebooks/presentation.ipynb`](../notebooks/presentation.ipynb) presents the test case
from the files in `testcase/`: network-area diagrams coloured by zone (by topology and
on the map), interactive
explorer (live kernel only), zones and interconnections, HVDC link, scenario dispatch and
zone balances, voltage profiles, branch loadings, contingencies and batteries. It is
committed with its outputs, so it reads on GitHub without running it, and runs in the
browser on
[Binder](https://mybinder.org/v2/gh/SuperGrid-Institute/hynet-t32-reference-test-case/main?labpath=notebooks%2Fpresentation.ipynb),
explorer included, without installing anything.

## Acknowledgement

<img src="assets/eu-emblem.svg" alt="Flag of the European Union" height="48">

HYNET project has received funding from the European Union's Horizon Europe research
and innovation programme under Grant Agreement No 101172757.
