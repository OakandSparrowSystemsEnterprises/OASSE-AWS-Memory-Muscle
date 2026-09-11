from oasse_memory_muscle.config import Settings


def test_defaults_preserve_event_dataset_names(monkeypatch):
    for name in ["COGNEE_DATASET", "HYDRADB_TENANT_ID", "DEMO_REPOSITORY", "DEMO_BASE_BRANCH"]:
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env()
    assert settings.cognee_dataset == "oasse-aws-hackathon"
    assert settings.hydradb_tenant_id == "oasse_aws_hackathon"
    assert settings.demo_base_branch == "main"
