from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    fides_env: str = "development"
    vnpt_provider_mode: str = "mock"
    vnpt_base_url: str = "https://api.idg.vnpt.vn"
    vnpt_access_token: str | None = None
    vnpt_token_id: str | None = None
    vnpt_token_key: str | None = None
    vnpt_ekyc_token: str | None = None
    vnpt_mac_address: str = "TEST1"
    vnpt_stt_sample_rate: int = 16000
    vnpt_stt_content_type: str = "audio/wav"
    vnpt_stt_enable_lm: str = "true"
    vnpt_stt_bit_per_rate: int = 16
    vnpt_stt_domain: str = "general"
    vnpt_stt_save_log: str = "true"
    vnpt_stt_cap_punct_recovery: str = "true"
    vnpt_voice_base_url: str = "https://api.idg.vnpt.vn/voice-service"
    vnpt_voice_verify_email: str = "demo-customer@fides.local"
    vnpt_voice_verify_name: str = "FIDES Demo Customer"
    vnpt_smartvoice_api_key: str | None = None
    vnpt_smartbot_api_key: str | None = None
    vnpt_smartreader_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
