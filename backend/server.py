from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from strlib_service import compute_poteau_comprime, list_profiles
from poutre_service import compute_poutre_flechie, list_supports, list_deflection_limits
from poteau_beton_service import (
    compute_poteau_beton, list_methodes, list_concrete_classes, list_rebar_grades,
)
from neige_service import compute_neige, list_fr_departments, list_fr_zones
from vent_service import compute_vent, list_fr_departments as list_vent_fr_departments, list_fr_regions, list_terrain_categories
from seisme_service import compute_seisme, list_zones as list_seisme_zones, list_soil_classes as list_seisme_soil_classes, list_importance_classes as list_seisme_importance_classes
import stripe_service
import auth_service
from auth_service import AuthError, current_user, current_user_optional


# MongoDB connection — requise depuis l'introduction des comptes
# utilisateurs (auth + quota serveur).
mongo_url = os.environ.get('MONGO_URL')
if not mongo_url:
    raise RuntimeError(
        "MONGO_URL n'est pas defini. C-Lab a besoin de MongoDB pour les "
        "comptes et le quota. Exemple : MONGO_URL=mongodb://localhost:27017 "
        "et DB_NAME=clab (voir .env.example)."
    )
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'clab')]

# Create the main app without a prefix
app = FastAPI(title="C-Lab API")
# Rend la base accessible aux dependances (auth_service.current_user).
app.state.db = db

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Existing endpoints (kept)
# ---------------------------------------------------------------------------
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

@api_router.get("/")
async def root():
    return {"message": "Structura API — calculs structuraux via Str-lib"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]


# ---------------------------------------------------------------------------
# Calculation endpoints — wired to Str-lib (strlib_repo)
# ---------------------------------------------------------------------------
class PoutreFlexionInput(BaseModel):
    """Deprecated — kept as stub to avoid breaking older callers."""

    pass


class ResultRow(BaseModel):
    label: str
    value: str
    unit: Optional[str] = None
    status: Optional[str] = None
    formula: Optional[str] = None


class DetailRow(BaseModel):
    label: str
    value: str
    unit: Optional[str] = None
    formula: Optional[str] = None


class DetailBlock(BaseModel):
    title: str
    rows: List[DetailRow] = []
    subBlocks: List["DetailBlock"] = []


class DetailPayload(BaseModel):
    blocks: List[DetailBlock]


class CalculResponse(BaseModel):
    module: str
    inputs: dict
    results: List[ResultRow]
    detail: Optional[DetailPayload] = None
    spectrum: Optional[dict] = None
    diagram: Optional[dict] = None


DetailBlock.model_rebuild()



async def _consume_quota(user: dict) -> None:
    """Decompte un calcul du quota du compte — 402 si epuise."""
    try:
        await auth_service.consume_quota(db, user["user_id"], user["premium"])
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail)


class PoteauComprimeInput(BaseModel):
    # Main inputs
    norme: str = Field("EC3", description="EC3 ou SIA263")
    profile: str = Field(..., description="Profilé acier, ex. 'HEA 200'")
    grade: str = Field("S275", description="Nuance d'acier")
    N_ed_kn: float = Field(0.0, ge=0)
    My_ed_knm: float = Field(0.0, ge=0)
    Mz_ed_knm: float = Field(0.0, ge=0)
    Vz_ed_kn: float = Field(0.0, ge=0)
    Vy_ed_kn: float = Field(0.0, ge=0)
    Lcry_m: float = Field(3.0, gt=0)
    Lcrz_m: float = Field(3.0, gt=0)
    LcrLT_m: float = Field(3.0, gt=0)
    # Metadata for detail display
    length_m: Optional[float] = None
    Ky: Optional[float] = None
    Kz: Optional[float] = None
    psi_y: float = Field(1.0)
    psi_z: float = Field(1.0)
    # Advanced
    gamma_m0: Optional[float] = Field(None, gt=0)
    gamma_m1: Optional[float] = Field(None, gt=0)
    C1: float = Field(1.0, gt=0)
    Cmy: float = Field(0.9, gt=0)
    Cmz: float = Field(0.9, gt=0)
    section_class: int = Field(1, ge=1, le=4)
    interaction_method: int = Field(2, ge=1, le=2)
    curve_y_override: Optional[str] = None
    curve_z_override: Optional[str] = None
    curve_LT_override: Optional[str] = None


@api_router.post("/calcul/acier/poteau-comprime", response_model=CalculResponse)
async def calcul_poteau_comprime(
    payload: PoteauComprimeInput, user: dict = Depends(current_user)
) -> CalculResponse:
    await _consume_quota(user)
    try:
        result = compute_poteau_comprime(**payload.dict())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CalculResponse(**result)


@api_router.get("/profiles/{family}")
async def get_profiles(family: str) -> dict:
    return {"family": family.upper(), "profiles": list_profiles(family)}


# ---------------------------------------------------------------------------
# Poutre acier fléchie — EC3 (EN 1993-1-1 / 1-5) et SIA 263
# ---------------------------------------------------------------------------
class PoutreFlechieInput(BaseModel):
    norme: str = Field("EC3", description="'EC3' ou 'SIA263'")
    profile: str = Field(..., description="Profilé acier, ex. 'IPE 300'")
    grade: str = Field("S235", description="Nuance d'acier")
    # Efforts — N > 0 = traction
    N_ed_kn: float = Field(0.0)
    My_ed_knm: float = Field(0.0, ge=0)
    Mz_ed_knm: float = Field(0.0, ge=0)
    Vz_ed_kn: float = Field(0.0, ge=0)
    Vy_ed_kn: float = Field(0.0, ge=0)
    # Géométrie
    L_m: float = Field(6.0, gt=0)
    Lcr_LT_m: Optional[float] = Field(None, gt=0)
    Lcry_m: Optional[float] = Field(None, gt=0)
    Lcrz_m: Optional[float] = Field(None, gt=0)
    # Paramètres
    section_class: int = Field(1, ge=1, le=3)
    profile_type: str = Field("rolled", description="'rolled' ou 'welded'")
    a_stiffener_m: Optional[float] = Field(None, gt=0)
    rigid_end_post: bool = Field(True)
    psi: float = Field(1.0)
    C1: float = Field(1.0, gt=0)
    # ELS
    q_els_kn_m: Optional[float] = Field(None, ge=0)
    deflection_mm: Optional[float] = Field(None, ge=0)
    support: str = Field("simply_supported")
    limit_type: str = Field("floor_general")
    limit_ratio: Optional[float] = Field(None, gt=0)
    # Avancé
    gamma_m0: Optional[float] = Field(None, gt=0)
    gamma_m1: Optional[float] = Field(None, gt=0)


@api_router.post("/calcul/acier/poutre-flechie", response_model=CalculResponse)
async def calcul_poutre_flechie(
    payload: PoutreFlechieInput, user: dict = Depends(current_user)
) -> CalculResponse:
    await _consume_quota(user)
    try:
        result = compute_poutre_flechie(**payload.dict())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CalculResponse(**result)


@api_router.get("/poutre/supports")
async def get_poutre_supports() -> dict:
    return {"supports": list_supports()}


@api_router.get("/poutre/deflection-limits")
async def get_poutre_deflection_limits() -> dict:
    return {"limits": list_deflection_limits()}


# ---------------------------------------------------------------------------
# Poteau béton armé — EC2 (EN 1992-1-1 §5.8) et SIA 262 (§4.3.7)
# ---------------------------------------------------------------------------
class PoteauBetonInput(BaseModel):
    norme: str = Field("EC2", description="'EC2' ou 'SIA262'")
    methode: str = Field("courbure", description="'courbure' | 'rigidite' | 'forfaitaire'")
    shape: str = Field("rect", description="'rect' ou 'circ'")
    b_mm: float = Field(300.0, gt=0)
    h_mm: float = Field(400.0, gt=0)
    D_mm: float = Field(400.0, gt=0)
    l0_m: float = Field(3.5, gt=0)
    l_real_m: Optional[float] = Field(None, gt=0)
    N_ed_kn: float = Field(0.0, ge=0, description="Compression [kN]")
    M0_top_knm: float = Field(0.0)
    M0_bot_knm: float = Field(0.0)
    As_cm2: float = Field(0.0, ge=0)
    d_prime_mm: float = Field(50.0, gt=0)
    concrete_class: str = Field("C25/30")
    rebar_grade: str = Field("B500B")
    phi_ef: float = Field(2.0, ge=0)
    c_curvature: float = Field(10.0, gt=0)
    c0_stiffness: float = Field(8.0, gt=0)
    show_diagram: bool = Field(False)
    gamma_c: Optional[float] = Field(None, gt=0)
    gamma_s: Optional[float] = Field(None, gt=0)


@api_router.post("/calcul/beton/poteau", response_model=CalculResponse)
async def calcul_poteau_beton(
    payload: PoteauBetonInput, user: dict = Depends(current_user)
) -> CalculResponse:
    await _consume_quota(user)
    try:
        result = compute_poteau_beton(**payload.dict())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CalculResponse(**result)


@api_router.get("/beton/methodes")
async def get_beton_methodes() -> dict:
    return {"methodes": list_methodes()}


@api_router.get("/beton/classes")
async def get_beton_classes() -> dict:
    return {
        "concrete_classes": list_concrete_classes(),
        "rebar_grades": list_rebar_grades(),
    }


# ---------------------------------------------------------------------------
# Charges de neige — France (NF EN 1991-1-3/NA) et Suisse (SIA 261)
# ---------------------------------------------------------------------------
class NeigeInput(BaseModel):
    country: str = Field(..., description="'FR' ou 'CH'")
    angle_deg: float = Field(..., ge=0, le=90, description="Angle de toiture [°]")
    exposure: str = Field("normal", description="'expose'/'normal'/'abrite' (CH) ou 'normal'/'abrite' (FR)")
    Ct: float = Field(1.0, gt=0)
    # France
    zone: Optional[str] = Field(None, description="Zone FR : A1, A2, B1, B2, C1, C2, D, E")
    departement: Optional[str] = Field(None, description="Code département FR (ex. '74') — alternative à 'zone'")
    altitude_m: Optional[float] = Field(None, ge=0, le=2000)
    # Suisse
    h0_m: Optional[float] = Field(None, gt=0, description="Altitude de référence (SIA 261, Annexe D)")


@api_router.post("/calcul/neige", response_model=CalculResponse)
async def calcul_neige(
    payload: NeigeInput, user: dict = Depends(current_user)
) -> CalculResponse:
    await _consume_quota(user)
    try:
        result = compute_neige(**payload.dict())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CalculResponse(**result)


@api_router.get("/neige/departements")
async def get_neige_departements() -> dict:
    return {"departements": list_fr_departments()}


@api_router.get("/neige/zones")
async def get_neige_zones() -> dict:
    return {"zones": list_fr_zones()}


# ---------------------------------------------------------------------------
# Pression du vent — France (NF EN 1991-1-4/NA) et Suisse (SIA 261)
# ---------------------------------------------------------------------------
class VentInput(BaseModel):
    country: str = Field(..., description="'FR' ou 'CH'")
    h_m: float = Field(..., gt=0, description="Hauteur du bâtiment [m]")
    b_m: float = Field(..., gt=0, description="Largeur au vent [m]")
    d_m: float = Field(..., gt=0, description="Profondeur dans le sens du vent [m]")
    terrain_category: str = Field(..., description="FR: '0','II','IIIa','IIIb','IV' — CH: 'II','IIa','III','IV'")
    cscd: float = Field(1.0, gt=0)
    # France
    region: Optional[str] = Field(None, description="Région climatique FR : '1'..'4' ou DOM")
    departement: Optional[str] = Field(None, description="Code département FR (ex. '74') — alternative à 'region'")
    cdir: float = Field(1.0, gt=0)
    cseason: float = Field(1.0, gt=0)
    # Suisse
    qp0_kn_m2: Optional[float] = Field(None, gt=0, description="Pression dynamique de référence (SIA 261, Annexe E)")


@api_router.post("/calcul/vent", response_model=CalculResponse)
async def calcul_vent(
    payload: VentInput, user: dict = Depends(current_user)
) -> CalculResponse:
    await _consume_quota(user)
    try:
        result = compute_vent(**payload.dict())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CalculResponse(**result)


@api_router.get("/vent/departements")
async def get_vent_departements() -> dict:
    return {"departements": list_vent_fr_departments()}


@api_router.get("/vent/regions")
async def get_vent_regions() -> dict:
    return {"regions": list_fr_regions()}


@api_router.get("/vent/terrain-categories/{country}")
async def get_vent_terrain_categories(country: str) -> dict:
    return {"categories": list_terrain_categories(country)}


# ---------------------------------------------------------------------------
# Spectre de réponse sismique — France (NF EN 1998-1 + NA) et Suisse (SIA 261,
# chap. 16). Zones/importance FR reconstruites depuis l'arrêté du 22/10/2010
# (non lu comme document source) — voir norme.EC8.seisme.response_spectrum.
# ---------------------------------------------------------------------------
class SeismeInput(BaseModel):
    country: str = Field(..., description="'FR' ou 'CH'")
    zone: str = Field(..., description="Zone sismique — FR : '1'..'5' ; CH : 'Z1a'..'Z3b' (Annexe F, carte)")
    soil_class: str = Field(..., description="Classe de sol/terrain : 'A'..'E'")
    q: float = Field(1.5, gt=0, description="Coefficient de comportement")
    importance_class: Optional[str] = Field(None, description="FR : 'I'..'IV' (défaut 'II') ; CH : 'I'..'III' (défaut 'III')")
    xi_percent: float = Field(5.0, gt=0, description="Amortissement visqueux [%]")
    t_point: Optional[float] = Field(None, ge=0, description="Période T [s] pour lire un point exact sur la courbe")


@api_router.post("/calcul/seisme", response_model=CalculResponse)
async def calcul_seisme(
    payload: SeismeInput, user: dict = Depends(current_user)
) -> CalculResponse:
    await _consume_quota(user)
    try:
        result = compute_seisme(**payload.dict())
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return CalculResponse(**result)


@api_router.get("/seisme/zones/{country}")
async def get_seisme_zones(country: str) -> dict:
    return {"zones": list_seisme_zones(country)}


@api_router.get("/seisme/soil-classes/{country}")
async def get_seisme_soil_classes(country: str) -> dict:
    return {"soil_classes": list_seisme_soil_classes(country)}


@api_router.get("/seisme/importance-classes/{country}")
async def get_seisme_importance_classes(country: str) -> dict:
    return {"importance_classes": list_seisme_importance_classes(country)}



# ---------------------------------------------------------------------------
# Comptes utilisateurs — inscription, connexion, profil, quota
# ---------------------------------------------------------------------------
class RegisterInput(BaseModel):
    email: str
    password: str


class LoginInput(BaseModel):
    email: str
    password: str


class ChangePasswordInput(BaseModel):
    current_password: str
    new_password: str


@api_router.post("/auth/register")
async def auth_register(payload: RegisterInput) -> dict:
    try:
        return await auth_service.register(db, payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail)


@api_router.post("/auth/login")
async def auth_login(payload: LoginInput) -> dict:
    try:
        return await auth_service.login(db, payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail)


@api_router.get("/auth/me")
async def auth_me(user: dict = Depends(current_user)) -> dict:
    usage = await auth_service.get_usage(db, user["user_id"], user["premium"])
    return {"user": user, "usage": usage}


@api_router.post("/auth/password")
async def auth_change_password(
    payload: ChangePasswordInput, user: dict = Depends(current_user)
) -> dict:
    try:
        await auth_service.change_password(
            db, user["user_id"], payload.current_password, payload.new_password
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail)
    return {"ok": True}


@api_router.get("/auth/usage")
async def auth_usage(user: dict = Depends(current_user)) -> dict:
    return await auth_service.get_usage(db, user["user_id"], user["premium"])


# ---------------------------------------------------------------------------
# Stripe subscription endpoints
# ---------------------------------------------------------------------------
class CheckoutRequest(BaseModel):
    device_id: str = Field(..., min_length=6)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    email: Optional[str] = None


class CheckoutResponse(BaseModel):
    url: str
    session_id: str


class SubscriptionStatus(BaseModel):
    device_id: str
    is_premium: bool
    status: Optional[str] = None
    current_period_end: Optional[int] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    cancel_at_period_end: bool = False


@api_router.post("/stripe/create-checkout", response_model=CheckoutResponse)
async def stripe_create_checkout(payload: CheckoutRequest) -> CheckoutResponse:
    try:
        result = await stripe_service.create_checkout_session(
            db,
            device_id=payload.device_id,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
            customer_email=payload.email,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:  # pragma: no cover — stripe errors bubble here
        logger.exception("Stripe checkout error")
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc}")
    return CheckoutResponse(**result)


@api_router.get("/stripe/status/{device_id}", response_model=SubscriptionStatus)
async def stripe_status(device_id: str) -> SubscriptionStatus:
    data = await stripe_service.get_status(db, device_id)
    return SubscriptionStatus(**data)


@api_router.post("/stripe/reconcile", response_model=SubscriptionStatus)
async def stripe_reconcile(device_id: str, session_id: str) -> SubscriptionStatus:
    """Client-triggered reconciliation after checkout redirect."""
    data = await stripe_service.reconcile_from_session(db, device_id, session_id)
    return SubscriptionStatus(**data)


@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        return await stripe_service.process_webhook_event(db, payload, signature)
    except HTTPException:
        raise
    except Exception as exc:  # signature failures etc.
        logger.warning("Stripe webhook error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_db_client():
    try:
        await stripe_service.ensure_indexes(db)
        logger.info("Stripe indexes ensured")
    except Exception as exc:
        logger.warning("Could not ensure Stripe indexes: %s", exc)
    try:
        await auth_service.ensure_indexes(db)
        logger.info("Auth indexes ensured")
    except Exception as exc:
        logger.warning("Could not ensure auth indexes: %s", exc)
    if auth_service.AUTH_SECRET_IS_EPHEMERAL:
        logger.warning(
            "AUTH_SECRET absent : cle de signature ephemere generee. "
            "Toutes les sessions seront invalidees au prochain redemarrage. "
            "Definissez AUTH_SECRET en production."
        )


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# ---------------------------------------------------------------------------
# Site web statique — sert l'export web d'Expo (yarn build → frontend/dist)
# Doit rester déclaré après api_router pour que /api garde la priorité.
# ---------------------------------------------------------------------------
FRONTEND_DIST = ROOT_DIR.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    logger.warning(
        "frontend/dist introuvable — lancez 'yarn build' dans frontend/ avant de servir le site."
    )
