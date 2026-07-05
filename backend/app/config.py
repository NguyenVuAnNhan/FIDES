from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    fides_env: str = "development"
    vnpt_provider_mode: str = "real"
    vnpt_ekyc_mode: str | None = None
    vnpt_smartvoice_mode: str | None = "real"
    vnpt_smartbot_mode: str | None = "real"
    vnpt_smartvision_mode: str | None = "real"
    vnpt_smartreader_mode: str | None = "real"
    vnpt_base_url: str = "https://api.idg.vnpt.vn"
    vnpt_smartbot_base_url: str = "https://assistant-stream.vnpt.vn"
    vnpt_access_token: str | None = None
    vnpt_token_id: str | None = None
    vnpt_token_key: str | None = None
    vnpt_ekyc_access_token: str | None = None
    vnpt_ekyc_token_id: str | None = None
    vnpt_ekyc_token_key: str | None = None
    vnpt_smartvoice_access_token: str | None = None
    vnpt_smartvoice_token_id: str | None = None
    vnpt_smartvoice_token_key: str | None = None
    vnpt_smartbot_access_token: str | None = None
    vnpt_smartbot_token_id: str | None = None
    vnpt_smartbot_token_key: str | None = None
    vnpt_smartbot_bot_id: str | None = None
    vnpt_smartbot_input_channel: str = "api"
    vnpt_smartbot_sender_id: str = "fides-shield-user"
    vnpt_smartbot_request_timeout_seconds: int = 45
    vnpt_smartvision_access_token: str | None = None
    vnpt_smartvision_token_id: str | None = None
    vnpt_smartvision_token_key: str | None = None
    vnpt_smartvision_token: str | None = None
    vnpt_smartvision_detect_face_path: str = "/data-service/v1/smartvision/detect-face"
    vnpt_smartvision_max_object: int = 1
    vnpt_smartvision_request_timeout_seconds: int = 30
    vnpt_smartreader_access_token: str | None = None
    vnpt_smartreader_token_id: str | None = None
    vnpt_smartreader_token_key: str | None = None
    vnpt_smartreader_token: str | None = None
    vnpt_smartreader_request_timeout_seconds: int = 60
    vnpt_ekyc_token: str | None = None
    vnpt_mac_address: str = "TEST1"
    vnpt_request_timeout_seconds: int = 20
    vnpt_ekyc_request_timeout_seconds: int = 60
    vnpt_stt_sample_rate: int = 16000
    vnpt_stt_content_type: str = "audio/wav"
    vnpt_stt_enable_lm: str = "true"
    vnpt_stt_bit_per_rate: int = 16
    vnpt_stt_domain: str = "general"
    vnpt_stt_save_log: str = "true"
    vnpt_stt_cap_punct_recovery: str = "true"
    vnpt_smartvoice_api_key: str | None = None
    vnpt_smartbot_api_key: str | None = None
    vnpt_smartreader_api_key: str | None = None
    voice_stress_enabled: bool = True
    voice_stress_mode: str = "auto"
    voice_stress_locale: str = "vi"
    voice_stress_backend: str = "emotion2vec"
    voice_stress_model_name: str = "iic/emotion2vec_plus_base"
    voice_stress_model_hub: str = "hf"
    voice_stress_arousal_weight: float = 0.55
    voice_stress_prosody_weight: float = 0.45
    neo4j_enabled: bool = False
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "fides-dev-password"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
