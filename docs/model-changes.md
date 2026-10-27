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
(66 branches) with the basis of each value:

| Branches                          | Count | Basis                                                                 |
|-----------------------------------|-------|-----------------------------------------------------------------------|
| IEEE 39 lines and transformers    | 41    | Rating `rateA` of the MATPOWER `case39` data set, converted at 345 kV |
| IEEE 39 line L-6-11               | 1     | `rateA` 480 MVA raised to 600 MVA: at 480 MVA, S1 would overload it   |
| IEEE 39 step-up transformers T-10-32, T-19-33, T-23-36, T-29-38 | 4 | Sized for their unit: P / 0.9, rounded up to the next 100 MVA. The units of this test case are larger than in the original data set, so its ratings (900–1200 MVA) are below the units' output. |
| IEEE 14 lines                     | 17    | 138 kV conductor classes of 400 or 600 A, the smallest keeping S1 at or below 80 % |
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

## Remarks passed on to the model provider

Not corrected, as they are modelling choices rather than errors:

- The shunts `B4-SH-1` and `B5-SH-1` (100 and 200 Mvar at nominal voltage, IEEE 39
  buses 4 and 5) are not part of the original IEEE 39 data set.
- The two VSC converter stations have no reactive power limits. `VSC_Station_16`
  regulates its bus voltage and supplies 326–666 Mvar in S1–S3.
- Generator `B31-G1` regulates the voltage of load `B31-L1` remotely.
