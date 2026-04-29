"""Application configuration with YAML + .env layering.

Precedence (highest to lowest):
  1. init kwargs
  2. environment variables
  3. .env file
  4. env.yaml file
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource


class ModelsConfig(BaseSettings):
    """LLM model routing."""

    model_config = SettingsConfigDict(extra="ignore")

    buyer_model: str = Field(default="openai/gpt-4o")
    seller_model: str = Field(default="anthropic/claude-3-5-sonnet-20241022")
    judge_model: str = Field(default="openai/gpt-4o-mini")
    max_tokens: int = Field(default=4096, ge=256)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class SimulationConfig(BaseSettings):
    """Simulation parameters."""

    model_config = SettingsConfigDict(extra="ignore")

    seed: int = Field(default=42)
    dyads_per_cell: int = Field(default=30, ge=1)
    max_negotiation_turns: int = Field(default=3, ge=1, le=10)
    autonomy: Literal["full_auto", "checkpoint_at_decision", "audit_each_step"] = Field(
        default="full_auto"
    )


class CatalogConfig(BaseSettings):
    """Product catalog fetcher settings."""

    model_config = SettingsConfigDict(extra="ignore")

    fetch_timeout_s: int = Field(default=30, ge=5)
    max_pdf_pages: int = Field(default=20, ge=1)


class ReportingConfig(BaseSettings):
    """Report generation settings."""

    model_config = SettingsConfigDict(extra="ignore")

    auto_open: bool = Field(default=False)


class AppConfig(BaseSettings):
    """Root configuration object."""

    model_config = SettingsConfigDict(
        yaml_file=["env.yaml"],
        yaml_file_encoding="utf-8",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)

    # Provider API keys (sourced from .env only)
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    google_api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")

    models: ModelsConfig = Field(default_factory=ModelsConfig)
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    catalog: CatalogConfig = Field(default_factory=CatalogConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )


@lru_cache
def get_config() -> AppConfig:
    """Return the cached application configuration."""
    return AppConfig()
