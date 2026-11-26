import Mathlib.Tactic
set_option linter.style.header false
namespace Uniquant.ResearchBridges

theorem prop_3_2 {X Z : Type*} (E : X → Z) (P : X → Prop) (Pt : Z → Prop)
    (he : ∀ x, P x ↔ Pt (E x)) (hh : ∀ z ∈ Set.range E, Pt z) : ∀ x, P x :=
  fun x => (he x).mpr (hh (E x) ⟨x, rfl⟩)

theorem prop_9_1 (n b : ℕ) (f : (Fin n → Bool) → (Fin b → Bool))
    (hf : Function.Injective f) : n ≤ b := by
  have hc := Fintype.card_le_of_injective f hf
  simp only [Fintype.card_fun, Fintype.card_bool, Fintype.card_fin] at hc
  exact (Nat.pow_le_pow_iff_right (by decide : 1 < 2)).mp hc

noncomputable def F_poly (s : ℂ) : ℂ := ((s - 1 / 4) ^ 2 + 1) * ((s - 3 / 4) ^ 2 + 1)

theorem prop_10_1_sym (s : ℂ) : F_poly (1 - s) = F_poly s := by unfold F_poly; ring

theorem prop_10_1_zero : F_poly (1 / 4 + Complex.I) = 0 ∧ (1 / 4 + Complex.I : ℂ).re ≠ 1 / 2 := by
  refine ⟨?_, by norm_num⟩
  unfold F_poly
  have h1 : ((1 / 4 + Complex.I : ℂ) - 1 / 4) ^ 2 + 1 = 0 := by
    calc ((1 / 4 + Complex.I : ℂ) - 1 / 4) ^ 2 + 1 = Complex.I ^ 2 + 1 := by ring
         _ = -1 + 1 := by rw [Complex.I_sq]
         _ = 0 := by norm_num
  rw [h1, zero_mul]

structure TargetBridge (U T : Type*) where
  encode : T → U
  target_prop : T → Prop
  uniquart_prop : U → Prop
  bridge : ∀ x, target_prop x ↔ uniquart_prop (encode x)

theorem resolve {U T : Type*} (B : TargetBridge U T)
    (hc : ∀ u ∈ Set.range B.encode, B.uniquart_prop u) : ∀ x, B.target_prop x :=
  prop_3_2 B.encode B.target_prop B.uniquart_prop B.bridge hc

end Uniquant.ResearchBridges
