#### UNIQUANT

*"What uniform and orderly motions must be assumed in order to account for the apparent motions of the planets?"* — Plato 

**Author:** J. C. Anders (2026)
**Research DOI:** 10.5281/zenodo.24570873
**Machine-Verified Lean 4 Proofs:** joesen88/UNIQUANT-Formal (40 verified modules, 0 sorry) 

#### Overview

**UNIQUANT** is an interdisciplinary research framework that reformulates physical, astronomical, climatic, and historical models using **exact rational and integer arithmetic** instead of floating-point approximations (float32 / float64). 

Standard floating-point simulations suffer from cumulative rounding errors, catastrophic cancellation, and hardware-dependent drift over long time horizons. UNIQUANT eliminates these issues by building time scales, geometric transformations, fluid solvers, and statistical diagnostics directly on exact discrete ratios. 

All core theorems, conservation laws, error bounds, and combinatorial results from this repository have been independently proven and verified by the **Lean 4** theorem prover in **joesen88/UNIQUANT-Formal**. 

#### Research Domains & Applications

DomainCore ConceptsPractical Applications
****Discrete Time & Astronomy****
Exact time quantum q = 75/1012 s, 529-year anchor cycle (23²), bounded lunar parabolas, 299 = 13 × 23 phase lattices, Base-23 arithmeticDrift-free ephemeris calculations, long-horizon calendar synchronization, mode/aliasing analysis, exact historical chronology
****Observer Geometry & Climate****
Apparent observer accelerations, three-anchor orthonormal reference triads, Coriolis/centrifugal drift, spatial correlation bias (N_eff), spectral-gap counterexamplesSeparating physical trends from coordinate-frame artifacts or station-network drift, multi-scale similarity modeling (23^k)
****Integer-First Hydrodynamics****
Exact integer volume ledgers, cancellation-free trapezoidal geometry, row-dominant tridiagonal M-matrix solvers, 128/256-bit arithmeticBit-identical simulations across Python, C++, and CUDA GPUs; strict mass/sediment conservation; certified L_infinity error bounds
****Optimization & Diagnostics****
Strictly convex Ridge-QP Hessians, linear L1 polytope bounds, root-free squared RMS guards, lossless gradient accumulationDrift-free parameter calibration without small-gradient underflow, online change-point detection (block-CUSUM)
****Stylometry & Decipherment****
Corpus-mean cancellation in Burrows' Delta, 820-state consonant coding, 365-day Egyptian calendar, minimal hitting sets, Shannon unicity distanceReference-invariant authorship attribution, rigorous hypothesis elimination for undeciphered scripts without post-hoc retuning

#### Repository Structure

* **Research Papers (.pdf):** Studies on quantized time (0-Uniquantsystem_Paper_EN.pdf), three-anchor reference frames (Drei-Anker-Bezugssystem.pdf), observer drift (Drift_Bezugssysteme_*.pdf), climate station network errors (UNIQUANT_Temperaturaenderung_Stationsnetzfehler.pdf), planetary modes (uniquant_planetary_modes_visibility.pdf), and linear flow models.
* **Reference Implementations:** Python scripts for 23-base cycle arithmetic (zyklus23.py), numerical demonstrators (0Demnstrator/), and stylometric/hieroglyphic analysis (delta_hieroglyphen/).
* **Formal Verification (lean4/):** Lean 4 proof files (full 40-module suite available in joesen88/UNIQUANT-Formal).
