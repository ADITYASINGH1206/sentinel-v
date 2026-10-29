import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sv_api.database import get_db
from sv_api.models import PolicyModel
from sv_engine.cascade import POLICY_PRESETS, PolicyConfig

from tools.simulate_policy import (
    simulate_model_preset,
    simulate_policy,
    sweep_prevalence_curve,
)

router = APIRouter()


class ThresholdsSchema(BaseModel):
    tau_authentic: float = Field(0.35, ge=0.0, le=1.0)
    tau_manipulated: float = Field(0.75, ge=0.0, le=1.0)


class PolicySchema(BaseModel):
    policy_id: str
    version: int = 1
    name: str
    description: str = ""
    target_prevalence: float = Field(0.01, gt=0.0, lt=1.0)
    stage1_variant: str = "smsdt-s-a"
    stage2_variant: str = "smsdt-st-b"
    cascade_enabled: bool = True
    exit_below_p_bal: float = Field(0.12, ge=0.0, le=1.0)
    thresholds: ThresholdsSchema = Field(
        default_factory=lambda: ThresholdsSchema(tau_authentic=0.35, tau_manipulated=0.75)
    )
    audit_sample_rate: float = Field(0.02, ge=0.0, le=1.0)


class SimulateRequest(BaseModel):
    variant: str | None = None
    tpr: float | None = Field(None, ge=0.0, le=1.0)
    fpr: float | None = Field(None, ge=0.0, le=1.0)
    prevalence: float = Field(0.01, gt=0.0, lt=1.0)
    volume_per_day: int = Field(10000, gt=0)
    sweep: bool = False


def _preset_to_dict(p: PolicyConfig) -> dict[str, Any]:
    return {
        "policy_id": p.policy_id,
        "version": p.version,
        "name": p.name,
        "description": p.description,
        "target_prevalence": p.target_prevalence,
        "stage1_variant": p.stage1_variant,
        "stage2_variant": p.stage2_variant,
        "cascade_enabled": p.cascade_enabled,
        "exit_below_p_bal": p.exit_below_p_bal,
        "thresholds": {
            "tau_authentic": p.thresholds.tau_authentic,
            "tau_manipulated": p.thresholds.tau_manipulated,
        },
        "audit_sample_rate": p.audit_sample_rate,
    }


@router.get("/presets", response_model=dict[str, Any])
async def get_presets():
    """Get standard built-in policy presets (strict-low-fpr, transfer-calibrated, evidence-desk)."""
    return {k: _preset_to_dict(v) for k, v in POLICY_PRESETS.items()}


@router.get("", response_model=list[dict[str, Any]])
async def list_policies(db: AsyncSession = Depends(get_db)):
    """List all configured screening policies."""
    stmt = select(PolicyModel).where(PolicyModel.active.is_(True))
    res = await db.execute(stmt)
    rows = res.scalars().all()

    if not rows:
        # Return standard presets if database is not yet seeded
        return [_preset_to_dict(v) for v in POLICY_PRESETS.values()]

    results = []
    for r in rows:
        try:
            cfg = json.loads(r.config)
            cfg["policy_id"] = r.id
            cfg["version"] = r.version
            cfg["name"] = r.name
            results.append(cfg)
        except Exception:
            continue
    return results


@router.get("/{policy_id}", response_model=dict[str, Any])
async def get_policy_by_id(policy_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve policy configuration by ID."""
    stmt = select(PolicyModel).where(PolicyModel.id == policy_id, PolicyModel.active.is_(True))
    res = await db.execute(stmt)
    row = res.scalar_one_or_none()

    if row is not None:
        try:
            cfg = json.loads(row.config)
            cfg["policy_id"] = row.id
            cfg["version"] = row.version
            cfg["name"] = row.name
            return cfg
        except Exception:
            pass

    if policy_id in POLICY_PRESETS:
        return _preset_to_dict(POLICY_PRESETS[policy_id])

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy '{policy_id}' not found"
    )


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_or_update_policy(req: PolicySchema, db: AsyncSession = Depends(get_db)):
    """Register or update a decision policy with version increment."""
    stmt = select(PolicyModel).where(PolicyModel.id == req.policy_id)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    new_version = (existing.version + 1) if existing else req.version
    config_dict = req.model_dump()
    config_dict["version"] = new_version

    if existing:
        existing.version = new_version  # type: ignore[assignment]
        existing.name = req.name  # type: ignore[assignment]
        existing.config = json.dumps(config_dict)  # type: ignore[assignment]
        existing.active = True  # type: ignore[assignment]
    else:
        new_policy = PolicyModel(
            id=req.policy_id,
            version=new_version,
            name=req.name,
            config=json.dumps(config_dict),
            active=True,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(new_policy)

    await db.commit()
    return config_dict


@router.post("/simulate", response_model=dict[str, Any])
async def run_policy_simulation(req: SimulateRequest):
    """Run prevalence-aware policy simulation (SPEC §7.4)."""
    if req.variant:
        target_fpr = req.fpr if req.fpr is not None else 0.01
        sim = simulate_model_preset(
            variant=req.variant,
            target_fpr=target_fpr,
            prevalence=req.prevalence,
            volume_per_day=req.volume_per_day,
        )
        if req.sweep:
            sim["prevalence_sweep"] = sweep_prevalence_curve(
                tpr=sim["tpr"],
                fpr=sim["fpr"],
                volume_per_day=req.volume_per_day,
            )
        return sim

    if req.tpr is not None and req.fpr is not None:
        sim = simulate_policy(
            tpr=req.tpr,
            fpr=req.fpr,
            prevalence=req.prevalence,
            volume_per_day=req.volume_per_day,
        )
        if req.sweep:
            sim["prevalence_sweep"] = sweep_prevalence_curve(
                tpr=req.tpr,
                fpr=req.fpr,
                volume_per_day=req.volume_per_day,
            )
        return sim

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Must supply either 'variant' or both 'tpr' and 'fpr'",
    )
