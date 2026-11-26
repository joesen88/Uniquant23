import Mathlib.Data.Real.Basic
import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Analysis.Calculus.Deriv.Mul
import Mathlib.Analysis.Calculus.Deriv.Inv
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic
import Mathlib.Tactic

namespace Uniquant.ObserverGeometry

noncomputable section

theorem prop_4_1_apparent_velocity (r₀ v κ t : ℝ)
    (h_denom : 1 + κ * (r₀ + v * t) ≠ 0) :
    HasDerivAt (fun s => (r₀ + v * s) / (1 + κ * (r₀ + v * s)))
      (v / (1 + κ * (r₀ + v * t)) ^ 2) t := by
  have h1 : HasDerivAt (fun s => r₀ + v * s) v t := by
    simpa using (hasDerivAt_const t r₀).add ((hasDerivAt_id t).const_mul v)
  have h2 : HasDerivAt (fun s => 1 + κ * (r₀ + v * s)) (κ * v) t := by
    simpa using (hasDerivAt_const t (1 : ℝ)).add (h1.const_mul κ)
  convert h1.div h2 h_denom using 1
  field_simp [h_denom]
  ring

theorem prop_4_1_apparent_acceleration (r₀ v κ t : ℝ)
    (h_denom : 1 + κ * (r₀ + v * t) ≠ 0) :
    HasDerivAt (fun s => v / (1 + κ * (r₀ + v * s)) ^ 2)
      (-2 * κ * v ^ 2 / (1 + κ * (r₀ + v * t)) ^ 3) t := by
  have h_lin : HasDerivAt (fun s => r₀ + v * s) v t := by
    simpa using (hasDerivAt_const t r₀).add ((hasDerivAt_id t).const_mul v)
  have h_base : HasDerivAt (fun s => 1 + κ * (r₀ + v * s)) (κ * v) t := by
    simpa using (hasDerivAt_const t (1 : ℝ)).add (h_lin.const_mul κ)
  have h_sq : HasDerivAt (fun s => (1 + κ * (r₀ + v * s)) ^ 2)
      (2 * (1 + κ * (r₀ + v * t)) * (κ * v)) t := by
    simpa using h_base.pow 2
  have h_sq_ne : (1 + κ * (r₀ + v * t)) ^ 2 ≠ 0 := pow_ne_zero 2 h_denom
  convert (hasDerivAt_const t v).div h_sq h_sq_ne using 1
  field_simp [h_denom]
  ring

theorem relative_position_ambiguity (x b h : ℝ → ℝ) :
    (fun t => (x t + h t) - (b t + h t)) = (fun t => x t - b t) := by
  ext t
  ring

theorem central_ray_nonuniqueness (μ₀ R : ℝ) :
    let tau_uniform := 2 * μ₀ * R
    let tau_layered := 2 * ((1.5 * μ₀) * (R / 2) + (0.5 * μ₀) * (R - R / 2))
    tau_uniform = tau_layered := by
  dsimp only
  ring

theorem origin_shift_amplitude_invariance (a b δ : ℝ) :
    let a' := a * Real.cos δ + b * Real.sin δ
    let b' := -a * Real.sin δ + b * Real.cos δ
    a' ^ 2 + b' ^ 2 = a ^ 2 + b ^ 2 := by
  dsimp only
  calc
    (a * Real.cos δ + b * Real.sin δ) ^ 2 + (-a * Real.sin δ + b * Real.cos δ) ^ 2
      = (a ^ 2 + b ^ 2) * (Real.sin δ ^ 2 + Real.cos δ ^ 2) := by ring
    _ = (a ^ 2 + b ^ 2) * 1 := by rw [Real.sin_sq_add_cos_sq]
    _ = a ^ 2 + b ^ 2 := by ring

end

end Uniquant.ObserverGeometry
