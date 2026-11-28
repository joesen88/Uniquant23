#### UNIQUANT: Uniform and Orderly Motions, Exact Time Quantization & Discrete Scientific Computing

*"What uniform and orderly motions must be assumed in order to account for the apparent motions of the planets?"* — Plato 

* **Author:** J. C. Anders (2026)
* **Research DOI:** 10.5281/zenodo.24570873
* **Primary Research Repository:** [joesen88/Uniquant23](https://github.com/joesen88/Uniquant23)
* **Machine-Verified Proofs (Lean 4):** [joesen88/UNIQUANT-Formal](https://github.com/joesen88/UNIQUANT-Formal) (40 kernel-verified modules, 0 sorry)

#### Overview

**UNIQUANT** is an interdisciplinary research framework investigating how complex physical, astronomical, climatic, and historical systems can be formulated using **exact discrete ratios and integer arithmetic** rather than lossy floating-point approximations (float32/float64). 

Starting from classical astronomical periodicity and the geometry of observer reference frames, this repository brings together theoretical papers, analytical derivations, and reference implementations (zyklus23.py and related solvers). All core mathematical theorems, conservation laws, error bounds, and combinatorial structures developed across these works have been independently formalized and verified by the **Lean 4** mathematical kernel in the companion repository **[UNIQUANT-Formal](https://github.com/joesen88/UNIQUANT-Formal)**. 

#### Core Scientific Themes & Practical Applications

#### 1. Discrete Time Quantization & Astronomical Periodicity

* **What it covers:** Formulates time as an exact rational quantum (
𝑞

=751012

 s
⁠), derives multi-century anchor cycles (
529

=232
⁠ years), analyzes bounded lunar parabolas on 
𝐿

=1

,

165

,

824

 joe
⁠, constructs rational phase lattices (
299

=13

×23
⁠), and develops Base-23 positional arithmetic.
* **What it can be used for:** 

  * **Long-Horizon Ephemeris & Calendar Synchronization:** Performing multi-century astronomical and historical calendar calculations with zero cumulative floating-point drift.
  * **Mode & Aliasing Analysis:** Identifying exact rational frequencies that vanish identically across discrete observation grids.
  * **Exact Chronology Reconstruction:** Linking historical records and epoch offsets without index-shift errors.

#### 2. Observer Geometry, Reference Frames & Spectral Stability

* **What it covers:** Analyzes apparent accelerations arising from observer motion (

−2κv2(1+κr)3negative the fraction with numerator 2 kappa v squared and denominator open paren 1 plus kappa r close paren cubed end-fraction
−2𝜅𝑣2(1+𝜅𝑟)3
⁠), three-anchor orthonormal reference triads (invariable plane and CMB dipole), Coriolis and centrifugal drift terms in rotating frames, spatial correlation bias (

Neffcap N sub eff end-sub
𝑁eff
⁠) in climate station networks, and spectral-gap collapse counterexamples.
* **What it can be used for:** 

  * **Separating Signal from Observer Artifacts:** Distinguishing genuine physical trends from coordinate-frame drift or station-network bias in climate and geophysical datasets.
  * **Multi-Scale Similarity Modeling:** Preserving Reynolds-number and velocity invariants across discrete 

23k23 to the k-th power
23𝑘
⁠ scale ladders.
  * **Numerical Stability Diagnostics:** Detecting ill-conditioned operators where bounded amplitude hides unbounded gradient energy or collapsing spectral gaps.

#### 3. Integer-First Hydrodynamics & Bit-Exact Scientific Computing

* **What it covers:** Replaces floating-point fluid and transport solvers with exact integer volume ledgers, cancellation-free trapezoidal channel geometry, strictly row-dominant tridiagonal M-matrix integer solvers, and multi-limb fixed-point arithmetic (128/256-bit).
* **What it can be used for:** 

  * **Bit-Identical CPU & GPU Simulations:** Guaranteeing deterministic, bit-exact results across Python prototypes, C++ CPUs, and CUDA GPUs.
  * **Strict Mass & Sediment Conservation:** Eliminating artificial volume creation or loss over millions of simulation time steps in open-channel and river hydraulics.
  * **Certified Error Bounds:** Providing rigorous, machine-checkable 

ℓ∞ℓ raised to the infinity power
ℓ∞
⁠ coordinate error guarantees directly from integer residuals.

#### 4. Convex Optimization & Root-Free Numerical Diagnostics

* **What it covers:** Establishes strict convexity for Ridge Quadratic Programming Hessians, linear polytope reformulations for 

L1cap L to the first power
𝐿1
⁠ constraints, convex backtracking rules, root-free squared RMS gain guards, and lossless main/remainder parameter accumulation.
* **What it can be used for:** 

  * **Drift-Free Parameter Calibration:** Running inverse models and constrained optimization without catastrophic cancellation or small-gradient underflow.
  * **Online Change-Point Detection:** Tracking regime shifts and phase delays in noisy time series using exact integer block-CUSUM diagnostics.

#### 5. Stylometry, Historical Calendars & Information-Theoretic Decipherment

* **What it covers:** Proves exact corpus-mean cancellation in Burrows' Delta 

zz
𝑧
⁠-score metrics, constructs combinatorial consonant-sequence coding spaces, formalizes ancient Egyptian 

365365
365
⁠-day calendar and synodic beat-period identities, and applies minimal hitting sets and Shannon's unicity distance (
𝑈

=𝐻

(

𝐾

)

/𝐷
⁠) to undeciphered scripts.
* **What it can be used for:** 

  * **Robust Stylometric Attribution:** Comparing textual corpora independently of reference-mean shifts.
  * **Rigorous Hypothesis Elimination:** Determining the minimum set of blind empirical tests required to refute competing decipherment hypotheses without post-hoc retuning.

#### Repository Contents

* **Theoretical Papers & PDFs:** Foundational studies on quantized time (0-Uniquantsystem_Paper_EN.pdf), three-anchor reference frames (Drei-Anker-Bezugssystem.pdf), observer-frame drift (Drift_Bezugssysteme_*.pdf), climate network error bounds (UNIQUANT_Temperaturaenderung_Stationsnetzfehler.pdf), planetary modes (uniquant_planetary_modes_visibility.pdf), and linear flow formulas.
* **Reference Code (zyklus23.py, 0Demnstrator/, delta_hieroglyphen/):** Executable Python implementations of the 23-base cycle arithmetic, numerical demonstrations, and stylometric/hieroglyphic analysis tools.
* **Formal Verification (lean4/ & [UNIQUANT-Formal](https://github.com/joesen88/UNIQUANT-Formal)):** Complete machine-verified Lean 4 proof suite confirming the mathematical soundness of all core equations and algorithms.
