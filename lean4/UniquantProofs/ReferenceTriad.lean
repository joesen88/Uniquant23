import Mathlib.Data.Real.Basic
import Mathlib.Tactic

namespace Uniquant.ReferenceTriad

structure Vec3 where
  x : ℝ
  y : ℝ
  z : ℝ

def dot (u v : Vec3) : ℝ := u.x * v.x + u.y * v.y + u.z * v.z

def cross (u v : Vec3) : Vec3 :=
  ⟨u.y * v.z - u.z * v.y,
   u.z * v.x - u.x * v.z,
   u.x * v.y - u.y * v.x⟩

def sub (u v : Vec3) : Vec3 := ⟨u.x - v.x, u.y - v.y, u.z - v.z⟩
def smul (c : ℝ) (v : Vec3) : Vec3 := ⟨c * v.x, c * v.y, c * v.z⟩

theorem triad_e1_perp_e3 (C e₃ : Vec3) (he₃ : dot e₃ e₃ = 1) :
    let p := sub C (smul (dot C e₃) e₃)
    dot p e₃ = 0 := by
  dsimp only [sub, smul, dot] at *
  linear_combination -(C.x * e₃.x + C.y * e₃.y + C.z * e₃.z) * he₃

theorem triad_e2_perp_e3 (e₁ e₃ : Vec3) : dot (cross e₃ e₁) e₃ = 0 := by
  unfold dot cross; ring

theorem triad_e2_perp_e1 (e₁ e₃ : Vec3) : dot (cross e₃ e₁) e₁ = 0 := by
  unfold dot cross; ring

theorem anchor_closure_uniqueness {α : Type*} (T_AB T_BC T_CA : α → α)
    (h_close : ∀ x, T_AB (T_BC (T_CA x)) = x)
    (h_inj_AB : Function.Injective T_AB)
    (h_inj_BC : Function.Injective T_BC)
    (T_CA' : α → α)
    (h_close' : ∀ x, T_AB (T_BC (T_CA' x)) = x) :
    T_CA = T_CA' := by
  ext x
  apply h_inj_BC
  apply h_inj_AB
  rw [h_close x, h_close' x]

end Uniquant.ReferenceTriad
