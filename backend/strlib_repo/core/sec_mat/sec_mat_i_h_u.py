 #!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Module to define the container class for an I/H/U steel section
    associated with a steel material.

    This class does not perform any calculation. It serves as a container
    that bundles a SecIHU section and a MatSteel material together,
    to be used when instantiating a beam element.

    References:
        - EN 1993-1-1 (Eurocode 3)
"""

__all__ = ['SecMatIHU']

from typing import Optional

from core.sec.sec_i_h_u import SecIHU
from core.mat.mat_steel import MatSteel


# =============================================================================
# SecMatIHU
# =============================================================================

class SecMatIHU:
    """
    Conteneur section + matériau pour profilés I, H et U en acier.

    Cette classe ne fait aucun calcul. Elle regroupe :
        - une section  ``SecIHU``   (propriétés géométriques)
        - un matériau  ``MatSteel`` (propriétés mécaniques)

    Elle est destinée à être passée aux classes de vérification
    (flexion, cisaillement, flambement, déversement, etc.) et à
    l'instanciation d'un élément poutre.

    :param sec:  Instance de SecIHU
    :param mat:  Instance de MatSteel
    :param name: Nom optionnel (défaut : combinaison sec.name + mat.grade)
    :param section_class: Classe de section (1, 2, 3 ou 4) — coefficient
        propre à la barre vérifiée (dépend de l'état de contrainte, pas
        seulement de la géométrie), au même titre que les longueurs de
        flambement passées aux vérifications de stabilité.
    """

    def __init__(
        self,
        sec: SecIHU,
        mat: MatSteel,
        name: Optional[str] = None,
        section_class: int = 1,
        Anet: Optional[float] = None,
    ) -> None:

        # ----- Validation -----
        if not isinstance(sec, SecIHU):
            raise TypeError(
                f"sec doit être une instance de SecIHU "
                f"(reçu : {type(sec).__name__})"
            )
        if not isinstance(mat, MatSteel):
            raise TypeError(
                f"mat doit être une instance de MatSteel "
                f"(reçu : {type(mat).__name__})"
            )

        # ----- Stockage -----
        self._sec = sec
        self._mat = mat
        self._name = name or f"{sec.name} — {mat.grade}"
        self._section_class = section_class
        self._Anet = Anet

    # =================================================================
    # Factory — construction à partir de grandeurs brutes (catalogue)
    # =================================================================

    @classmethod
    def from_properties(
        cls,
        name: str,
        *,
        h: float, b: float, tw: float = 0.0, tf: float, r: float = 0.0,
        A: float, Avz: float,
        Iy: float, Iz: float,
        wel_y: float, wel_z: float, wpl_y: float, wpl_z: float,
        iy: float = 0.0, iz: float = 0.0,
        It: float = 0.0, Iw: float = 0.0,
        section_type: str = "H",
        fy: float, fu: float,
        gamma_m0: Optional[float] = None,
        gamma_m1: Optional[float] = None,
        gamma_m2: Optional[float] = None,
        section_class: int = 1,
        Anet: Optional[float] = None,
    ) -> "SecMatIHU":
        """
        Construit un ``SecMatIHU`` complet à partir de grandeurs brutes
        (typiquement un enregistrement de catalogue JSON + une nuance).

        C'est le point d'entrée à utiliser côté appelant (backend, script…) :
        il évite de recréer ``SecIHU``/``MatSteel`` à la main à chaque fois
        qu'un profilé est chargé, et centralise la construction pour que
        tous les éléments (poteau, poutre…) partagent la même logique.

        :param gamma_m0, gamma_m1, gamma_m2: Coefficients partiels γM.
            Si fournis, priment sur l'Annexe Nationale (utile pour les
            normes hors EC3, ex. SIA 263).
        """
        sec = SecIHU(
            name=name,
            h=h, b=b, tw=tw, tf=tf, r=r,
            A=A, Avz=Avz,
            Iy=Iy, Iz=Iz,
            wel_y=wel_y, wel_z=wel_z, wpl_y=wpl_y, wpl_z=wpl_z,
            iy=iy, iz=iz,
            It=It, Iw=Iw,
            section_type=section_type,
        )
        mat = MatSteel(
            fy=fy, fu=fu,
            gamma_m0=gamma_m0, gamma_m1=gamma_m1, gamma_m2=gamma_m2,
        )
        return cls(
            sec=sec, mat=mat, name=name,
            section_class=section_class, Anet=Anet,
        )

    # =================================================================
    # Propriétés d'accès
    # =================================================================

    @property
    def name(self) -> str:
        """Nom de l'ensemble section-matériau"""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def sec(self) -> SecIHU:
        """Section géométrique (SecIHU)"""
        return self._sec

    @sec.setter
    def sec(self, value: SecIHU) -> None:
        if not isinstance(value, SecIHU):
            raise TypeError(
                f"sec doit être une instance de SecIHU "
                f"(reçu : {type(value).__name__})"
            )
        self._sec = value
        self._name = f"{value.name} — {self._mat.grade}"

    @property
    def mat(self) -> MatSteel:
        """Matériau acier (MatSteel)"""
        return self._mat

    @mat.setter
    def mat(self, value: MatSteel) -> None:
        if not isinstance(value, MatSteel):
            raise TypeError(
                f"mat doit être une instance de MatSteel "
                f"(reçu : {type(value).__name__})"
            )
        self._mat = value
        self._name = f"{self._sec.name} — {value.grade}"

    # =================================================================
    # Raccourcis — Géométrie (délégation vers sec)
    # =================================================================

    @property
    def h(self) -> float:
        """Hauteur totale du profilé [mm]"""
        return self._sec.h

    @property
    def b(self) -> float:
        """Largeur de la semelle [mm]"""
        return self._sec.b

    @property
    def tw(self) -> float:
        """Épaisseur de l'âme [mm]"""
        return self._sec.tw

    @property
    def tf(self) -> float:
        """Épaisseur de la semelle [mm]"""
        return self._sec.tf

    @property
    def r(self) -> float:
        """Rayon de congé âme-semelle [mm]"""
        return self._sec.r

    @property
    def hi(self) -> float:
        """Hauteur droite de l'âme [mm]"""
        return self._sec.hi

    @property
    def hw(self) -> float:
        """Hauteur de l'âme entre semelles hw = h - 2·tf [mm].

        Convention EN 1993-1-5 (Figure 5.1) : hauteur libre de l'âme, congés
        exclus — utilisée pour l'élancement hw/tw du voilement par
        cisaillement."""
        return self._sec.h - 2.0 * self._sec.tf

    @property
    def area(self) -> float:
        """Aire de la section [mm²]"""
        return self._sec.area

    @property
    def A(self) -> float:
        """Alias pour area — Aire de la section [mm²]"""
        return self._sec.area

    @property
    def Anet(self) -> float:
        """Aire nette [mm²].

        Par défaut égale à l'aire brute : les catalogues de profilés ne
        tabulent pas l'aire nette, qui dépend du percement effectif. À
        renseigner explicitement (constructeur ou ``from_properties``)
        dès qu'il y a des trous — sinon la vérification de section nette
        (EC3 §6.2.3 (2)b / SIA §5.1.2 éq. 39) est faite sur la section
        brute, ce qui n'est PAS sécuritaire en présence de percements."""
        return self._Anet if self._Anet is not None else self._sec.area

    @Anet.setter
    def Anet(self, value: Optional[float]) -> None:
        self._Anet = value

    @property
    def Avz(self) -> float:
        """Aire de cisaillement selon z [mm²]"""
        return self._sec.Avz

    @property
    def Av_z(self) -> float:
        """Alias — Aire de cisaillement selon z [mm²]"""
        return self._sec.Avz

    @property
    def Av_y(self) -> float:
        """Aire de cisaillement selon y [mm²] — approximation A - Av,z
        (les catalogues I/H ne tabulent que Av,z)."""
        return max(0.0, self._sec.area - self._sec.Avz)

    @property
    def section_type(self) -> str:
        """Type de section — pour la sélection auto des courbes de
        flambement / déversement."""
        return self._sec.section_type

    @property
    def section_class(self) -> int:
        """Classe de section (1, 2, 3 ou 4) — coefficient propre à la barre."""
        return self._section_class

    @section_class.setter
    def section_class(self, value: int) -> None:
        self._section_class = value

    @property
    def inertia_y(self) -> float:
        """Moment d'inertie selon y-y [mm⁴]"""
        return self._sec.inertia_y

    @property
    def Iy(self) -> float:
        """Alias — Moment d'inertie selon y-y [mm⁴]"""
        return self._sec.inertia_y

    @property
    def inertia_z(self) -> float:
        """Moment d'inertie selon z-z [mm⁴]"""
        return self._sec.inertia_z

    @property
    def Iz(self) -> float:
        """Alias — Moment d'inertie selon z-z [mm⁴]"""
        return self._sec.inertia_z

    @property
    def wel_y(self) -> float:
        """Module de résistance élastique selon y-y [mm³]"""
        return self._sec.wel_y

    @property
    def wel_z(self) -> float:
        """Module de résistance élastique selon z-z [mm³]"""
        return self._sec.wel_z

    @property
    def wpl_y(self) -> float:
        """Module de résistance plastique selon y-y [mm³]"""
        return self._sec.wpl_y

    @property
    def wpl_z(self) -> float:
        """Module de résistance plastique selon z-z [mm³]"""
        return self._sec.wpl_z

    # ----- Alias majuscules (convention utilisée par les vérifications
    #       norme.EC3.elu.* / norme.EC3.buckling.*) -----
    @property
    def Wel_y(self) -> float:
        """Alias — Module de résistance élastique selon y-y [mm³]"""
        return self._sec.wel_y

    @property
    def Wel_z(self) -> float:
        """Alias — Module de résistance élastique selon z-z [mm³]"""
        return self._sec.wel_z

    @property
    def Wpl_y(self) -> float:
        """Alias — Module de résistance plastique selon y-y [mm³]"""
        return self._sec.wpl_y

    @property
    def Wpl_z(self) -> float:
        """Alias — Module de résistance plastique selon z-z [mm³]"""
        return self._sec.wpl_z

    @property
    def iy(self) -> float:
        """Rayon de giration selon y-y [mm]"""
        return self._sec.iy

    @property
    def iz(self) -> float:
        """Rayon de giration selon z-z [mm]"""
        return self._sec.iz

    @property
    def It(self) -> float:
        """Constante de torsion de Saint-Venant [mm⁴]"""
        return self._sec.It

    @property
    def Iw(self) -> float:
        """Constante de gauchissement [mm⁶]"""
        return self._sec.Iw

    @property
    def cf_tf(self) -> float:
        """Élancement semelle c/tf [-]"""
        return self._sec.cf_tf

    @property
    def dw_tw(self) -> float:
        """Élancement âme d/tw [-]"""
        return self._sec.dw_tw

    # =================================================================
    # Raccourcis — Matériau (délégation vers mat)
    # =================================================================

    @property
    def fy(self) -> float:
        """Limite d'élasticité [MPa]"""
        return self._mat.fy

    @property
    def fu(self) -> float:
        """Résistance ultime à la traction [MPa]"""
        return self._mat.fu

    @property
    def E(self) -> float:
        """Module d'élasticité [MPa]"""
        return self._mat.E

    @property
    def G(self) -> float:
        """Module de cisaillement [MPa]"""
        return self._mat.G

    @property
    def nu(self) -> float:
        """Coefficient de Poisson [-]"""
        return self._mat.nu

    @property
    def epsilon(self) -> float:
        """ε = √(235 / fy) [-]"""
        return self._mat.epsilon

    @property
    def gamma_m0(self) -> float:
        """Coefficient partiel γM0 [-]"""
        return self._mat.gamma_m0

    @property
    def gamma_m1(self) -> float:
        """Coefficient partiel γM1 [-]"""
        return self._mat.gamma_m1

    @property
    def gamma_m2(self) -> float:
        """Coefficient partiel γM2 [-]"""
        return self._mat.gamma_m2

    @property
    def grade(self) -> str:
        """Nuance d'acier"""
        return self._mat.grade

    # =================================================================
    # Affichage
    # =================================================================

    def __repr__(self) -> str:
        return (
            f"SecMatIHU(name='{self._name}', "
            f"sec={repr(self._sec)}, "
            f"mat={repr(self._mat)})"
        )

    def __str__(self) -> str:
        sep = "=" * 75
        lines = [
            sep,
            f"  Section-Matériau : {self._name}",
            sep,
            "",
            "  ── SECTION ──",
            f"  h  = {self.h:.1f} mm      b  = {self.b:.1f} mm",
            f"  tw = {self.tw:.1f} mm      tf = {self.tf:.1f} mm",
            f"  r  = {self.r:.1f} mm      hi  = {self.hi:.1f} mm",
            f"  A  = {self.area:.0f} mm²    Avz = {self.Avz:.0f} mm²",
            f"  Iy = {self.inertia_y:.0f} mm⁴",
            f"  Iz = {self.inertia_z:.0f} mm⁴",
            f"  Wel,y = {self.wel_y:.0f} mm³   Wel,z = {self.wel_z:.0f} mm³",
            f"  Wpl,y = {self.wpl_y:.0f} mm³   Wpl,z = {self.wpl_z:.0f} mm³",
            f"  iy = {self.iy:.1f} mm      iz = {self.iz:.1f} mm",
            f"  It = {self.It:.0f} mm⁴     Iw = {self.Iw:.4e} mm⁶",
            f"  c/tf = {self.cf_tf:.2f}       hi/tw = {self.dw_tw:.2f}",
            "",
            "  ── MATÉRIAU ──",
            f"  Nuance : {self.grade}",
            f"  fy = {self.fy:.0f} MPa     fu = {self.fu:.0f} MPa",
            f"  E  = {self.E:.0f} MPa   G  = {self.G:.0f} MPa",
            f"  ε  = {self.epsilon:.4f}",
            f"  γM0 = {self.gamma_m0}   γM1 = {self.gamma_m1}   γM2 = {self.gamma_m2}",
            sep,
        ]
        return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":

    # --- Création de la section ---
    ipe300 = SecIHU(
        name="IPE 300",
        h=300, b=150, tw=7.1, tf=10.7, r=15,
        A=5381,
        Avz=2568,
        Iy=83560000,
        Iz=6038000,
        wel_y=557100,
        wel_z=80510,
        wpl_y=628400,
        wpl_z=125200,
        iy=124.6,
        iz=33.5,
        It=201000,
        Iw=126000000000,
    )

    # --- Création du matériau ---
    s355 = MatSteel(grade="S355", thickness=10.7)

    # --- Création du conteneur section-matériau ---
    profil = SecMatIHU(sec=ipe300, mat=s355)
    print(profil)

    # --- Accès raccourcis ---
    print(f"\nAccès directs :")
    print(f"  A     = {profil.A:.0f} mm²")
    print(f"  fy    = {profil.fy:.0f} MPa")
    print(f"  Wpl,y = {profil.wpl_y:.0f} mm³")
    print(f"  ε     = {profil.epsilon:.4f}")
    print(f"  γM0   = {profil.gamma_m0}")

    # --- Accès aux objets sous-jacents ---
    print(f"\nVia sec : {profil.sec.name}")
    print(f"Via mat : {profil.mat.grade}")

    # --- Repr ---
    print(f"\n{repr(profil)}")

    # --- Changement de matériau ---
    s235 = MatSteel(grade="S235", thickness=10.7)
    profil.mat = s235
    print(f"\nAprès changement matériau :")
    print(f"  Nom   = {profil.name}")
    print(f"  fy    = {profil.fy:.0f} MPa")
    print(f"  ε     = {profil.epsilon:.4f}")
