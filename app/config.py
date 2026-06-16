"""Application settings loaded from environment variables.

Production deployments should inject secrets through GCP Secret Manager. Local
development may use a `.env` file that follows `.env.example`.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    """Base class shared by nested settings models."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


class GCPSettings(EnvSettings):
    """GCP project, region, and Pub/Sub resource settings."""

    project_id: str = Field(default="", validation_alias="GCP_PROJECT_ID")
    region: str = Field(default="", validation_alias="GCP_REGION")
    pubsub_topic_call_completed: str = Field(
        default="call.completed",
        validation_alias="PUBSUB_TOPIC_CALL_COMPLETED",
    )
    pubsub_subscription_worker: str = Field(
        default="call-intelligence-worker-sub",
        validation_alias="PUBSUB_SUBSCRIPTION_WORKER",
    )


class GCSSettings(EnvSettings):
    """GCS buckets used by telephony providers."""

    audio_bucket: str = Field(
        default="pb-dispositions-call-recordings",
        validation_alias="GCS_AUDIO_BUCKET",
    )
    ringcentral_bucket: str = Field(default="", validation_alias="GCS_RINGCENTRAL_BUCKET")


class PhoneBurnerSettings(EnvSettings):
    """PhoneBurner API and webhook settings."""

    api_key: str = Field(default="", validation_alias="PHONEBURNER_API_KEY")
    client_id: str = Field(default="", validation_alias="PHONEBURNER_CLIENT_ID")
    webhook_secret: str = Field(default="", validation_alias="PHONEBURNER_WEBHOOK_SECRET")


class RingCentralSettings(EnvSettings):
    """RingCentral API and webhook settings."""

    client_id: str = Field(default="", validation_alias="RINGCENTRAL_CLIENT_ID")
    client_secret: str = Field(default="", validation_alias="RINGCENTRAL_CLIENT_SECRET")
    account_id: str = Field(default="", validation_alias="RINGCENTRAL_ACCOUNT_ID")
    webhook_verification_token: str = Field(
        default="",
        validation_alias="RINGCENTRAL_WEBHOOK_VERIFICATION_TOKEN",
    )


class TelephonySettings(EnvSettings):
    """Telephony provider settings grouped by source."""

    phoneburner: PhoneBurnerSettings = Field(default_factory=PhoneBurnerSettings)
    ringcentral: RingCentralSettings = Field(default_factory=RingCentralSettings)


class STTSettings(EnvSettings):
    """Speech-to-text provider settings."""

    deepgram_api_key: str = Field(default="", validation_alias="DEEPGRAM_API_KEY")
    provider: Literal["deepgram", "google", "passthrough"] = Field(
        default="deepgram",
        validation_alias="STT_PROVIDER",
    )


class LLMSettings(EnvSettings):
    """LLM provider settings."""

    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")


class WorkspaceCRMSettings(EnvSettings):
    """Twenty CRM connection settings for one workspace."""

    base_url: str = ""
    api_token: str = ""


class CRMSettings(EnvSettings):
    """Twenty CRM workspace settings."""

    intake: WorkspaceCRMSettings = Field(default_factory=WorkspaceCRMSettings)
    medhub: WorkspaceCRMSettings = Field(default_factory=WorkspaceCRMSettings)
    grs: WorkspaceCRMSettings = Field(default_factory=WorkspaceCRMSettings)

    @classmethod
    def from_env(cls) -> "CRMSettings":
        """Build CRM settings from flat workspace-specific environment variables."""

        return cls(
            intake=WorkspaceCRMSettings(
                base_url=IntakeCRMEnv().base_url,
                api_token=IntakeCRMEnv().api_token,
            ),
            medhub=WorkspaceCRMSettings(
                base_url=MedHubCRMEnv().base_url,
                api_token=MedHubCRMEnv().api_token,
            ),
            grs=WorkspaceCRMSettings(
                base_url=GRSCRMEnv().base_url,
                api_token=GRSCRMEnv().api_token,
            ),
        )


class IntakeCRMEnv(EnvSettings):
    """Flat environment aliases for Intake CRM settings."""

    base_url: str = Field(default="", validation_alias="INTAKE_CRM_BASE_URL")
    api_token: str = Field(default="", validation_alias="INTAKE_CRM_API_TOKEN")


class MedHubCRMEnv(EnvSettings):
    """Flat environment aliases for MedHub CRM settings."""

    base_url: str = Field(default="", validation_alias="MEDHUB_CRM_BASE_URL")
    api_token: str = Field(default="", validation_alias="MEDHUB_CRM_API_TOKEN")


class GRSCRMEnv(EnvSettings):
    """Flat environment aliases for GRS CRM settings."""

    base_url: str = Field(default="", validation_alias="GRS_CRM_BASE_URL")
    api_token: str = Field(default="", validation_alias="GRS_CRM_API_TOKEN")


class DatabaseSettings(EnvSettings):
    """Database connection settings."""

    url: str = Field(default="", validation_alias="DATABASE_URL")


class PipelineSettings(EnvSettings):
    """Pipeline behavior and review queue settings."""

    min_call_duration_seconds: int = Field(
        default=30,
        validation_alias="MIN_CALL_DURATION_SECONDS",
    )
    match_confidence_threshold: float = Field(
        default=0.8,
        validation_alias="MATCH_CONFIDENCE_THRESHOLD",
    )
    slack_review_queue_webhook_url: str = Field(
        default="",
        validation_alias="SLACK_REVIEW_QUEUE_WEBHOOK_URL",
    )


class Settings(EnvSettings):
    """Root settings object composed of nested settings groups."""

    gcp: GCPSettings = Field(default_factory=GCPSettings)
    gcs: GCSSettings = Field(default_factory=GCSSettings)
    telephony: TelephonySettings = Field(default_factory=TelephonySettings)
    stt: STTSettings = Field(default_factory=STTSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    crm: CRMSettings = Field(default_factory=CRMSettings.from_env)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)

    def safe_summary(self) -> dict[str, object]:
        """Return non-secret settings useful for startup logs."""

        return {
            "gcp_project_id": self.gcp.project_id,
            "gcp_region": self.gcp.region,
            "pubsub_topic": self.gcp.pubsub_topic_call_completed,
            "pubsub_subscription": self.gcp.pubsub_subscription_worker,
            "audio_bucket": self.gcs.audio_bucket,
            "ringcentral_bucket_configured": bool(self.gcs.ringcentral_bucket),
            "stt_provider": self.stt.provider,
            "database_configured": bool(self.database.url),
            "review_queue_configured": bool(self.pipeline.slack_review_queue_webhook_url),
            "crm_workspaces_configured": {
                "intake": bool(self.crm.intake.base_url),
                "medhub": bool(self.crm.medhub.base_url),
                "grs": bool(self.crm.grs.base_url),
            },
        }


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
