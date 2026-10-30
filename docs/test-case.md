# HYNET Task 3.2 reference test case

Common reference test case of HYNET Task 3.2, used to validate tool behaviour before
the demonstrations, to compare similar tools and to investigate tool complementarity.
This page describes what `testcase/` contains and how it is produced. File schemas
are in [data-dictionary.md](data-dictionary.md), corrections to the source models in
[model-changes.md](model-changes.md) and the build and its inputs in
[build.md](build.md).

## Content

| Variant   | Content                                      | Status    |
|-----------|----------------------------------------------|-----------|
| `tx-full` | IEEE 39-bus + VSC HVDC link + IEEE 14-bus    | Available |

`tx-full` comes in two network cases: `base`, and `reinforced` (see below).
Planned: a reduced variant (`tx-reduced`).

### `tx-full`

The IEEE 39-bus (345 kV) and IEEE 14-bus (138 kV) systems are two separate AC
islands, joined only by the VSC HVDC link `HVDC_Link_16_113` from IEEE 39 bus 16 to
IEEE 14 bus 13 (rated 50 MW, rectifier on the IEEE 39 side). The data of the
synchronous units, transformers, three loads and the HVDC link follow UCY's
PowerFactory model (see [Changes to the source model](#changes-to-the-source-model)),
which is at 60 Hz. Seven wind and solar units and two batteries are added to it.

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
effects in [model-changes.md](model-changes.md)):

- **MC-1.** The IEEE 39 part is rescaled from a 1 kV base to 345 kV, its nominal
  voltage. Per-unit results are unchanged; values in kV, A and Ω become physical.
- **MC-2.** Every line and transformer gets a permanent current limit, which the source
  lacks: the ratings of the PowerFactory model, converted at the nominal voltages of
  the test case.
- **MC-3.** The two batteries (see [Storage](#storage)) are added.
- **MC-4.** Whitespace is removed from ids: for example `B101-G1` for the source's
  `"B101-G1 "` and `B4-SH-1` for `"B4-SH 1"`.
- **MC-5.** Every substation gets geographical coordinates (see
  [Geography](#geography)).
- **MC-6 to MC-10.** Element data are aligned with UCY's PowerFactory model, the
  reference: generator ratings, active and reactive ranges, voltage set points and
  base-case dispatch, with three units as synchronous condensers (MC-6),
  transformer impedances and the ratio of `T-31-6-1` (MC-7), the second circuit of
  IEEE 14 line 1-2, `L-101-102-2` (MC-8), the loads at buses 1, 16 and 20 (MC-9), and
  the HVDC data, converter control and 50 MW rating (MC-10).
- **MC-11.** Seven wind and solar units are added (see [Generation](#generation)).

None of them applies to the PowerFactory model, shipped as received (see
[PowerFactory](#powerfactory)).

## Bidding zones

Four bidding zones overlay the network; they do not change it. IEEE 39 follows its
classic three-area partition and IEEE 14 forms a zone of its own.

| Zone | Buses                                    | Synchronous units                      | Wind and solar units     |
|------|------------------------------------------|----------------------------------------|--------------------------|
| Z0   | IEEE 14: 101–114                         | B101, B102; condensers B103, B106, B108 | WF-B101-1, PV-B106-1    |
| Z1   | 15, 16, 19–24, 33–36                     | B33, B34, B35, B36                     | WF-B15-1, PV-B21-1       |
| Z2   | 1, 2, 3, 17, 18, 25–30, 37, 38           | B30, B37, B38                          | WF-B3-1                  |
| Z3   | 4–14, 31, 32, 39                         | B31, B32, B39                          | WF-B14-1, PV-B6-1        |

Each zone is connected through its own branches. Zones are linked by:

| Interconnection | Type      | Zones   | Capacity |
|-----------------|-----------|---------|----------|
| L-1-39          | AC line   | Z2 – Z3 | 1000 MVA |
| L-3-4           | AC line   | Z2 – Z3 | 500 MVA  |
| L-14-15         | AC line   | Z3 – Z1 | 600 MVA  |
| L-16-17         | AC line   | Z1 – Z2 | 600 MVA  |
| HVDC_Link_16_113| VSC HVDC  | Z1 → Z0 | 50 MW    |

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

Each has a two-hour duration, sits next to a solar park (`PV-B6-1`, 400 MW;
`PV-B106-1`, 30 MW) and has about 12 % of the wind and solar capacity of its zone
(800 MW in Z3, 80 MW in Z0).

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

## Generation

The synchronous units are those of the PowerFactory model, with its ratings and its
types; three of them are synchronous condensers. Seven inverter-based wind and solar
units are added (MC-11 in [model-changes.md](model-changes.md)).

| Type      | Units                                        | Rated P (MW) | Price (EUR/MWh) |
|-----------|----------------------------------------------|--------------|-----------------|
| NUCLEAR   | B31, B32, B35, B37 (751.5 each), B38, B39, B101 | 5072.15    | 8               |
| COAL      | B33, B34, B36 (751.5 each)                   | 2254.5       | 45              |
| GAS       | B102                                         | 80           | 70              |
| HYDRO     | B30                                          | 560.5        | 5               |
| CONDENSER | B103, B106, B108                             | 0            | 0               |
| WIND      | WF-B14-1, WF-B15-1, WF-B3-1, WF-B101-1       | 950          | 1               |
| SOLAR     | PV-B6-1, PV-B21-1, PV-B106-1                 | 630          | 0               |

B38-G1 (865.45 MW), B39-G1 (819.9 MW, the IEEE 39 equivalent of the external
system) and B101-G1 (380.8 MW) are the nuclear units outside the 751.5 MW class.
Types of the units PowerFactory leaves as "Others" (B39, B101, B102) are those of
earlier versions of the test case. Prices are synthetic. `scenarios/generators.csv`
lists every unit; `nominal_p_mw` is its rated active power, the upper bound of its
active power range in the network models.

## Scenarios

| Id | Name                  | Timestamp (UTC)      | Loads (P / Q)   | Wind and solar   | HVDC  |
|----|-----------------------|----------------------|-----------------|------------------|-------|
| S1 | `baseline`            | 2025-01-01T00:00:00Z | × 1.00 / × 1.00 | 50 % of rating   | 40 MW |
| S2 | `high_res_low_demand` | 2025-01-01T01:00:00Z | × 0.70 / × 0.70 | 100 % of rating  | 50 MW |
| S3 | `low_res_high_demand` | 2025-01-01T02:00:00Z | × 1.08 / × 1.80 | 10 % of rating   | 40 MW |

Load factors apply to the active (P) and reactive (Q) power of the loads of the base
case. S3 raises reactive demand more than active demand, as at a low power factor
peak, so that it shows a voltage drop as well as thermal stress. Only S2 runs the HVDC
link at its 50 MW rating.

The dispatch follows one rule in every scenario:

1. wind and solar units at the scenario share of their rating, condensers at 0 MW;
2. every other synchronous unit at least at 30 % of its rated active power, a minimum
   stable output (scaled down uniformly when the minimums exceed the demand of the
   island, as in IEEE 14 in S2);
3. the rest in merit order of price (ties in file order) within each AC island, so
   that each island balances its load plus or minus the HVDC transfer; losses are
   left to the slack.

The minimum output keeps units that regulate voltage in operation. Without it, merit
order would shut down most coal units of zone Z1 in S1 and overload L-2-3. No unit is
dispatched above its rated active power. This dispatch is a simple, reproducible
starting point: adequacy and market tools compute their own.

| Synchronous dispatch (MW) | S1    | S2    | S3    |
|---------------------------|-------|-------|-------|
| B30 (hydro)               | 560.5 | 560.5 | 560.5 |
| B31                       | 751.5 | 467.5 | 751.5 |
| B32, B35, B37 (each)      | 751.5 | 225.4 | 751.5 |
| B38                       | 865.4 | 259.6 | 865.4 |
| B39                       | 376.4 | 246.0 | 819.9 |
| B33                       | 225.4 | 225.4 | 751.5 |
| B34                       | 225.4 | 225.4 | 351.5 |
| B36                       | 225.4 | 225.4 | 225.4 |
| B101                      | 155.0 | 42.4  | 207.7 |
| B102                      | 24.0  | 8.9   | 24.0  |

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
[build.md](build.md#scenariosvalidationyaml)). The build stops, without
writing anything, if a scenario breaks one. Voltage rises and drops are measured bus by
bus against S1.

| Scenario | Rules                                                                   | Value at the current state |
|----------|-------------------------------------------------------------------------|----------------------------|
| S1       | No branch above 100 %; every voltage within 0.90–1.10 p.u.              | 91 %; 0.98–1.06 p.u.       |
| S2       | HVDC at its maximum; some bus at least 0.015 p.u. above S1              | 50 MW; +0.035 p.u.         |
| S3       | At least one branch above 100 %; some bus at least 0.03 p.u. below S1   | 2 overloads; −0.050 p.u.   |

The S1 band is wider than the usual 0.95–1.05 p.u. because generator set points reach
1.06 p.u.

The base case is the operating point of the PowerFactory model: its unit set points,
the HVDC link at 50 MW, wind, solar and batteries idle. Its set points are not
balanced (see [model-changes.md](model-changes.md#remarks-passed-on-to-the-model-provider)),
so the slack takes up more than the losses. Each scenario snapshot is the base case
with the scenario's generation, loads and HVDC set point applied.
These load flows validate the data; they are not results of any HYNET tool.

Voltages at the solved states range from about 0.95 to 1.08 p.u.: generator set
points reach 1.06 p.u., S2 lifts IEEE 39 voltages to 1.08 p.u. and S3 drops the
lowest IEEE 14 voltage to 0.95 p.u. The IEEE 14 condensers and B102-G1 reach their
small reactive limits in S1 and S3, and the converter at bus 113 reaches its ±25 Mvar
limit in S2. Voltage control (for example with a reactive optimal power flow) is left
to the tools.

### Branch loadings

Every line and transformer has a permanent current limit (see
[model-changes.md](model-changes.md), MC-2). Loadings at the solved states, in % of
the limit:

| State | Highest loading         | Overloaded branches                                         |
|-------|-------------------------|-------------------------------------------------------------|
| base  | 93 % (L-113-114)        | —                                                           |
| S1    | 91 % (L-113-114)        | —                                                           |
| S2    | 99 % (L-113-114)        | —                                                           |
| S3    | 104 % (L-2-3)           | L-2-3 104 %, L-113-114 102 %                                |

L-113-114 (20 MVA) carries part of the HVDC infeed at bus 113 towards bus 114; at
50 MW, in S2, it is close to its limit, so the HVDC interconnection is binding. S3 is
meant to stress thermal limits: L-2-3 carries part of the export of zone Z2.

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
| `N1-L-26-29`   | line L-26-29              | carries the output of B38 towards bus 26                 |
| `N1-L-6-11`    | line L-6-11               | next to battery `BAT-B6-1`                               |
| `N1-L-21-22`   | line L-21-22              | inside zone Z1                                           |
| `N1-L-16-17`   | line L-16-17              | tie line between zones Z1 and Z2                         |
| `N1-L-104-105` | line L-104-105            | central IEEE 14 line; overloads L-113-114                |
| `N1-B38-G1`    | generator B38-G1 (865 MW) | largest unit                                             |
| `N1-T-104-107` | transformer T-104-107     | IEEE 14 transformer that does not isolate any bus        |

Highest branch loading after each outage (% of the permanent limit), from AC load flows
with the settings above; a lost generator's output is taken up by the other units in
proportion to their output:

| Contingency    | S1    | S2    | S3    |
|----------------|-------|-------|-------|
| `N1-L-26-27`   | 145 % | 99 %  | 165 % |
| `N1-L-26-29`   | 93 %  | 99 %  | 105 % |
| `N1-L-6-11`    | 121 % | 99 %  | 125 % |
| `N1-L-21-22`   | 121 % | 99 %  | 125 % |
| `N1-L-16-17`   | 91 %  | 99 %  | 105 % |
| `N1-L-104-105` | 114 % | 116 % | 127 % |
| `N1-B38-G1`    | 91 %  | 99 %  | 138 % |
| `N1-T-104-107` | 111 % | 102 % | 137 % |

The build reports these post-contingency overloads; it does not enforce them. Neither
island is N-1 secure, even in S1.

## Reinforced case

The `reinforced` network case is the `base` case plus a second circuit parallel to
L-26-27, `L-26-27-2`, with the same impedance, admittance and current limit (600 MVA).
It is shipped as a network only (`network/reinforced/`, XIIDM and CGMES): tools apply
the scenario set points of `scenarios/` to it.

| New line    | Length  | Investment  | Annuity (5 %, 40 years) |
|-------------|---------|-------------|-------------------------|
| `L-26-27-2` | 58.3 km | 70.0 M EUR  | 4.08 M EUR/year         |

The length is that of line 26-27 in the PowerFactory model; the cost uses the 1.2 M EUR/km of the economic
assumptions. The build compares both cases on every scenario and reports, without
enforcing it, how violations change:

| Scenario | Overloads with all lines in service | Post-contingency overloads | Outage of L-26-27 (highest loading) |
|----------|-------------------------------------|----------------------------|-------------------------------------|
| S1       | 0 → 0                               | 11 → 9                     | 145 % → 91 %                        |
| S2       | 0 → 0                               | 3 → 3                      | 99 % → 99 %                         |
| S3       | 2 → 1                               | 25 → 19                    | 165 % → 104 %                       |

Post-contingency overloads count (contingency, overloaded branch) pairs. The
reinforcement secures the L-26-27 corridor in S1, relieves L-2-3 in S3 and leaves the
IEEE 14 bottleneck L-113-114, which lies elsewhere.

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
  set point but not the 50 MW limit, which is in XIIDM.
- Wind and solar units are exported as synchronous machines on a
  `WindGeneratingUnit` or `SolarGeneratingUnit`, the only way CGMES 2.4.15 attaches a
  generating unit to a generator. The condensers are synchronous machines of kind
  generator with a 0 MW range.
- CGMES 2.4.15 has no battery class. Each battery is exported as a synchronous
  machine on a hydro generating unit with a negative minimum power, and is read back
  as a generator. Its `RotatingMachine.ratedS` is a placeholder (the largest double):
  IIDM batteries have no rated power.
- Bus-view ids generated by pypowsybl (such as `VL6_0`) are not stable between
  formats; use substation, voltage level or bus-breaker bus ids (such as `B6`).

### PowerFactory

The `.pfd` file is UCY's model, used for dynamic studies, and the reference for
element data: MC-6 to MC-10 align the other formats with it. pypowsybl can neither
read nor write it, so it holds none of the other corrections in
[model-changes.md](model-changes.md) and none of the scenario states. Its element names
are those of the source model, before MC-4: applying the MC-4 rule to them gives the
ids of the other formats.

What the `.pfd` does not hold, for anyone reproducing a snapshot in PowerFactory:

- the seven wind and solar units (MC-11): bus, rating, reactive range in
  [model-changes.md](model-changes.md#mc-11--wind-and-solar-units-added) and active
  power of each snapshot in `scenarios/generation.csv`; they can be added as static
  generators (`ElmGenstat`);
- the two batteries, idle in every snapshot;
- the HVDC rating of the test case, 50 MW (500 MW in PowerFactory): S1 and S3 run at
  40 MW, S2 at 50 MW (`scenarios/hvdc.csv`), and the ±25 Mvar converter limits;
- the shunts `B4-SH-1` and `B5-SH-1`, which only the XIIDM and CGMES models have;
- the dispatch of each snapshot (`scenarios/generation.csv`), with the condensers at
  0 MW, and the loads (`scenarios/loads.csv`).

The differences the test case keeps with the PowerFactory model, and the remarks
passed on to UCY, are listed in [model-changes.md](model-changes.md).

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
scenario, if a scheduled generator output lies outside the unit's range, if a load
flow does not converge or moves a battery, or if a scenario check fails.
[build.md](build.md) describes the build and its inputs.

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
