"""SwarmFi Configuration

Manages all configuration through environment variables and YAML config files.
Uses Pydantic Settings for validation and type safety.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContractAddresses(BaseSettings):
    """Smart contract addresses for SwarmFi on Initia."""

    oracle: str = Field(default="initia1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq4kqxw", description="Oracle contract address")
    market: str = Field(default="initia1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq5kqxw", description="Market contract address")
    vault: str = Field(default="initia1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq6kqxw", description="Vault contract address")


class AgentConfig(BaseSettings):
    """Configuration for a specific agent type."""

    enabled: bool = Field(default=True, description="Whether this agent is enabled")
    interval_seconds: int = Field(default=30, description="Polling interval in seconds")
    max_retries: int = Field(default=3, description="Max retry attempts on failure")
    timeout_seconds: int = Field(default=10, description="Request timeout in seconds")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific extra config")


class Settings(BaseSettings):
    """SwarmFi Agent System Settings.

    Loads from environment variables with sensible defaults for testnet.
    Override via .env file or environment variables.

    Attributes:
        initia_rpc_url: Initia RPC endpoint URL.
        initia_chain_id: Initia chain identifier.
        contracts: Smart contract addresses.
        agent_private_key: Private key for signing transactions (hex).
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        consensus_threshold: Fraction (0-1) of agents needed for consensus.
        stigmergy_decay_rate: Rate at which stigmergy signals decay per tick.
        demo_mode: Whether to run in demo mode (no blockchain needed).
        assets: List of asset pairs to track.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SWARMFI_",
        case_sensitive=False,
    )

    # Blockchain
    initia_rpc_url: str = Field(
        default="https://rpc.testnet.initia.xyz",
        description="Initia RPC endpoint URL",
        alias="INITIA_RPC_URL",
    )
    initia_chain_id: str = Field(
        default="initiation-1",
        description="Initia chain ID",
        alias="INITIA_CHAIN_ID",
    )

    # Contracts
    contracts: ContractAddresses = Field(default_factory=ContractAddresses)

    # Auth
    agent_private_key: str = Field(
        default="***REDACTED_PRIVATE_KEY***",
        description="Agent private key for signing (hex)",
        alias="AGENT_PRIVATE_KEY",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        alias="LOG_LEVEL",
    )

    # Consensus
    consensus_threshold: float = Field(
        default=0.67,
        ge=0.0,
        le=1.0,
        description="Fraction of agents needed for consensus",
        alias="CONSENSUS_THRESHOLD",
    )
    outlier_deviation: float = Field(
        default=0.05,
        ge=0.0,
        description="Deviation threshold to flag outlier submissions",
    )

    # Stigmergy
    stigmergy_decay_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Signal decay rate per tick (0 = no decay, 1 = instant)",
        alias="STIGMERGY_DECAY_RATE",
    )
    stigmergy_max_signals: int = Field(
        default=1000,
        ge=10,
        description="Maximum signals stored in the stigmergy field",
    )

    # Demo mode
    demo_mode: bool = Field(
        default=False,
        description="Run in demo mode without blockchain connection",
    )

    # Assets
    assets: List[str] = Field(
        default=["BTC/USDT", "ETH/USDT", "INIT/USDT"],
        description="Asset pairs to track",
    )

    # Agent configs
    price_agent_config: AgentConfig = Field(default_factory=lambda: AgentConfig(interval_seconds=15))
    risk_agent_config: AgentConfig = Field(default_factory=lambda: AgentConfig(interval_seconds=30))
    market_maker_agent_config: AgentConfig = Field(default_factory=lambda: AgentConfig(interval_seconds=20))
    resolution_agent_config: AgentConfig = Field(default_factory=lambda: AgentConfig(interval_seconds=60))

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return v_upper

    @classmethod
    def from_yaml(cls, path: str | Path) -> Settings:
        """Load settings from a YAML config file.

        YAML values override defaults but environment variables
        take the highest precedence.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            A Settings instance with merged configuration.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r") as f:
            raw = yaml.safe_load(f) or {}

        # Flatten nested YAML into flat dict for Pydantic
        flat: Dict[str, Any] = {}
        for key, value in raw.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat[f"{key}_{sub_key}"] = sub_value
            else:
                flat[key] = value

        return cls(**flat)

    def get_agent_config(self, agent_type: str) -> AgentConfig:
        """Get configuration for a specific agent type.

        Args:
            agent_type: One of 'price', 'risk', 'market_maker', 'resolution'.

        Returns:
            AgentConfig for the specified agent type.
        """
        mapping = {
            "price": self.price_agent_config,
            "risk": self.risk_agent_config,
            "market_maker": self.market_maker_agent_config,
            "resolution": self.resolution_agent_config,
        }
        return mapping.get(agent_type, AgentConfig())
