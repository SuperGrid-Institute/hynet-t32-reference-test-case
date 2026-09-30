# HYNET Task 3.2 reference test case

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/SuperGrid-Institute/hynet-t32-reference-test-case/main?labpath=notebooks%2Fpresentation.ipynb)

Common reference test case of HYNET Task 3.2, shared by the grid-analysis tools of
ART, SGI and UCY. It is used to validate tool behaviour before the
demonstrations, to compare similar tools and to investigate tool complementarity on
a shared, citable dataset.

> **Status:** work in progress. The dataset is not released yet; ids, layout and
> values may still change.

## The test case

`tx-full` is the IEEE 39-bus system (345 kV) and the IEEE 14-bus system (138 kV),
joined by a 60 MW VSC HVDC link. It comes with:

- two network cases: `base`, and `reinforced` with a second circuit parallel to line
  L-26-27;
- three operating scenarios: S1 base case, S2 high renewables and low demand, S3 low
  renewables and high demand;
- four bidding zones, two batteries, economic assumptions and a list of eight
  contingencies.

A reduced variant, `tx-reduced`, is planned.

## Content

| Path                                                               | Content                                                                        |
|--------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`testcase/tx-full/`](testcase/tx-full)                            | Network models (XIIDM, CGMES 2.4.15, PowerFactory) and CSV data                |
| [`docs/test-case.md`](docs/test-case.md)                           | What the test case contains, how it is built and how to use it                 |
| [`docs/data-dictionary.md`](docs/data-dictionary.md)               | Schema of every CSV file                                                       |
| [`docs/scenarios_presentation.pptx`](docs/scenarios_presentation.pptx) | Slides introducing the scenarios                                           |
| [`notebooks/presentation.ipynb`](notebooks/presentation.ipynb)     | Guided tour of the test case: network, zones, scenarios, loadings, contingencies |
| [`CHANGELOG.md`](CHANGELOG.md)                                     | Changes between versions                                                       |

## Getting started

Download the repository (**Code → Download ZIP**) or clone it. Every file of the test
case is in `testcase/tx-full/`; the XIIDM files load directly in
[pypowsybl](https://pypowsybl.readthedocs.io):

```python
import pypowsybl as pp

network = pp.network.load("testcase/tx-full/network/base/xiidm/tx-full_base.xiidm")
```

The presentation notebook is readable on GitHub with its outputs. The Binder badge
above runs it in the browser, with an interactive network explorer, without
installing anything. Its load flows are computed live with pypowsybl to illustrate
the operating points; they are not results of any HYNET tool.

## How it is built

This branch is generated; it is not edited by hand. It was published from commit
[`6845812`](https://github.com/SuperGrid-Institute/hynet-t32-reference-test-case/tree/6845812dbbb0b4f9f6988dc4170851ee58b3d202) of the `dev` branch, which holds the
source models, the hand-edited inputs and the code that builds `testcase/`. The
corrections applied to the source models are listed in
[`docs/model-changes.md`](https://github.com/SuperGrid-Institute/hynet-t32-reference-test-case/blob/6845812dbbb0b4f9f6988dc4170851ee58b3d202/docs/model-changes.md).

## Licences

- Notebook and Binder configuration (`notebooks/`, `binder/`): [MIT](LICENSE).
- Data and documentation (`testcase/` and `docs/`): [CC-BY-4.0](LICENSE-DATA).

When you reuse the dataset, credit it as "HYNET Task 3.2 reference test case" and
cite the tagged version you used (see [CITATION.cff](CITATION.cff)).

## Acknowledgement

<img src="docs/assets/eu-emblem.svg" alt="Flag of the European Union" height="48">

HYNET project has received funding from the European Union's Horizon Europe research
and innovation programme under Grant Agreement No 101172757.
