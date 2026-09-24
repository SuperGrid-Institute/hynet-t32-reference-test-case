# HYNET Task 3.2 reference test case

Common reference test case of HYNET Task 3.2, used to validate tool behaviour before
the demonstrations, to compare similar tools and to investigate tool complementarity.
This page describes what `testcase/` contains and how it is produced. File schemas
are in [data-dictionary.md](data-dictionary.md); corrections to the source models are
in [model-changes.md](model-changes.md).

## Content

| Variant   | Content                                      | Status    |
|-----------|----------------------------------------------|-----------|
| `tx-full` | IEEE 39-bus + VSC HVDC link + IEEE 14-bus    | Available |

Planned: economic assumptions, contingencies, a `reinforced` network case, a reduced
variant (`tx-reduced`) and a distribution variant (`dx-33`).

### `tx-full`

The IEEE 39-bus (345 kV) and IEEE 14-bus (138 kV) systems are two separate AC
islands, joined only by the VSC HVDC link `HVDC_Link_16_113` from IEEE 39 bus 16 to
IEEE 14 bus 13 (maximum 60 MW, rectifier on the IEEE 39 side).

Element ids are those of the source model. Generator, load, line, transformer and
shunt ids end with a space (for example `"B101-G1 "`); the space is part of the id.

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

The build reports voltages, the HVDC flow and branch loadings for each state. These
are reported, not enforced.

The base case keeps the operating point of the source model. Each scenario snapshot
is the base case with the scenario's generation, loads and HVDC set point applied.
These load flows validate the data; they are not results of any HYNET tool.

Voltages at the solved states range from about 0.94 to 1.09 p.u.: IEEE 14 generator
set points reach 1.09 p.u., and S3 drops the lowest IEEE 14 voltage to 0.94 p.u.
Voltage control (for example with a reactive optimal power flow) is left to the tools.

### Branch loadings

Every line and transformer has a permanent current limit (see
[model-changes.md](model-changes.md), MC-2). Loadings at the solved states, in % of
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

## Formats

| Format     | Shipped for                  | Notes                                            |
|------------|------------------------------|--------------------------------------------------|
| XIIDM      | base case and each snapshot  | IIDM 1.17, sorted. Reference format.             |
| CGMES      | base case and each snapshot  | CGMES 2.4.15: EQ, TP, SSH and SV profiles.       |
| PowerFactory (`.pfd`) | base case only    | UCY's model, shipped unchanged.                  |

### CGMES

- CGMES identifiers (mRID) are UUIDs derived from the IIDM ids; the source ids
  contain spaces and are not valid CGMES identifiers. Each CGMES directory holds an
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
[model-changes.md](model-changes.md), none of the scenario states and no batteries.

## Layout of `testcase/`

```
testcase/tx-full/
├── network/base/
│   ├── xiidm/tx-full_base.xiidm
│   ├── cgmes/tx-full_base_{EQ,TP,SSH,SV}.xml, id_mapping.csv
│   └── pfd/TestCase.pfd
├── zones/
│   └── bus_zones.csv, element_zones.csv, interconnections.csv, zone_balance.csv
├── storage/
│   └── batteries.csv
└── scenarios/
    ├── generation.csv, loads.csv, hvdc.csv, battery_setpoints.csv, generators.csv
    └── snapshots/S1..S3/
        ├── xiidm/tx-full_base_S<n>.xiidm
        └── cgmes/tx-full_base_S<n>_{EQ,TP,SSH,SV}.xml, id_mapping.csv
```

## Rebuilding

`testcase/` is generated from `data/` and must not be edited by hand:

```sh
uv sync
uv run hynet-testcase build
```

Rebuilding from an unchanged commit reproduces `testcase/` byte for byte. The build
stops, without writing anything, if an input file is malformed, if an id does not
resolve in the network, if a network element is not covered by every scenario, or if
a load flow does not converge.

## Presentation notebook

[`notebooks/presentation.ipynb`](../notebooks/presentation.ipynb) presents the test case
from the files in `testcase/`: network-area diagram coloured by zone, interactive
explorer (live kernel only), zones and interconnections, HVDC link, scenario dispatch and
zone balances, voltage profiles, branch loadings and batteries. It is committed with its
outputs. To re-execute it:

```sh
uv run python -m nbconvert --to notebook --execute --inplace     --ExecutePreprocessor.store_widget_state=False notebooks/presentation.ipynb
```

`store_widget_state=False` keeps the explorer's state (about 12 MB) out of the file.

The notebook also runs on [Binder](https://mybinder.org/v2/gh/SuperGrid-Institute/hynet-t32-reference-test-case/HEAD?labpath=notebooks%2Fpresentation.ipynb),
configured in `binder/`: Python 3.14 (`runtime.txt`), dependencies pinned from
`uv.lock` (`requirements.txt`) and the package installed by `postBuild`.

## Dependencies

Dependencies are managed with uv. After changing them, refresh both exported
requirement files:

```sh
uv export --format requirements-txt --no-dev --group notebooks --no-hashes -o requirements.txt
uv export --format requirements-txt --no-dev --group notebooks --no-hashes --no-emit-project -o binder/requirements.txt
```

## Acknowledgement

<img src="assets/eu-emblem.svg" alt="Flag of the European Union" height="48">

HYNET project has received funding from the European Union's Horizon Europe research
and innovation programme under Grant Agreement No 101172757.
