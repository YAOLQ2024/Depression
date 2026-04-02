"""Top-level entry for unified V1 API endpoints."""

from __future__ import annotations

from flask import Blueprint

from .api_common import api_health, api_meta

api_v1_bp = Blueprint("api_v1", __name__)

PLANNED_MODULES = [
    "auth-profile",
    "persona",
    "assessment",
    "text-dialogue",
    "speech",
    "emotion",
    "eeg",
    "risk-assessment",
    "intervention",
    "history-report",
    "admin-settings",
]

PLANNED_CAPABILITIES = [
    "identity-access",
    "virtual-clinician",
    "scale-screening",
    "guided-conversation",
    "speech-transcribe",
    "speech-emotion",
    "facial-affect",
    "eeg-sensing",
    "risk-stratification",
    "intervention-decision",
    "record-reporting",
    "system-ops",
]

IMPLEMENTED_CAPABILITIES = ["scale-screening", "risk-stratification"]
IMPLEMENTED_MODULES = ["assessment", "risk-assessment"]

WORKFLOW_V1 = [
    {
        "step": 1,
        "module": "assessment",
        "capability": "scale-screening",
        "label": "量表评估",
    },
    {
        "step": 2,
        "module": "risk-assessment",
        "capability": "risk-stratification",
        "label": "初步风险分层与安全建议",
    },
    {
        "step": 3,
        "module": "text-dialogue",
        "capability": "guided-conversation",
        "label": "引导问诊与画像补全",
    },
    {
        "step": 4,
        "module": "intervention",
        "capability": "intervention-decision",
        "label": "个性化调控决策",
    },
    {
        "step": 5,
        "module": "history-report",
        "capability": "record-reporting",
        "label": "记录与报告",
    },
]


@api_v1_bp.route("/api/v1/health", methods=["GET"])
def api_v1_health():
    return api_health(
        mode="mixed",
        model_loaded=True,
        extra={
            "entry": "api-v1",
            "implemented_module_count": len(IMPLEMENTED_MODULES),
            "planned_module_count": len(PLANNED_MODULES),
            "implemented_modules": IMPLEMENTED_MODULES,
            "workflow_v1": WORKFLOW_V1,
        },
    )


@api_v1_bp.route("/api/v1/meta", methods=["GET"])
def api_v1_meta():
    return api_meta(
        module="api-v1",
        capability="gateway-entry",
        module_zh="统一 API 入口",
        capability_zh="V1 网关入口能力",
        owner="team-platform",
        supports_mock=False,
        extra={
            "module_count": len(PLANNED_MODULES),
            "capability_count": len(PLANNED_CAPABILITIES),
            "planned_modules": PLANNED_MODULES,
            "implemented_modules": IMPLEMENTED_MODULES,
            "implemented_capabilities": IMPLEMENTED_CAPABILITIES,
            "openapi_spec": "depression/docs/openapi_v1.yaml",
            "workflow_v1": WORKFLOW_V1,
            "workflow_notes": [
                "risk-stratification 只负责初步风险分层、阈值判断和安全建议",
                "guided-conversation 是当前主链中的必经画像补全过程",
                "intervention-decision 承接最终的个性化调控内容选择",
            ],
        },
    )
