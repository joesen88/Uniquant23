# UNIQUANT – Formalized Proofs in Lean 4

Machine-verified formalizations of the core theorems, exact rational arithmetic bounds,
and observer-geometry propositions from the UNIQUANT working papers (J. C. Anders, 2026).

## Verified Modules

- `UniquantProofs/TimeCore.lean`: Quantum unit `q = 75/1012 s`, bounded window rounding error (`< 1 q`, Prop. 1.1 & Theorem 3), 529-year anchor period (Theorem 1), and mod-23 residue stepping (Theorem 2).
- `UniquantProofs/LunarAxis.lean`: Lunar parabola `ν(x)` on the `L = 1,165,824 joe` grid, `29` or `30 q` step bounds per `joe`, and integer lunation bounds (`34,427,469 + 0..4 q`, Prop. 2).
- `UniquantProofs/PhaseClasses.lean`: `13/23` phase lattice on denominator `299` and exact vanishing of the `k = 299` cosine mode across all bin widths `r/299` (Prop. 2.1).
- `UniquantProofs/ObserverGeometry.lean`: Exact `HasDerivAt` second-derivative proof of zero-point apparent acceleration `-2κv² / (1 + κr)³` (Prop. 4.1), relative trajectory ambiguity, central-ray nonuniqueness (Prop. 5.1), and origin-shift amplitude invariance.
- `UniquantProofs/ReferenceTriad.lean`: Orthonormality of the invariable-plane / CMB-dipole triad `(e₁, e₂, e₃)` and uniqueness of the triple-anchor closure condition `T_AB ∘ T_BC ∘ T_CA = id`.
- `UniquantProofs/ResearchBridges.lean`: Predicate transport (Prop. 3.2), bit-encoding lower bound `n ≤ b` (Prop. 9.1), reflection-symmetry counterexample `F(1-s) = F(s)` (Prop. 10.1), and `TargetBridge` architecture.

## Build & Verify

```bash
lake exe cache get
lake build
```
