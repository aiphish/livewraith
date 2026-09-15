from pydantic import BaseModel, Field, computed_field, AliasChoices, field_validator
from typing import Annotated, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, YamlConfigSettingsSource

class ProdSettings(BaseModel):
    ENV_TYPE: Literal['production'] = 'production'
    DEBUG: bool = False

class DevSettings(BaseModel):
    ENV_TYPE: Literal['development'] = 'development'
    DEBUG: bool = True

class StageSettings(BaseModel):
    ENV_TYPE: Literal['staging'] = 'staging'
    DEBUG: bool = True

EnvSettings = Annotated[
    ProdSettings | DevSettings | StageSettings,
    Field(discriminator="ENV_TYPE")
]

class WraithOpt(BaseModel):
    """
    CLI flags passed into MuseTalk.
    """
    fps: int = 50
    batch_size: int = 16
    stride_left_size: int = 10
    stride_right_size: int = 10

    @property
    def chunk(self) -> int:
        return 16000 // self.fps

    @property
    def frame_bytes(self) -> int:
        return self.chunk * 2


class LiveWraithConfig(BaseSettings):
    """
    The LiveWraith configuration class.
    """

    model_config = SettingsConfigDict(
        yaml_file="/aiphish/config/config.yaml",
        env_file_encoding="utf-8",
        env_file=".env",
        secrets_dir="/run/secrets",
        env_prefix="AIPHISH_",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSettingsSource(settings_cls),
        )
    
    ENV: Annotated[
        EnvSettings,
        Field(
            default_factory=DevSettings,
            validation_alias=AliasChoices("ENVIRONMENT"),
        )
    ]

    SECRETS_DIR: str = "/run/secrets"

    API_KEYS: list[str] = []

    CORS_ORIGINS: list[str] = []

    OPT: WraithOpt

    @computed_field
    @property
    def DEBUG(self) -> bool:
        """
        Accepts DEBUG env variable directly instead of nesting it.
        """
        return self.ENV.DEBUG
    
    @field_validator("ENV", mode="before")
    @classmethod
    def _coerce_env(cls, v):
        """
        Accepts setting ENV type directly instead of through env_type.
        """
        if isinstance(v, str):
            return {"ENV_TYPE": v}
        return v