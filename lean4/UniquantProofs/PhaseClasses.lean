import Mathlib.Analysis.SpecialFunctions.Trigonometric.Deriv
import Mathlib.MeasureTheory.Integral.IntervalIntegral.FundThmCalculus
import Mathlib.Tactic
set_option linter.style.header false
namespace Uniquant.PhaseClasses

open Real intervalIntegral

lemma grid_13_on_299 (j : ℤ) : (j : ℝ) / 13 = ((23 * j : ℤ) : ℝ) / 299 := by
  push_cast; ring

lemma grid_23_on_299 (l : ℤ) : (l : ℝ) / 23 = ((13 * l : ℤ) : ℝ) / 299 := by
  push_cast; ring

lemma sin_add_int_two_pi (x : ℝ) (r : ℤ) :
    Real.sin (x + (r : ℝ) * (2 * Real.pi)) = Real.sin x := by
  simpa [mul_comm] using Real.sin_add_int_mul_two_pi x r

theorem proposition_2_1_invisible_mode (a : ℝ) (r : ℤ) :
    ∫ x in a..(a + (r : ℝ) / 299), Real.cos (2 * Real.pi * 299 * x) = 0 := by
  let c : ℝ := 2 * Real.pi * 299
  let F : ℝ → ℝ := fun x => Real.sin (c * x) / c
  have hF : ∀ x ∈ Set.uIcc a (a + (r : ℝ) / 299),
      HasDerivAt F (Real.cos (c * x)) x := by
    intro x _
    have h1 : HasDerivAt (fun t : ℝ => c * t) c x := by
      have hid : HasDerivAt (fun t : ℝ => t) 1 x := hasDerivAt_id x
      have hmul := hid.const_mul c
      rw [mul_one] at hmul
      exact hmul
    have h2 : HasDerivAt (fun t : ℝ => Real.sin (c * t)) (Real.cos (c * x) * c) x :=
      (Real.hasDerivAt_sin (c * x)).comp x h1
    have h3 := h2.div_const c
    have hc : c ≠ 0 := by unfold c; positivity
    rw [mul_div_cancel_right₀ _ hc] at h3
    exact h3
  rw [integral_eq_sub_of_hasDerivAt hF (Continuous.intervalIntegrable (by continuity) _ _)]
  dsimp only [F, c]
  have harg : 2 * Real.pi * 299 * (a + (r : ℝ) / 299) =
      2 * Real.pi * 299 * a + (r : ℝ) * (2 * Real.pi) := by ring
  rw [harg, sin_add_int_two_pi, sub_self]

end Uniquant.PhaseClasses
