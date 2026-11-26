import Mathlib.Tactic
set_option linter.style.header false
namespace Uniquant.LunarAxis

def A_lunar : ℤ := 9634217446503
def G_lunar : ℤ := 32
def d_lunar : ℤ := 23 ^ 4
def L_joe : ℤ := 1165824

def nu_rat (x : ℚ) : ℚ :=
  ((A_lunar : ℚ) * x + (G_lunar : ℚ) * x ^ 2) / (d_lunar : ℚ)

theorem joe_step_exact (m : ℤ) :
    nu_rat ((m + 1 : ℚ) / L_joe) - nu_rat ((m : ℚ) / L_joe) =
      ((A_lunar : ℚ) * L_joe + (G_lunar : ℚ) * (2 * m + 1)) /
        ((d_lunar : ℚ) * (L_joe : ℚ) ^ 2) := by
  unfold nu_rat L_joe d_lunar; field_simp; ring

theorem joe_step_bounds (m : ℤ) (hm0 : 0 ≤ m) (hm1 : m ≤ 15000 * L_joe) :
    (29 : ℚ) < nu_rat ((m + 1 : ℚ) / L_joe) - nu_rat ((m : ℚ) / L_joe) ∧
    nu_rat ((m + 1 : ℚ) / L_joe) - nu_rat ((m : ℚ) / L_joe) < (30 : ℚ) := by
  rw [joe_step_exact]
  have h_int : 29 * (d_lunar * L_joe ^ 2) < A_lunar * L_joe + G_lunar * (2 * m + 1) ∧
               A_lunar * L_joe + G_lunar * (2 * m + 1) < 30 * (d_lunar * L_joe ^ 2) := by
    unfold A_lunar G_lunar d_lunar L_joe at *; constructor <;> linarith
  unfold d_lunar L_joe
  constructor
  · rw [lt_div_iff₀ (by positivity)]; exact_mod_cast h_int.1
  · rw [div_lt_iff₀ (by positivity)]; exact_mod_cast h_int.2

theorem lunation_step_exact (k : ℤ) :
    nu_rat (k + 1) - nu_rat k =
      ((A_lunar : ℚ) + (G_lunar : ℚ) * (2 * k + 1)) / (d_lunar : ℚ) := by
  unfold nu_rat; ring

theorem lunation_step_bounds (k : ℤ) (hk0 : 0 ≤ k) (hk1 : k ≤ 12000) :
    (34427469 : ℚ) < nu_rat (k + 1) - nu_rat k ∧
    nu_rat (k + 1) - nu_rat k < (34427473 : ℚ) := by
  rw [lunation_step_exact]
  have h_int : 34427469 * d_lunar < A_lunar + G_lunar * (2 * k + 1) ∧
               A_lunar + G_lunar * (2 * k + 1) < 34427473 * d_lunar := by
    unfold A_lunar G_lunar d_lunar at *; constructor <;> linarith
  unfold d_lunar
  constructor
  · rw [lt_div_iff₀ (by positivity)]; exact_mod_cast h_int.1
  · rw [div_lt_iff₀ (by positivity)]; exact_mod_cast h_int.2

end Uniquant.LunarAxis
