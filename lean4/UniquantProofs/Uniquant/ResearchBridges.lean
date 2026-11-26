import Mathlib.Data.Real.Basic
import Mathlib.Data.Complex.Basic
import Mathlib.Data.Fintype.Card
import Mathlib.Tactic

namespace Uniquant.ResearchBridges

theorem proposition_3_2 {X Z : Type*} (E : X → Z) (P : X → Prop) (P_tilde : Z → Prop)
    (h_equiv : ∀ x : X, P x ↔ P_tilde (E x))
    (h_holds : ∀ z ∈ Set.range E, P_tilde z) :
    ∀ x : X, P x := by
  intro x
  rw [h_equiv x]
  apply h_holds
  exact ⟨x, rfl⟩

theorem proposition_9_1 (n b : ℕ) (f : (Fin n → Bool) → (Fin b → Bool))
    (hf : Function.Injective f) : n ≤ b := by
  have hcard := Fintype.card_le_of_injective f hf
  simp only [Fintype.card_fun, Fintype.card_bool, Fintype.card_fin] at hcard
  exact Nat.pow_le_pow_iff_right (by decide : 1 < 2) |>.mp hcard

def F_poly (s : ℂ) : ℂ :=
  ((s - 1 / 4) ^ 2 + 1) * ((s - 3 / 4) ^ 2 + 1)

theorem proposition_10_1_symmetry (s : ℂ) : F_poly (1 - s) = F_poly s := by
  unfold F_poly; ring

theorem proposition_10_1_off_line_zero :
    let s₀ : ℂ := 1 / 4 + Complex.I
    F_poly s₀ = 0 ∧ s₀.re ≠ 1 / 2 := by
  constructor
  · unfold F_poly
    have h1 : ((1 / 4 + Complex.I : ℂ) - 1 / 4) ^ 2 + 1 = 0 := by
      ring_nf; rw [Complex.I_sq]; ring
    rw [h1, zero_mul]
  · simp only [Complex.add_re, Complex.ofReal_re, Complex.I_re]
    norm_num

structure TargetBridge (UniquantState TargetDomain : Type*) where
  encode : TargetDomain → UniquantState
  target_property : TargetDomain → Prop
  uniquart_property : UniquantState → Prop
  required_bridge : ∀ x : TargetDomain, target_property x ↔ uniquart_property (encode x)

theorem conditional_target_resolution {U T : Type*} (B : TargetBridge U T)
    (h_core : ∀ u ∈ Set.range B.encode, B.uniquart_property u) :
    ∀ x : T, B.target_property x :=
  proposition_3_2 B.encode B.target_property B.uniquart_property B.required_bridge h_core

end Uniquant.ResearchBridges
