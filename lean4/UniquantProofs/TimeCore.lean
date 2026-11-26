import Mathlib.Data.Real.Basic
import Mathlib.Data.Int.ModEq
import Mathlib.Algebra.Order.Floor.Defs
import Mathlib.Tactic

namespace Uniquant.TimeCore

noncomputable section

def q : ℝ := 75 / 1012

lemma q_pos : 0 < q := by unfold q; norm_num

def addr (t : ℝ) : ℤ := ⌊t / q + 1 / 2⌋
def rem (t : ℝ) : ℝ := t / q - (addr t : ℝ)

lemma rem_bounds (t : ℝ) : -1 / 2 ≤ rem t ∧ rem t < 1 / 2 := by
  unfold rem addr
  have h1 : (⌊t / q + 1 / 2⌋ : ℝ) ≤ t / q + 1 / 2 := Int.floor_le _
  have h2 : t / q + 1 / 2 < (⌊t / q + 1 / 2⌋ : ℝ) + 1 := Int.lt_floor_add_one _
  constructor <;> linarith

theorem window_error_lt_one_q (t_m t_n : ℝ) :

    |q * ((addr t_m : ℝ) - (addr t_n : ℝ)) - (t_m - t_n)| < q := by
  have hq : q ≠ 0 := ne_of_gt q_pos
  have hm : q * (addr t_m : ℝ) - t_m = -q * rem t_m := by unfold rem; field_simp; ring
  have hn : q * (addr t_n : ℝ) - t_n = -q * rem t_n := by unfold rem; field_simp; ring
  have hdiff : q * ((addr t_m : ℝ) - (addr t_n : ℝ)) - (t_m - t_n) =
      q * (rem t_n - rem t_m) := by linarith
  rw [hdiff, abs_mul, abs_of_pos q_pos]
  obtain ⟨h1_n, h2_n⟩ := rem_bounds t_n
  obtain ⟨h1_m, h2_m⟩ := rem_bounds t_m
  have habs : |rem t_n - rem t_m| < 1 := by rw [abs_lt]; constructor <;> linarith
  nlinarith [q_pos]

end

def Y_anchor : ℤ := 425806080
def b_anchor : ℤ := 703993
def g_anchor : ℤ := -11
def d_anchor : ℤ := 529

def tau_rat (n : ℤ) : ℚ :=
  (Y_anchor * n : ℚ) + ((b_anchor * n + g_anchor * n ^ 2 : ℤ) : ℚ) / (d_anchor : ℚ)

theorem theorem_1_period_529 (n : ℤ) :
    tau_rat (n + 529) - tau_rat n =
      ((529 * Y_anchor + b_anchor + g_anchor * (2 * n + 529) : ℤ) : ℚ) := by
  unfold tau_rat Y_anchor b_anchor g_anchor d_anchor
  push_cast
  ring

theorem theorem_1_great_chart_zero (k : ℤ) :
    tau_rat (529 * k) =
      ((Y_anchor * (529 * k) + b_anchor * k + g_anchor * 529 * k ^ 2 : ℤ) : ℚ) := by
  unfold tau_rat Y_anchor b_anchor g_anchor d_anchor
  push_cast
  ring

theorem theorem_2_step_mod_23 (j : ℤ) : (b_anchor * j) ≡ (9 * j) [ZMOD 23] := by
  have hb : b_anchor ≡ 9 [ZMOD 23] := by decide
  exact hb.mul_right j

lemma coprime_step_23 : Nat.Coprime 9 23 := by decide

end Uniquant.TimeCore
