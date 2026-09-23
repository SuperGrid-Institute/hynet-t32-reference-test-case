# Provenance of the source models

Files in `data/sources/` are kept exactly as received. The build never modifies
them; every correction it applies is declared in `data/inputs/` and described in
[docs/model-changes.md](../../docs/model-changes.md).

## `tx-full/` — IEEE 39-bus + HVDC link + IEEE 14-bus

- **Provided by**: University of Cyprus (UCY), HYNET Task 3.2 partner, as its
  proposal for the common transmission test case.
- **Released under**: CC-BY-4.0, with UCY's agreement.
- **Derived from**: the public IEEE 39-bus (New England) and IEEE 14-bus benchmark
  systems, joined by a VSC HVDC link between IEEE 39 bus 16 and IEEE 14 bus 13
  (`HVDC_Link_16_113`, 50 MW set point, 60 MW maximum).
- **Exported**: 2025-11-26 (case date of the XIIDM and CGMES files).

| File                               | Format                      | Role in the build                     | SHA-256                                                            |
|------------------------------------|-----------------------------|---------------------------------------|--------------------------------------------------------------------|
| `TestCase.xiidm`                   | IIDM XML 1.13               | Source of `tx-full`                   | `7b4e0f1e89041e83185c3dd52ef49d4328f65d5c177d35548a136465c311a5f2` |
| `TestCase.pfd`                     | PowerFactory project export | Shipped unchanged (dynamic studies)   | `faeac3b824bac18662bca41603ffa0006a0ef21a510e13530f6f70e1809ec727` |
| `TestCase_CGMES/TestCase_EQ.xml`   | CGMES 2.4.15 EQ             | Kept for reference; not used          | `dd383967bd925def16b381c5937a6532d6675e7d18c4fc5ebe06615a9d885f00` |
| `TestCase_CGMES/TestCase_SSH.xml`  | CGMES 2.4.15 SSH            | Kept for reference; not used          | `d8cc1eec36996b2345142353fe303adc865e26b9a998d60758b52830d664d72e` |
| `TestCase_CGMES/TestCase_SV.xml`   | CGMES 2.4.15 SV             | Kept for reference; not used          | `6e7868c4cf550e99a9c322134e1b22a16caf6e3576d3037b66117133d63fe3f9` |
| `TestCase_CGMES/TestCase_TP.xml`   | CGMES 2.4.15 TP             | Kept for reference; not used          | `c1bae230b9c96eff013a1099a0f9805e08818e988726f1c1de5aaca775ec1a63` |

Known characteristics of the source, handled by the build:

- The IEEE 39 part is expressed in per unit on a 1 kV base: its 27 voltage levels
  have a nominal voltage of 1 kV and impedances are scaled accordingly. The IEEE 14
  part is at 138 kV.
- The model carries no thermal (operational) limits.
- Generator, load, line and transformer ids end with a space (for example
  `"B101-G1 "`). They are kept verbatim, since they are the ids of the model.

## `dx-33/` — modified IEEE 33-bus hybrid AC/DC distribution system

- **Provided by**: INESC, HYNET Task 3.2 partner.
- **Status**: not published. The files are excluded from the repository until INESC
  agrees to their release under CC-BY-4.0.

## Scenario inputs (`data/inputs/scenarios/`)

Synthetic operating points written for this test case by SuperGrid Institute
(generator types, nominal powers and marginal prices are illustrative, not taken
from any real system).
