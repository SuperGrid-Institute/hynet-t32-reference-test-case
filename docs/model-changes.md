# Changes to the source models

The source models in `data/sources/` are kept exactly as received. The build applies
the corrections below when it produces `testcase/`; each one is declared in
`data/inputs/network/` and is listed here with its reason and its effect.

The PowerFactory model (`TestCase.pfd`) is shipped unchanged: none of these
corrections apply to it.

## `tx-full`

Source: `data/sources/tx-full/TestCase.xiidm` (UCY). Corrections:
`data/inputs/network/tx-full_corrections.yaml`.

### MC-1 — IEEE 39 rescaled from a 1 kV base to 345 kV

**Finding.** The IEEE 39 part of the source is expressed in per unit on a 1 kV base:
its 27 voltage levels have a nominal voltage of 1 kV, and every impedance is the
per-unit value of the IEEE 39 data set multiplied by the 1 kV impedance base
(0.01 Ω at 100 MVA). For example, line 1–2 has r = 3.5·10⁻⁵ Ω, i.e.
0.0035 p.u. × 0.01 Ω. Load-flow results in per unit are correct, but every value in
kV, A or Ω on the IEEE 39 side is off by a factor of 345 (345² for impedances):
bus voltages read about 1 kV, currents tens of kA. The 1.0 voltage set point of
`VSC_Station_16` is a consequence of this, not a separate error.

**Correction.** The 27 voltage levels at 1 kV are moved to 345 kV, the nominal
voltage of the IEEE 39 system. With k = 345:

| Element                    | Attribute                              | Scaling |
|----------------------------|----------------------------------------|---------|
| Voltage levels             | nominal voltage                        | × k     |
| Lines                      | r, x                                   | × k²    |
| Lines                      | g1, b1, g2, b2                         | ÷ k²    |
| Two-winding transformers   | r, x                                   | × k²    |
| Two-winding transformers   | g, b                                   | ÷ k²    |
| Two-winding transformers   | rated voltages                         | × k     |
| Ratio tap changers         | voltage target                         | × k     |
| Linear shunt compensators  | g, b per section                       | ÷ k²    |
| Generators                 | voltage target                         | × k     |
| VSC converter stations     | voltage target                         | × k     |

The IEEE 14 part (138 kV) and the HVDC line are unchanged. The build stops if the
number of 1 kV voltage levels is not 27, if a branch connects a rescaled voltage level
to another one, or if the model contains an element type whose voltage-dependent
attributes the correction does not scale (phase tap changers, three-winding
transformers, static var compensators, dangling lines, LCC stations, non-linear
shunts, voltage or operational limits).

**Effect.** Per-unit voltages, angles and all active and reactive power flows are
unchanged: before and after the correction they agree to within 10⁻¹⁵. Values in kV,
A and Ω become physical.

### MC-2 — Thermal limits added

**Finding.** The source model carries no operational limits, so congestion and
thermal stress cannot be assessed.

**Correction.** Every line and two-winding transformer gets a permanent current limit,
the same on both sides, declared in `data/inputs/network/tx-full_thermal_limits.csv`
(67 branches) with the basis of each value:

| Branches                          | Count | Basis                                                                 |
|-----------------------------------|-------|-----------------------------------------------------------------------|
| IEEE 39 lines and transformers    | 41    | Rating `rateA` of the MATPOWER `case39` data set, converted at 345 kV |
| IEEE 39 line L-6-11               | 1     | `rateA` 480 MVA raised to 600 MVA: at 480 MVA, S1 would overload it   |
| IEEE 39 step-up transformers T-10-32, T-19-33, T-23-36, T-29-38 | 4 | Sized for their unit: P / 0.9, rounded up to the next 100 MVA. The units of this test case are larger than in the original data set, so its ratings (900–1200 MVA) are below the units' output. |
| IEEE 14 lines                     | 18    | 138 kV conductor classes of 400 or 600 A, the smallest keeping S1 at or below 80 %; `L-101-102-2` (MC-8) as `L-101-102-1` |
| IEEE 14 transformers              | 3     | 100 MVA at 138 kV                                                     |

MVA ratings are converted as I = S / (√3 · U_nominal).

**Effect.** Load-flow results are unchanged; limits only allow loadings to be
assessed. See [test-case.md](test-case.md#branch-loadings) for the resulting
loadings.

### MC-3 — Batteries added

**Finding.** The source model has no storage.

**Correction.** The two batteries of `data/inputs/storage/tx-full_batteries.csv` are
added as IIDM batteries at buses B6 (`BAT-B6-1`, ± 100 MW) and B106 (`BAT-B106-1`,
± 10 MW), with a reactive range of ± their power in Mvar. They are idle (0 MW, 0 Mvar)
in the base case and in every snapshot.

**Effect.** Load-flow results are unchanged, since the batteries are idle. The
PowerFactory model does not contain them.

### MC-4 — Whitespace removed from ids

**Finding.** 132 ids of the source contain whitespace. Generator, load, line,
transformer and shunt ids end with a space (`"B101-G1 "`, `"L-26-27-1 "`), the three
shunts `"B4-SH 1"`, `"B5-SH 1"` and `"B109-SH 1"` contain one, and so do the network
and subnetwork ids (`"IEEE 39 bus"`). Most CSV tools trim values by default or on
request (spreadsheets, database imports, R's `strip.white`), which turns
`"B101-G1 "` into `"B101-G1"`, an id that does not exist in the network.

**Correction.** Before the source is imported, every id is rewritten with this rule:

1. leading and trailing whitespace is removed;
2. whitespace next to a `-`, `_` or `+` separator is removed;
3. any remaining run of whitespace becomes `-`.

| Source id                           | Test-case id                      |
|-------------------------------------|-----------------------------------|
| `"B101-G1 "`                        | `B101-G1`                         |
| `"L-26-27-1 "`                      | `L-26-27-1`                       |
| `"B4-SH 1"`                         | `B4-SH-1`                         |
| `"IEEE 39 bus"`                     | `IEEE-39-bus`                     |
| `"Default+IEEE 14 bus+IEEE 39 bus"` | `Default+IEEE-14-bus+IEEE-39-bus` |

The same rule applies to the CGMES ids the source keeps as aliases and properties
(for example `"B101-G1 _GU"` → `B101-G1_GU`). Element names only lose their leading
and trailing whitespace. pypowsybl cannot change an id once a network is loaded, so
the correction rewrites the XIIDM text before the import. The build stops if the
number of changed ids is not 132 or if two ids would become the same.

**Effect.** Only ids change: every value of the network and every load-flow result
is identical. The ids in `data/inputs/` and `testcase/` are the new ones, and CGMES
UUIDs, derived from the ids, change accordingly. The PowerFactory model keeps the
source names; applying the rule above to them gives the ids of the other formats.

### MC-5 — Geographical coordinates added

**Finding.** The source model has no geographical data.

**Correction.** Every substation gets the coordinates (WGS84) of
`data/inputs/network/tx-full_substation_coordinates.csv` as the IIDM
`substationPosition` extension: IEEE 14 in south-east England, the three IEEE 39
zones in northern France (Z1), Belgium (Z2) and the Netherlands (Z3). The
coordinates are illustrative, not real substation sites. The build stops if a
substation is missing, unknown or listed twice, or if a coordinate is out of range.

**Effect.** Load-flow results are unchanged. The CGMES export has no geographical
profile and the PowerFactory model is shipped as received, so neither holds the
coordinates; `testcase/tx-full/network/bus_coordinates.csv` gives them for every bus.

### Alignment with the PowerFactory model (MC-6 to MC-10)

The XIIDM source and UCY's PowerFactory model (`TestCase.pfd`, the master model used
by Tool#9) describe the same system but differ in element data. The PowerFactory model
is the reference: MC-6 to MC-10 bring the XIIDM data in line with it, as read from its
DGS export `data/sources/tx-full/TestCase.dgs`. Ids are kept; each value is declared
in `data/inputs/network/` with the PowerFactory element it comes from. Per-unit values
are compared on 100 MVA and the nominal voltage of each model.

### MC-6 — Generator data from the PowerFactory model

**Finding.** The source generators have placeholder ratings (no rated power), wide
reactive limits (−500…800 Mvar for most IEEE 39 units) and four voltage set points
that differ from the PowerFactory model (B36 1.0635 instead of 1.05, B102 1.045
instead of 1.05, B106 1.07 instead of 1.02, B108 1.09 instead of 1.04). B101-G1 does
not regulate voltage (reactive range 0…0 Mvar), whereas PowerFactory holds its
terminal at 1.06 p.u.

**Correction.** `data/inputs/network/tx-full_generator_data.csv` sets, for all 15
units, the rated power S_n of the PowerFactory machine type, the reactive limits of
the PowerFactory machine (converted from p.u. of S_n to Mvar) and its voltage set
point. B101-G1 regulates its voltage at 1.06 p.u. within −179…336 Mvar.

**Effect.** S1 voltages now lie within 0.98–1.06 p.u. (up to 1.09 before). The small
reactive ranges of the IEEE 14 units (B103-G1 0…16 Mvar, B106-G1 and B108-G1
−1.5…6 Mvar) make them reach their limits in several states.

### MC-7 — Transformer impedances and ratio from the PowerFactory model

**Finding.** The IEEE 39 transformers of the source carry the impedances of the IEEE 39
data set. The PowerFactory transformer types give other values: their ratings are
900, 500 or 1000 MVA, and their short-circuit voltage and copper losses lead to
reactances 40 % lower to 11 % higher. `T-20-34-1` is two units in parallel in
PowerFactory. The IEEE 14 transformers `T-104-107-1` and `T-104-109-1` have twice the
source reactance (short-circuit voltage given on 50 MVA). `T-31-6-1` has an 8-step
tap changer fixed at ρ = 1.1667, where both IEEE 39 and PowerFactory use 1.07.

**Correction.** `data/inputs/network/tx-full_transformer_data.csv` gives the
nameplate data of every transformer (rating, short-circuit voltage, copper losses,
units in parallel), from which the build derives r and x as PowerFactory does, and
sets the rating. In `tx-full_corrections.yaml`, `tap_ratios` replaces the tap changer
of `T-31-6-1` by a fixed ratio of 1.07.

**Effect.** The IEEE 39 transformer impedances differ from the IEEE 39 data set, as in
the PowerFactory model. The lower ratio of `T-31-6-1` lowers the reactive power
injected towards bus 6.

### MC-8 — Second circuit of IEEE 14 line 1-2

**Finding.** IEEE 14 line 1-2 is a double circuit in the PowerFactory model, each
circuit with the impedance of the source line `L-101-102-1`.

**Correction.** `parallel_lines` in `tx-full_corrections.yaml` adds `L-101-102-2`, a
copy of `L-101-102-1`. A second line, rather than one line with halved impedance,
keeps one IIDM line per PowerFactory line. Its current limit is declared with the
others (MC-2).

**Effect.** The impedance between buses 101 and 102 is halved and the line is no
longer the most loaded IEEE 14 branch.

### MC-9 — Loads at buses 1, 16 and 20 from the PowerFactory model

**Finding.** Three loads differ: bus 1 is empty in the source and has 97.6 MW /
44.2 Mvar in PowerFactory, bus 16 has 329.4 MW instead of 329.0 MW and bus 20 680 MW
instead of 628 MW. Both models mix two versions of the IEEE 39 data set. In total,
IEEE 39 consumes 45.2 MW more in PowerFactory.

**Correction.** `data/inputs/network/tx-full_load_data.csv` sets the three loads of
the base case to the PowerFactory values. The scenario loads of
`data/inputs/scenarios/load_scenarios.csv` apply the scenario factors to them.

**Effect.** IEEE 39 consumption rises by 45.2 MW, in zones Z1 and Z2.

### MC-10 — HVDC data and converter control from the PowerFactory model

**Finding.** The source HVDC line has a nominal voltage of 150 kV and a resistance of
5 Ω, i.e. 0.56 MW of losses at 50 MW. PowerFactory models a symmetric monopole at
±320 kV with 2 × 150 km of cable at 0.01 Ω/km (3.0 Ω loop). Both source converter
stations regulate their AC voltage with unlimited reactive power: `VSC_Station_16`
absorbs up to 666 Mvar to hold bus 16 at 1.0 p.u. In PowerFactory, converter 1
(bus 16) controls the DC voltage at zero reactive power and converter 2 (bus 113)
controls its AC voltage at 1.01 p.u.

**Correction.** `hvdc` in `tx-full_corrections.yaml` sets the line to 320 kV and
0.75 Ω (the 3.0 Ω loop seen from one pole). `VSC_Station_16` stops regulating and
runs at 0 Mvar; `VSC_Station_113` regulates bus 113 at 1.01 p.u. Since the converter
transformers are not modelled, the set point applies at bus 113 rather than at the
converter terminal. The PowerFactory export has no converter reactive limits: both
stations get ±25 Mvar, i.e. ±0.5 p.u. of a 50 MW rating. The maximum active power
stays 60 MW.

**Effect.** HVDC losses fall to 0.02 MW at 50 MW. Bus 16 is no longer held at 1.0 p.u.
by the converter.

## Remarks passed on to the model provider

Not corrected, as they are modelling choices rather than errors:

- The shunts `B4-SH-1` and `B5-SH-1` (100 and 200 Mvar at nominal voltage, IEEE 39
  buses 4 and 5) are not part of the original IEEE 39 data set.
- Generator `B31-G1` regulates the voltage of load `B31-L1` remotely.
