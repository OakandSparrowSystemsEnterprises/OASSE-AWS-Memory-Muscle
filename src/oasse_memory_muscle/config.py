from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    cognee_base_url: str
    cognee_api_key: str
    cognee_dataset: str
    hydradb_api_key: str
    hydradb_tenant_id: str
    hotdata_api_key: str
    hotdata_workspace: str
    rote_api_key: str
    snyk_token: str
    tenki_api_key: str
    gatekeeper_url: str
    gatekeeper_api_key: str
    demo_repository: str
    demo_base_branch: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            cognee_base_url=os.getenv("COGNEE_BASE_URL", ""),
            cognee_api_key=os.getenv("COGNEE_API_KEY", ""),
            cognee_dataset=os.getenv("COGNEE_DATASET", "oasse-aws-hackathon"),
            hydradb_api_key=os.getenv("HYDRADB_API_KEY", ""),
            hydradb_tenant_id=os.getenv("HYDRADB_TENANT_ID", "oasse_aws_hackathon"),
            hotdata_api_key=os.getenv("HOTDATA_API_KEY", ""),
            hotdata_workspace=os.getenv("HOTDATA_WORKSPACE", ""),
            rote_api_key=os.getenv("ROTE_API_KEY", ""),
            snyk_token=os.getenv("SNYK_TOKEN", ""),
            tenki_api_key=os.getenv("TENKI_API_KEY", ""),
            gatekeeper_url=os.getenv("GATEKEEPER_URL", ""),
            gatekeeper_api_key=os.getenv("GATEKEEPER_API_KEY", ""),
            demo_repository=os.getenv("DEMO_REPOSITORY", "OakandSparrowSystemsEnterprises/OASSE-AWS-Memory-Muscle"),
            demo_base_branch=os.getenv("DEMO_BASE_BRANCH", "main"),
        )

    def missing_required(self) -> list[str]:
        required = {
            "COGNEE_BASE_URL": self.cognee_base_url,
            "COGNEE_API_KEY": self.cognee_api_key,
            "HYDRADB_API_KEY": self.hydradb_api_key,
            "HYDRADB_TENANT_ID": self.hydradb_tenant_id,
            "HOTDATA_API_KEY": self.hotdata_api_key,
            "ROTE_API_KEY": self.rote_api_key,
            "SNYK_TOKEN": self.snyk_token,
            "GATEKEEPER_URL": self.gatekeeper_url,
            "GATEKEEPER_API_KEY": self.gatekeeper_api_key,
        }
        return [name for name, value in required.items() if not value]
