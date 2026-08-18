#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Tests complets du module FEM
    
    Cas testés :
    ─────────────
    1. Poutre console (encastrement + force ponctuelle)
    2. Poutre bi-appuyée + charge répartie
    3. Portique simple (2 poteaux + 1 traverse)
    4. Poutre continue 3 travées
    5. Treillis triangulaire simple
    6. Vérification des réactions d'appui
    7. Vérification des efforts internes
    
    Résultats comparés aux solutions analytiques.
    
    Units : N, mm, rad
"""

import numpy as np
import sys

# ─── Import du module FEM ───
# Adapter le chemin si nécessaire
# sys.path.insert(0, "..")

from rdm import (
    Model,
    DistributedLoad,
    PointLoadOnBeam,
    MomentOnBeam,
)

# ─── Tolérance pour les comparaisons ───
TOL_FORCE = 1.0          # N
TOL_DISPLACEMENT = 0.01  # mm
TOL_MOMENT = 1.0         # N.mm
TOL_RATIO = 0.01         # 1%


def passed(name: str) -> None:
    print(f"  ✅ {name}")


def failed(name: str, expected, got) -> None:
    print(f"  ❌ {name} — attendu: {expected}, obtenu: {got}")


def check(name: str, value: float, expected: float, tol: float) -> bool:
    """Compare valeur obtenue vs attendue"""
    ok = abs(value - expected) <= tol or (
        expected != 0 and abs((value - expected) / expected) <= TOL_RATIO
    )
    if ok:
        passed(name)
    else:
        failed(name, f"{expected:.4f}", f"{value:.4f}")
    return ok


# ═══════════════════════════════════════════════════════════
#  TEST 1 — Poutre console (cantilever)
# ═══════════════════════════════════════════════════════════
def test_cantilever():
    """
        Poutre encastrée à gauche, force P à droite.
        
        ▓▓▓▓├────────────────────┤
                                 ↓ P
        
        Solution analytique :
            δ_max = P·L³ / (3·E·I)
            M_encastrement = -P·L
            R_y = P
    """
    print("\n═══ TEST 1 : Poutre console ═══")

    L = 6000.0      # mm
    P = 10000.0      # N
    E = 210000.0     # MPa
    I = 8.356e7      # mm⁴  (IPE 300)
    A = 5380.0       # mm²

    m = Model()
    n1 = m.add_node(0, 0, rx=True, ry=True, rz=True)   # Encastrement
    n2 = m.add_node(L, 0)                                # Libre
    b = m.add_element(n1, n2, E=E, A=A, I=I)

    # Charge ponctuelle en bout
    n2.set_forces(fy=-P)

    m.solve()

    # ── Solutions analytiques ──
    delta_ana = P * L**3 / (3 * E * I)       # flèche en bout
    M_enc = P * L                              # moment encastrement

    results_ok = True
    results_ok &= check("δ bout",       abs(n2.results.dy), delta_ana, TOL_DISPLACEMENT)
    results_ok &= check("Ry encastr.",  n1.results.ry,      P,         TOL_FORCE)
    results_ok &= check("Mz encastr.",  abs(n1.results.mz), M_enc,     TOL_MOMENT)

    return results_ok


# ═══════════════════════════════════════════════════════════
#  TEST 2 — Poutre bi-appuyée + charge répartie
# ═══════════════════════════════════════════════════════════
def test_simply_supported_udl():
    """
        Poutre sur 2 appuis, charge répartie uniforme q.
        
        △──────────────────────△
        ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓  q
        
        Solution analytique :
            δ_max = 5·q·L⁴ / (384·E·I)
            M_max = q·L² / 8
            R = q·L / 2
    """
    print("\n═══ TEST 2 : Bi-appuyée + charge répartie ═══")

    L = 8000.0       # mm
    q = 15.0         # N/mm
    E = 210000.0
    I = 8.356e7
    A = 5380.0

    m = Model()
    n1 = m.add_node(0, 0, rx=True, ry=True)     # Appui simple
    n2 = m.add_node(L/2, 0)                       # Mi-travée
    n3 = m.add_node(L, 0, ry=True)                # Appui rouleau

    b1 = m.add_element(n1, n2, E=E, A=A, I=I)
    b2 = m.add_element(n2, n3, E=E, A=A, I=I)

    b1.add_load(DistributedLoad(fy=-q))
    b2.add_load(DistributedLoad(fy=-q))

    m.solve()

    # ── Solutions analytiques ──
    delta_ana = 5 * q * L**4 / (384 * E * I)
    M_max = q * L**2 / 8
    R = q * L / 2

    results_ok = True
    results_ok &= check("δ mi-travée",  abs(n2.results.dy), delta_ana,  TOL_DISPLACEMENT)
    results_ok &= check("Ry gauche",    n1.results.ry,      R,          TOL_FORCE)
    results_ok &= check("Ry droite",    n3.results.ry,      R,          TOL_FORCE)

    return results_ok


# ═══════════════════════════════════════════════════════════
#  TEST 3 — Portique simple
# ═══════════════════════════════════════════════════════════
def test_portal_frame():
    """
        Portique simple — 2 poteaux encastrés + traverse.
        Charge horizontale en tête.
        
             F →  ┌────────────────┐
                  │                │
                  │                │
                  │                │
                  ▓▓              ▓▓
        
        Vérification : ΣFx = 0, ΣFy = 0, ΣM = 0
    """
    print("\n═══ TEST 3 : Portique simple ═══")

    H = 4000.0       # Hauteur poteaux
    L = 6000.0       # Portée traverse
    F = 50000.0      # Force horizontale
    E = 210000.0
    I = 8.356e7
    A = 5380.0

    m = Model()

    # Pieds encastrés
    n1 = m.add_node(0, 0, rx=True, ry=True, rz=True)
    n2 = m.add_node(L, 0, rx=True, ry=True, rz=True)

    # Têtes de poteaux
    n3 = m.add_node(0, H)
    n4 = m.add_node(L, H)

    # Poteaux
    m.add_element(n1, n3, E=E, A=A, I=I)
    m.add_element(n2, n4, E=E, A=A, I=I)

    # Traverse
    m.add_element(n3, n4, E=E, A=A, I=I)

    # Charge horizontale en tête gauche
    n3.set_forces(fx=F)

    m.solve()

    # ── Vérification équilibre global ──
    sum_rx = n1.results.rx + n2.results.rx
    sum_ry = n1.results.ry + n2.results.ry
    sum_forces_x = sum_rx + F
    sum_forces_y = sum_ry

    results_ok = True
    results_ok &= check("ΣFx = 0",  abs(sum_forces_x), 0.0, TOL_FORCE)
    results_ok &= check("ΣFy = 0",  abs(sum_forces_y), 0.0, TOL_FORCE)

    # Vérification que les déplacements en tête sont non nuls et cohérents
    results_ok &= check("dx tête > 0", float(n3.results.dx > 0), 1.0, 0)
    results_ok &= check("dx symétrie", 
                         abs(n3.results.dx - n4.results.dx) / max(abs(n3.results.dx), 1e-10),
                         0.0, 0.05)

    return results_ok


# ═══════════════════════════════════════════════════════════
#  TEST 4 — Poutre continue 3 travées
# ═══════════════════════════════════════════════════════════
def test_continuous_beam():
    """
        Poutre continue sur 4 appuis, 3 travées égales.
        Charge répartie uniforme sur toutes les travées.
        
        △────────△────────△────────△
        ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓  q
        
        Vérification : ΣRy = q × L_total
    """
    print("\n═══ TEST 4 : Poutre continue 3 travées ═══")

    L = 5000.0       # Portée par travée
    q = 20.0         # N/mm
    E = 210000.0
    I = 8.356e7
    A = 5380.0

    m = Model()
    n1 = m.add_node(0,     0, rx=True, ry=True)
    n2 = m.add_node(L,     0, ry=True)
    n3 = m.add_node(2*L,   0, ry=True)
    n4 = m.add_node(3*L,   0, ry=True)

    b1 = m.add_element(n1, n2, E=E, A=A, I=I)
    b2 = m.add_element(n2, n3, E=E, A=A, I=I)
    b3 = m.add_element(n3, n4, E=E, A=A, I=I)

    for b in [b1, b2, b3]:
        b.add_load(DistributedLoad(fy=-q))

    m.solve()

    # ── Vérification ──
    L_total = 3 * L
    total_load = q * L_total
    sum_ry = n1.results.ry + n2.results.ry + n3.results.ry + n4.results.ry

    results_ok = True
    results_ok &= check("ΣRy = q·L_total", sum_ry, total_load, TOL_FORCE)

    # Symétrie des réactions d'extrémité
    results_ok &= check("R1 = R4 (symétrie)",
                         abs(n1.results.ry - n4.results.ry), 0.0, TOL_FORCE)
    # Symétrie des réactions intermédiaires
    results_ok &= check("R2 = R3 (symétrie)",
                         abs(n2.results.ry - n3.results.ry), 0.0, TOL_FORCE)

    # Réactions analytiques (poutre continue 3 travées égales, q uniforme)
    # R1 = R4 = 0.4·q·L, R2 = R3 = 1.1·q·L
    R_ext_ana = 0.4 * q * L
    R_int_ana = 1.1 * q * L

    results_ok &= check("R1 analytique", n1.results.ry, R_ext_ana, TOL_FORCE * 10)
    results_ok &= check("R2 analytique", n2.results.ry, R_int_ana, TOL_FORCE * 10)

    return results_ok


# ═══════════════════════════════════════════════════════════
#  TEST 5 — Poutre + moment appliqué
# ═══════════════════════════════════════════════════════════
def test_applied_moment():
    """
        Poutre bi-appuyée avec moment M₀ en mi-travée.
        
        △──────────⟲──────────△
                   M₀
        
        Solution analytique :
            R = M₀ / L (sens opposés)
            δ_max = M₀·L² / (16·E·I)  (approx.)
    """
    print("\n═══ TEST 5 : Poutre + moment appliqué ═══")

    L = 6000.0
    M0 = 5e7          # N.mm
    E = 210000.0
    I = 8.356e7
    A = 5380.0

    m = Model()
    n1 = m.add_node(0, 0, rx=True, ry=True)
    n2 = m.add_node(L/2, 0)
    n3 = m.add_node(L, 0, ry=True)

    m.add_element(n1, n2, E=E, A=A, I=I)
    m.add_element(n2, n3, E=E, A=A, I=I)

    # Moment appliqué au nœud central
    n2.set_forces(mz=M0)

    m.solve()

    # ── Vérification équilibre ──
    R_ana = M0 / L
    sum_ry = n1.results.ry + n3.results.ry

    results_ok = True
    results_ok &= check("ΣRy = 0",     abs(sum_ry), 0.0, TOL_FORCE)
    results_ok &= check("R1 = M₀/L",   abs(n1.results.ry), R_ana, TOL_FORCE)
    results_ok &= check("θ mi-travée ≠ 0", float(abs(n2.results.theta) > 0), 1.0, 0)

    return results_ok


# ═══════════════════════════════════════════════════════════
#  TEST 6 — Poutre console + charge répartie
# ═══════════════════════════════════════════════════════════
def test_cantilever_udl():
    """
        Console + charge répartie.
        
        ▓▓▓▓├═══════════════════┤
             ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓  q
        
        Solution analytique :
            δ_max = q·L⁴ / (8·E·I)
            M_encastrement = q·L² / 2
            R_y = q·L
    """
    print("\n═══ TEST 6 : Console + charge répartie ═══")

    L = 4000.0
    q = 25.0         # N/mm
    E = 210000.0
    I = 8.356e7
    A = 5380.0

    # On maille en 4 éléments pour plus de précision
    n_elem = 4

    m = Model()

    nodes = []
    for i in range(n_elem + 1):
        x = i * L / n_elem
        if i == 0:
            nodes.append(m.add_node(x, 0, rx=True, ry=True, rz=True))
        else:
            nodes.append(m.add_node(x, 0))

    for i in range(n_elem):
        b = m.add_element(nodes[i], nodes[i+1], E=E, A=A, I=I)
        b.add_load(DistributedLoad(fy=-q))

    m.solve()

    # ── Solutions analytiques ──
    delta_ana = q * L**4 / (8 * E * I)
    M_enc = q * L**2 / 2
    R_y = q * L

    n_tip = nodes[-1]
    n_base = nodes[0]

    results_ok = True
    results_ok &= check("δ bout",       abs(n_tip.results.dy),  delta_ana, TOL_DISPLACEMENT)
    results_ok &= check("Ry encastr.",  n_base.results.ry,      R_y,       TOL_FORCE)
    results_ok &= check("Mz encastr.",  abs(n_base.results.mz), M_enc,     TOL_MOMENT)

    return results_ok


# ═══════════════════════════════════════════════════════════
#  TEST 7 — Vérification erreurs / cas limites
# ═══════════════════════════════════════════════════════════
def test_edge_cases():
    """
        Vérifications de robustesse :
        - Structure non bloquée (doit lever une erreur)
        - Aucun chargement (déplacements = 0)
    """
    print("\n═══ TEST 7 : Cas limites ═══")

    results_ok = True
    E = 210000.0
    I = 8.356e7
    A = 5380.0

    # ── 7a : Structure non bloquée → erreur attendue ──
    try:
        m = Model()
        n1 = m.add_node(0, 0)
        n2 = m.add_node(1000, 0)
        m.add_element(n1, n2, E=E, A=A, I=I)
        n1.add_force(fy=-1000)
        m.solve()
        # Si on arrive ici sans erreur, c'est un problème
        failed("Structure libre → erreur", "Exception", "Aucune")
        results_ok = False
    except Exception:
        passed("Structure libre → erreur levée")

    # ── 7b : Aucun chargement → déplacements nuls ──
    m = Model()
    n1 = m.add_node(0, 0, rx=True, ry=True, rz=True)
    n2 = m.add_node(3000, 0, ry=True)
    m.add_element(n1, n2, E=E, A=A, I=I)
    m.solve()

    results_ok &= check("dx = 0 (pas de charge)", abs(n2.results.dx), 0.0, TOL_DISPLACEMENT)
    results_ok &= check("dy = 0 (pas de charge)", abs(n2.results.dy), 0.0, TOL_DISPLACEMENT)
    results_ok &= check("θz = 0 (pas de charge)", abs(n2.results.theta), 0.0, 1e-8)

    return results_ok


# ═══════════════════════════════════════════════════════════
#  TEST 8 — Effort normal pur (tirant)
# ═══════════════════════════════════════════════════════════
def test_axial():
    """
        Barre en traction pure.
        
        ▓──────────────────────→ F
        
        Solution analytique :
            δ = F·L / (E·A)
            N = F (constant)
    """
    print("\n═══ TEST 8 : Effort normal pur ═══")

    L = 5000.0
    F = 100000.0     # N
    E = 210000.0
    I = 8.356e7
    A = 5380.0

    m = Model()
    n1 = m.add_node(0, 0, rx=True, ry=True, rz=True)
    n2 = m.add_node(L, 0, ry=True)

    m.add_element(n1, n2, E=E, A=A, I=I)
    n2.set_forces(fx=F)

    m.solve()

    delta_ana = F * L / (E * A)

    results_ok = True
    results_ok &= check("δx bout", abs(n2.results.dx), delta_ana, TOL_DISPLACEMENT)
    results_ok &= check("dy = 0",  abs(n2.results.dy), 0.0,       TOL_DISPLACEMENT)
    results_ok &= check("Rx = F",  abs(n1.results.rx), F,         TOL_FORCE)

    return results_ok


# ═══════════════════════════════════════════════════════════
#  RUNNER
# ═══════════════════════════════════════════════════════════
def run_all_tests():
    """Lance tous les tests et affiche le résumé"""

    print("╔══════════════════════════════════════════╗")
    print("║        TESTS MODULE FEM                  ║")
    print("╚══════════════════════════════════════════╝")

    tests = [
        ("Poutre console",             test_cantilever),
        ("Bi-appuyée + q répartie",    test_simply_supported_udl),
        ("Portique simple",            test_portal_frame),
        ("Poutre continue 3 travées",  test_continuous_beam),
        ("Moment appliqué",            test_applied_moment),
        ("Console + q répartie",       test_cantilever_udl),
        ("Cas limites",                test_edge_cases),
        ("Effort normal pur",          test_axial),
    ]

    results = {}
    for name, func in tests:
        try:
            results[name] = func()
        except Exception as e:
            print(f"\n  💥 CRASH dans '{name}': {e}")
            results[name] = False

    # ── Résumé ──
    print("\n")
    print("╔══════════════════════════════════════════╗")
    print("║              RÉSUMÉ                      ║")
    print("╠══════════════════════════════════════════╣")

    n_pass = 0
    n_fail = 0
    for name, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"║  {status}  {name:<30s} ║")
        if ok:
            n_pass += 1
        else:
            n_fail += 1

    print("╠══════════════════════════════════════════╣")
    print(f"║  Total: {n_pass} passés / {n_pass + n_fail} tests"
          f"{' ' * (22 - len(str(n_pass)) - len(str(n_pass + n_fail)))}║")

    if n_fail == 0:
        print("║  🎉 TOUS LES TESTS PASSENT              ║")
    else:
        print(f"║  ⚠️  {n_fail} TEST(S) EN ÉCHEC              ║")

    print("╚══════════════════════════════════════════╝")

    return n_fail == 0


if __name__ == "__main__":
    #success = run_all_tests()
    #sys.exit(0 if success else 1)

    L = 4
    F = 5.0     # N
    E = 1
    I = 1
    A = 1

    m = Model()
    n1 = m.add_node(0, 0, rx=True, ry=True, rz=False)
    n2 = m.add_node(1, 0, rx=True, ry=True, rz=False)
    n3 = m.add_node(2, 0, rx=True, ry=True, rz=False)
    n4 = m.add_node(3, 0, rx=True, ry=True, rz=False)
    n5 = m.add_node(4, 0, rx=True, ry=True, rz=False)

    ab1 = m.add_element(n1, n2, E=E, A=A, I=I)
    ab2 = m.add_element(n2, n3, E=E, A=A, I=I)
    ab3 = m.add_element(n3, n4, E=E, A=A, I=I)
    ab4 = m.add_element(n4, n5, E=E, A=A, I=I)

    ab1.add_load(DistributedLoad(fy=-F))
    ab2.add_load(DistributedLoad(fy=-F))
    ab3.add_load(DistributedLoad(fy=-F))
    ab4.add_load(DistributedLoad(fy=-F))


    m.solve()

    internal_force = m.all_internal_forces(10)
    internal_displacement = m.all_displacements(10)

    # print("Node :", m.nodes)
    # print()
    # print("Element :", m.elements)
    # print()
    # print("Solver :", m.solver)
    # print()
    # print("solved :", m.is_solved)
    # print()
    # print("Summury :", m.summary())
    # print()
    # print("Internal forces :", internal_force)
    # print()
    print("Internal displacements :", internal_displacement)

    x  = 0
    y  = 0

    import matplotlib.pyplot as plt
    x_combined = []
    N_combined = []
    V_combined = []
    M_combined = []

    x2_combined = []
    u_combined = []
    v_combined = []
    theta_combined = []

    x_offset = 0
    for elem_name, forces in internal_force.items():
        x = np.array(forces['x']) + x_offset
        N = np.array(forces['N']) if hasattr(forces['N'], '__len__') else [forces['N']] * len(x)
        V = np.array(forces['V']) if hasattr(forces['V'], '__len__') else [forces['V']] * len(x)
        M = np.array(forces['M']) if hasattr(forces['M'], '__len__') else [forces['M']] * len(x)

        x_combined.extend(x)
        N_combined.extend(N)
        V_combined.extend(V)
        M_combined.extend(M)

        x_offset = x[-1]  # décalage pour l'élément suivant
    
    x_offset2 = 0
    for elem_name, forces in internal_displacement.items():
        x = np.array(forces['x']) + x_offset2
        u = np.array(forces['u']) if hasattr(forces['u'], '__len__') else [forces['u']] * len(x)
        v = np.array(forces['v']) if hasattr(forces['v'], '__len__') else [forces['v']] * len(x)
        theta = np.array(forces['theta']) if hasattr(forces['theta'], '__len__') else [forces['theta']] * len(x)

        x2_combined.extend(x)
        u_combined.extend(u)
        v_combined.extend(v)
        theta_combined.extend(theta)

        x_offset2 = x[-1]  # décalage pour l'élément suivant



 # Plot
    fig, axes = plt.subplots(6, 1, figsize=(10, 8), sharex=True)

    axes[0].plot(x_combined, N_combined, 'b-o')
    axes[0].axhline(0, color='k', linewidth=0.5)
    axes[0].set_ylabel("N [kN]")
    axes[0].set_title("Effort Normal")
    axes[0].grid(True)

    axes[1].plot(x_combined, V_combined, 'r-o')
    axes[1].axhline(0, color='k', linewidth=0.5)
    axes[1].set_ylabel("V [kN]")
    axes[1].set_title("Effort Tranchant")
    axes[1].grid(True)

    axes[2].plot(x_combined, M_combined, 'g-o')
    axes[2].invert_yaxis()
    axes[2].axhline(0, color='k', linewidth=0.5)
    axes[2].set_ylabel("M [kN·m]")
    axes[2].set_xlabel("x [m]")
    axes[2].set_title("Moment Fléchissant")
    axes[2].grid(True)

    axes[3].plot(x2_combined, u_combined, 'g-o')
    axes[3].axhline(0, color='k', linewidth=0.5)
    axes[3].set_ylabel("u [m]")
    axes[3].set_xlabel("x [m]")
    axes[3].set_title("Déplacement Axial")
    axes[3].grid(True)

    axes[4].plot(x2_combined, v_combined, 'g-o')
    axes[4].axhline(0, color='k', linewidth=0.5)
    axes[4].set_ylabel("v [m]")
    axes[4].set_xlabel("x [m]")
    axes[4].set_title("Déplacement Transversal")
    axes[4].grid(True)

    axes[5].plot(x2_combined, theta_combined, 'g-o')
    axes[5].axhline(0, color='k', linewidth=0.5)
    axes[5].set_ylabel("θ [rad]")
    axes[5].set_xlabel("x [m]")
    axes[5].set_title("Rotation")
    axes[5].grid(True)

    plt.tight_layout()
    plt.show()


