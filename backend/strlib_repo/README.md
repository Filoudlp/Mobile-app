# README.md

```markdown
<div align="center">

# 🏗️ StructLib

**Python library for structural engineering calculations according to Eurocodes**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

*Automate your code compliance checks with traceable results, explicit formulas and ready-to-use reports.*

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [The 3 Core Classes](#-the-3-core-classes)
- [Supported Eurocodes](#-supported-eurocodes)
- [Reporting System](#-reporting-system)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**StructLib** is a Python library designed by and for structural engineers. It implements common Eurocode verifications with a clear philosophy:

> Every result must be **traceable**, every formula must be **explicit**, every check must be **referenced**.

Whether you want to quickly check a section in tension, design a bolted connection or produce a complete calculation note, StructLib has you covered.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧮 **Quick calculations** | Standalone functions for single-line verifications |
| 🏛️ **Detailed calculations** | Full classes with access to every intermediate step |
| 📄 **Traceable reports** | `FormulaResult` and `FormulaCollection` for standardised outputs |
| 🔗 **Explicit formulas** | Every result displays its literal formula, numerical values and Eurocode reference |
| 🧱 **Modular** | Materials, sections and calculations are decoupled and reusable |
| 🐍 **Pythonic** | `@property`, type hints, `__repr__`, flexible kwargs |

---

## 🏗 Architecture **Will be modified**

**NIY = Not Implemented Yet**
```
structlib/
│
├── core/                           # Core classes
│   ├── mat/                        # Material — mechanical properties
│   │   ├── materials.py            # Abstract Material — mechanical properties                       
│   │   ├── mat_concrete.py         # Material — concrete mechanical properties
│   │   ├── mat_reinforcement.py    # Material — reinforced concrete mechanical properties
│   │   ├── mat_steel.py            # Material — steel mechanical properties
│   │   └── mat_bolt.py             # Material — bolt mechanical properties
│   ├── section/                    # Section — geometric properties
│   │   ├── rectangle.py            # Section — rectangular geometric properties
│   │   ├── cercle.py               # **NIY** — Section — circular geometric properties
│   │   ├── ihu.py                  # **NIY** — Section — triangular geometric properties
│   │   ├── chs_rhs_shs.py          # **NIY** — Section — triangular geometric properties
│   │   └── triangle.py             # **NIY** — Section — triangular geometric properties
│   └── section_material/           # SectionMaterial — coupled properties
│       ├── reinforce_concrete.py   # SectionMaterial — reinforced concrete coupled properties
│       ├── steel.py                # **NIY** — SectionMaterial — steel coupled properties
│       └── bolt.py                 # **NIY** — SectionMaterial — bolt coupled properties
│
├── formula/                        # Reporting system
│   ├── formula_result.py           # FormulaResult — single traceable result
│   └── formula_collection.py       # FormulaCollection — step grouping
│
├── ec2/                            # **NIY** Eurocode 2 — Reinforced concrete
│   ├── bending.py
│   ├── elu
│       ├── flexion.py                      # Flexion simple (Ned=0) & composée — §6.1
│       ├── effort_tranchant.py             # §6.2
│       ├── torsion.py                      # §6.3
│       ├── interaction_v_t.py              # §6.3.2
│       ├── poinconnement.py                # §6.4
│       ├── compression.py                  # Compression simple — §6.1
│       ├── flambement.py                   # §5.8 (courbure + raideur + classif)
│       └── bielles_tirants.py   
│   ├── els
│       ├── contrainte.py
│       ├── fissuration.py
│       └── fleche.py
│   ├── durability
│   ├── dispositions
│   ├── feu
│
├── ec3/                            # Eurocode 3 — Steel structures
│   ├── ELU                         # All formula regarding ELU
│       ├── bending.py              # Eurocode 3 — simple bending & bi-axial bending without normal force
│       ├── compression.py          # Eurocode 3 — compression without buckling
│       ├── combined.py             # Eurocode 3 — bending + shear + normal
│       ├── shear.py                # Eurocode 3 — Shear
│       └── traction.py             # Eurocode 3 — traction
│   ├── ELS                         # All formula regarding ELS
│       ├── defelection.py          # Eurocode 3 — verticale delection of a section
│       ├── drift.py                # Eurocode 3 — horizontal deflection of a section
│       ├── limit.py                # Eurocode 3 — deflection limit & vibration limite
│       ├── vibration.py            # Eurocode 3 — vibration of steel
│   ├── buckling
│   ├── element
│
├── ec4/                            # Eurocode 4 — Composite structures
│   └── ...
│
├── ec5/                            # Eurocode 5 — Timber structures
│   └── ...
│
├── ec8/                            # Eurocode 8 — Seismic design
│   └── ...
│
└── utils/                          # Utilities
    ├── units.py
    └── helpers.py
```

---

## ⚙️ Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/structlib.git
cd structlib

# Install in development mode
pip install -e .
```

> **Requirements**: Python ≥ 3.10

---

## 🚀 Quick Start

### Quick calculation (one line)

```python
from structlib.ec3.tension import nt_rd

# Nt,Rd for an IPE 300, S235
resistance = nt_rd(A=5381, fy=235, Anet=4800, fu=360)
print(f"Nt,Rd = {resistance:.0f} N")
```

### Detailed calculation with report

```python
from structlib.ec3.tension import Tension

# Problem definition
verif = Tension(
    Ned=250_000,        # Tensile force [N]
    A=5381,             # Gross cross-section area [mm²]
    fy=235,             # Yield strength [MPa]
    fu=360,             # Ultimate strength [MPa]
    Anet=4800,          # Net cross-section area [mm²]
)

# Results
print(f"Npl,Rd  = {verif.npl_rd:.0f} N")
print(f"Nu,Rd   = {verif.nu_rd:.0f} N")
print(f"Nt,Rd   = {verif.nt_rd:.0f} N")
print(f"Ratio   = {verif.verif:.2%}")
print(f"Verified = {verif.is_ok}")
```

### Using Material and Section classes

```python
from structlib.core import Material, Section
from structlib.ec3.tension import Tension

steel = Material(fy=235, fu=360, gamma_m0=1.0, gamma_m2=1.25)
ipe300 = Section(A=5381, Anet=4800)

verif = Tension(Ned=250_000, mat=steel, sec=ipe300)

# Generate full report
report = verif.report(with_values=True)
print(report)
```

**Output:**
```
══════════════════════════════════════════════════
  Tension check
  Ref. : EC3-1-1 — §6.2.3
══════════════════════════════════════════════════

  Npl,Rd = A · fy / γM0
  Npl,Rd = 5381.00 × 235.00 / 1.0 = 1264535.00 N
  ► Npl,Rd = 1264535.00 N          [EC3-1-1 — §6.2.3 (2)a]

  Nu,Rd = 0.9 · Anet · fu / γM2
  Nu,Rd = 0.9 × 4800.00 × 360.00 / 1.25 = 1244160.00 N
  ► Nu,Rd = 1244160.00 N           [EC3-1-1 — §6.2.3 (2)b]

  Nt,Rd = min(Npl,Rd ; Nu,Rd)
  Nt,Rd = min(1264535.00 ; 1244160.00) = 1244160.00 N
  ► Nt,Rd = 1244160.00 N           [EC3-1-1 — §6.2.3 (2)]

  Ned / Nt,Rd ≤ 1.0
  Ned / Nt,Rd = 250000.00 / 1244160.00 = 0.2010 ≤ 1.0 → OK ✓
  ► Ned/Nt,Rd = 0.2010              [EC3-1-1 — §6.2.3 (1)]

══════════════════════════════════════════════════
```

---

## 🧱 The 3 Core Classes

### `Material` — Mechanical Properties

Encapsulates material characteristics independently of geometry.

```python
from structlib.core import Material

# Steel S355
steel = Material(fy=355, fu=510, E=210_000, gamma_m0=1.0, gamma_m2=1.25)

# Concrete C30/37
concrete = Material(fck=30, fctm=2.9, Ecm=33_000, gamma_c=1.5)
```

| Property | Description | Unit |
|---|---|---|
| `fy` | Yield strength | MPa |
| `fu` | Ultimate tensile strength | MPa |
| `fck` | Characteristic compressive strength (concrete) | MPa |
| `E` | Young's modulus | MPa |
| `gamma_m0` | Partial factor γ_M0 | — |
| `gamma_m2` | Partial factor γ_M2 | — |
| `gamma_c` | Partial factor γ_c (concrete) | — |

### `Section` — Geometric Properties

Describes the pure geometry of the cross-section.

```python
from structlib.core import Section

ipe300 = Section(
    A=5381,         # Gross area [mm²]
    Anet=4800,      # Net area [mm²]
    Iy=8356e4,      # Second moment of area — strong axis [mm⁴]
    Iz=604e4,       # Second moment of area — weak axis [mm⁴]
    Wply=628.4e3,   # Plastic section modulus y [mm³]
    Wplz=125.2e3,   # Plastic section modulus z [mm³]
)
```

### `SectionMaterial` — Coupled Properties

Contains properties that depend on both the **section** and the **material**.

```python
from structlib.core import SectionMaterial

# Reinforced concrete — effective depth, cover, etc.
sec_rc = SectionMaterial(
    d=267,          # Effective depth [mm]
    c_nom=30,       # Nominal cover [mm]
)

# Bolted connection — default edge distances, etc.
sec_bolt = SectionMaterial(
    e1=40,          # End distance (longitudinal) [mm]
    e2=30,          # Edge distance (transverse) [mm]
    p1=70,          # Bolt pitch (longitudinal) [mm]
)
```

---

## 📐 Supported Eurocodes

| Eurocode | Domain | Status |
|---|---|---|
| **EC2** | Reinforced and prestressed concrete | 🔲 In progress |
| **EC3** | Steel structures | 🔲 In progress |
| **EC4** | Composite steel-concrete structures | 🔲 Planned |
| **EC5** | Timber structures | 🔲 Planned |
| **EC8** | Seismic design | 🔲 Planned |

### EC3 — Module Details

| Module | Verification | Reference | Status |
|---|---|---|---|
| `tension.py` | Tension | §6.2.3 | ✅ |
| `compression.py` | Compression | §6.2.4 | 🔲 |
| `bending.py` | Bending | §6.2.5 | 🔲 |
| `shear.py` | Shear | §6.2.6 | 🔲 |
| `buckling.py` | Flexural buckling | §6.3.1 | 🔲 |
| `ltb.py` | Lateral-torsional buckling | §6.3.2 | 🔲 |
| `combined.py` | Combined actions | §6.3.3 | 🔲 |

---

## 📄 Reporting System

Every calculation produces `FormulaResult` objects that can be grouped into a `FormulaCollection`:

```python
# A single result
result = verif.get_npl_rd(with_values=True)
print(result.name)            # "Npl,Rd"
print(result.formula)         # "Npl,Rd = A · fy / γM0"
print(result.formula_values)  # "Npl,Rd = 5381.00 × 235.00 / 1.0 = 1264535.00 N"
print(result.result)          # 1264535.0
print(result.unit)            # "N"
print(result.ref)             # "EC3-1-1 — §6.2.3 (2)a"

# Full collection
report = verif.report(with_values=True)
# Exportable, iterable, printable
```

---

## 🤝 Contributing

Contributions are welcome! Here is how to get involved:

1. **Fork** the repository
2. **Create** a branch (`git checkout -b feature/ec3-buckling`)
3. **Code** following the existing class template
4. **Test** your calculations against reference examples
5. **Submit** a Pull Request

### Code Conventions

- Every verification class follows the **standardised template** (properties, `get_xxx`, `report`)
- Every formula is **referenced** (Eurocode article)
- Units are in **N, mm, MPa** (consistent system)
- Type hints are mandatory
- Docstrings in French

---

## 📜 License

This project is distributed under the **MIT** license. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ for the structural engineering community**

*If this project is useful to you, drop a ⭐ !*

</div>
```