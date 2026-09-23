# HYNET Task 3.2 reference test case

Common reference test case of HYNET Task 3.2, shared by the grid-analysis tools of
ART, SGI, UCY and INESC. It is used to validate tool behaviour before the
demonstrations, to compare similar tools and to investigate tool complementarity on
a shared, citable dataset.

> **Status:** work in progress. The dataset is not released yet; ids, layout and
> values may still change.

## Content

| Variant      | Content                                                                 |
|--------------|-------------------------------------------------------------------------|
| `tx-full`    | IEEE 39-bus + 50 MW HVDC link + IEEE 14-bus                             |
| `tx-reduced` | IEEE 39-bus reduced to 3 equivalent nodes + detailed IEEE 14-bus + HVDC |
| `dx-33`      | Modified IEEE 33-bus hybrid AC/DC distribution system                   |

The transmission variants come with three operating scenarios (base case, high
RES with low demand, low RES with high demand), bidding zones, economic
assumptions, a contingency list and storage data for adequacy studies.

## Quick start

The project uses [uv](https://docs.astral.sh/uv/) and Python 3.14.

```sh
uv sync                     # build tooling only
uv sync --group notebooks   # also JupyterLab and the notebook dependencies
```

## Licences

- Code (`src/`, `notebooks/`, `binder/` and project configuration): [MIT](LICENSE).
- Data and documentation (`data/`, `testcase/` and `docs/`):
  [CC-BY-4.0](LICENSE-DATA).

When you reuse the dataset, credit it as "HYNET Task 3.2 reference test case" and
cite the tagged version you used (see [CITATION.cff](CITATION.cff)).

## Acknowledgement

<img src="docs/assets/eu-emblem.svg" alt="Flag of the European Union" height="48">

HYNET project has received funding from the European Union's Horizon Europe research
and innovation programme under Grant Agreement No 101172757.
