import Mathlib.Analysis.Calculus.Deriv.Basic
import Mathlib.Analysis.Calculus.Deriv.Add
import Mathlib.Analysis.Calculus.Deriv.Mul
import Mathlib.Analysis.Calculus.Deriv.Inv
import Mathlib.Analysis.Calculus.Deriv.Pow
import Mathlib.Tactic
set_option linter.style.header false
namespace Uniquant.ObserverGeometry
noncomputable section

lemma deriv_lin (r₀ v t : ℝ) : HasDerivAt (fun s => r₀ + v * s) v t := by
  have h := (hasDerivAt_const t r₀).add ((hasDerivAt_id t).const_mul v)
  rw [zero_add, mul_one] at h; exact h

lemma deriv_denom (r₀ v κ t : ℝ) : HasDerivAt (fun s => 1 + κ * (r₀ + v * s)) (κ * v) t := by
  have h := (hasDerivAt_const t (1 : ℝ)).add ((deriv_lin r₀ v t).const_mul κ)
  rw [zero_add] at h; exact h

theorem prop_4_1_vel (r₀ v κ t : ℝ) (hd : 1 + κ * (r₀ + v * t) ≠ 0) :
    HasDerivAt (fun s => (r₀ + v * s) / (1 + κ * (r₀ + v * s)))
      (v / (1 + κ * (r₀ + v * t)) ^ 2) t := by
  convert (deriv_lin r₀ v t).div (deriv_denom r₀ v κ t) hd using 1; field_simp [hd]; ring

theorem prop_4_1_acc (r₀ v κ t : ℝ) (hd : 1 + κ * (r₀ + v * t) ≠ 0) :
    HasDerivAt (fun s => v / (1 + κ * (r₀ + v * s)) ^ 2)
      (-2 * κ * v ^ 2 / (1 + κ * (r₀ + v * t)) ^ 3) t := by
  have h3 : HasDerivAt (fun s => (1 + κ * (r₀ + v * s)) ^ 2)
      (2 * (1 + κ * (r₀ + v * t)) * (κ * v)) t := by
    convert (deriv_denom r₀ v κ t).pow 2 using 1; norm_num
  convert (hasDerivAt_const t v).div h3 (pow_ne_zero 2 hd) using 1; field_simp [hd]; ring

theorem rel_ambiguity (x b h : ℝ → ℝ) :
    (fun t => (x t + h t) - (b t + h t)) = (fun t => x t - b t) := by ext t; ring

theorem central_ray_nonuniq (μ₀ R : ℝ) :
    2 * μ₀ * R = 2 * ((1.5 * μ₀) * (R / 2) + (0.5 * μ₀) * (R - R / 2)) := by ring

theorem origin_shift_inv (a b δ : ℝ) :
    (a * Real.cos δ + b * Real.sin δ) ^ 2 + (-a * Real.sin δ + b * Real.cos δ) ^ 2 =
      a ^ 2 + b ^ 2 := by
  calc _ = (a ^ 2 + b ^ 2) * (Real.sin δ ^ 2 + Real.cos δ ^ 2) := by ring
       _ = a ^ 2 + b ^ 2 := by rw [Real.sin_sq_add_cos_sq]; ring

end
end Uniquant.ObserverGeometry
