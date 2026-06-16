"""Factory for workspace CRM clients."""

from app.adapters.crm.base import CRMClient
from app.adapters.crm.grs import GRSCRMClient
from app.adapters.crm.intake import IntakeCRMClient
from app.adapters.crm.medhub import MedHubCRMClient
from app.config import get_settings


def get_crm_clients() -> dict[str, CRMClient]:
    """Build CRM clients for all configured workspaces."""

    settings = get_settings()
    return {
        "intake": IntakeCRMClient(
            base_url=settings.crm.intake.base_url,
            api_token=settings.crm.intake.api_token,
        ),
        "medhub": MedHubCRMClient(
            base_url=settings.crm.medhub.base_url,
            api_token=settings.crm.medhub.api_token,
        ),
        "grs": GRSCRMClient(
            base_url=settings.crm.grs.base_url,
            api_token=settings.crm.grs.api_token,
        ),
    }
