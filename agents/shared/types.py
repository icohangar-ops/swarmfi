"""SwarmFi Data Types

Pydantic models for all data structures used across the agent system.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Types of agents in the SwarmFi system."""

    PRICE = "PRICE"
    RISK = "RISK"
    MARKET_MAKER = "MARKET_MAKER"
    RESOLUTION = "RESOLUTION"


class AgentStatus(str, Enum):
    """Operational status of an agent."""

    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    ERROR = "ERROR"
    SYNCHRONIZING = "SYNCHRONIZING"


class SignalType(str, Enum):
    """Types of stigmergy signals."""

    PRICE_UPDATE = "PRICE_UPDATE"
    RISK_ALERT = "RISK_ALERT"
    CONSENSUS_REACHED = "CONSENSUS_REACHED"
    REBALANCE_REQUEST = "REBALANCE_REQUEST"
    MARKET_EVENT = "MARKET_EVENT"
    HEARTBEAT = "HEARTBEAT"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"


class AgentInfo(BaseModel):
    """Information about a registered agent.

    Attributes:
        name: Human-readable agent name.
        agent_type: Category of agent.
        address: Unique identifier / wallet address.
        status: Current operational status.
        reputation: Reputation score (0.0 to 1.0), affects consensus weight.
        uptime_seconds: Total uptime in seconds.
        last_heartbeat: Unix timestamp of last heartbeat.
        metadata: Additional agent-specific metadata.
    """

    name: str
    agent_type: AgentType
    address: str
    status: AgentStatus = AgentStatus.ACTIVE
    reputation: float = Field(default=0.5, ge=0.0, le=1.0)
    uptime_seconds: float = 0.0
    last_heartbeat: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PriceSubmission(BaseModel):
    """A price data submission from an agent.

    Attributes:
        asset_pair: Trading pair (e.g. "BTC/USDT").
        price: Price value in quote currency.
        confidence: Agent's confidence in this price (0.0 to 1.0).
        source: Data source identifier (e.g. "coingecko", "dex", "news").
        agent_address: Address of the submitting agent.
        timestamp: Unix timestamp of when data was fetched.
        volume_24h: Optional 24h volume for context.
        metadata: Additional data about the submission.
    """

    asset_pair: str
    price: float = Field(gt=0.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    source: str
    agent_address: str
    timestamp: float = Field(default_factory=time.time)
    volume_24h: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RiskAssessment(BaseModel):
    """A risk assessment from a risk agent.

    Attributes:
        asset_pair: Trading pair being assessed.
        volatility_score: Volatility metric (annualized, 0.0 to 1.0+).
        correlation_score: Cross-asset correlation (-1.0 to 1.0).
        liquidation_risk: Liquidation risk score (0.0 to 1.0).
        agent_address: Address of the assessing agent.
        timestamp: Unix timestamp of the assessment.
        horizon_minutes: Time horizon of the assessment.
        metadata: Additional risk data.
    """

    asset_pair: str
    volatility_score: float = Field(default=0.0, ge=0.0)
    correlation_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    liquidation_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    agent_address: str
    timestamp: float = Field(default_factory=time.time)
    horizon_minutes: int = Field(default=60, gt=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MarketOrder(BaseModel):
    """An order placed by a market maker agent.

    Attributes:
        market_id: Identifier of the prediction market.
        outcome: Which outcome token to trade.
        side: "BUY" or "SELL".
        amount: Amount of outcome tokens.
        price: Price per outcome token.
        agent_address: Address of the market maker agent.
        timestamp: Unix timestamp of the order.
    """

    market_id: str
    outcome: str
    side: str = Field(pattern=r"^(BUY|SELL)$")
    amount: float = Field(gt=0.0)
    price: float = Field(gt=0.0)
    agent_address: str
    timestamp: float = Field(default_factory=time.time)


class StigmergySignal(BaseModel):
    """A signal deposited in the stigmergy field.

    Agents communicate indirectly by depositing signals that other
    agents can sense, similar to pheromone trails in ant colonies.

    Attributes:
        signal_type: Category of the signal.
        from_agent: Address of the depositing agent.
        data: The signal payload (arbitrary data).
        strength: Current signal strength (decays over time).
        target_agents: List of agent types that should sense this signal.
            Empty means all agents.
        decay_rate: How fast this signal decays per tick.
        timestamp: Unix timestamp when the signal was deposited.
        ttl_seconds: Time-to-live in seconds before signal is removed.
        id: Unique signal identifier.
    """

    signal_type: SignalType
    from_agent: str
    data: Dict[str, Any] = Field(default_factory=dict)
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    target_agents: List[AgentType] = Field(default_factory=list)
    decay_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)
    ttl_seconds: float = Field(default=300.0, gt=0.0)
    id: str = ""

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if not self.id:
            self.id = f"sig_{self.from_agent}_{self.signal_type.value}_{int(self.timestamp * 1000)}"


class ConsensusResult(BaseModel):
    """Result of the swarm consensus computation.

    Attributes:
        asset_pair: Trading pair the consensus is for.
        consensus_price: The agreed-upon price.
        participating_agents: List of agent addresses that contributed.
        confidence: Overall confidence in the consensus (0.0 to 1.0).
        timestamp: Unix timestamp of when consensus was reached.
        std_deviation: Standard deviation of submissions.
        num_outliers: Number of submissions flagged as outliers.
        weighted_median: The weighted median value used.
    """

    asset_pair: str
    consensus_price: float = Field(gt=0.0)
    participating_agents: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)
    std_deviation: float = 0.0
    num_outliers: int = 0
    weighted_median: float = 0.0


class RebalanceRecommendation(BaseModel):
    """A vault rebalance recommendation from an agent.

    Attributes:
        vault_id: Identifier of the vault to rebalance.
        from_asset: Asset to decrease.
        to_asset: Asset to increase.
        amount: Amount to rebalance.
        reason: Human-readable explanation.
        urgency: How urgently this should be executed (0.0 to 1.0).
        agent_address: Address of the recommending agent.
        timestamp: Unix timestamp of the recommendation.
    """

    vault_id: str
    from_asset: str
    to_asset: str
    amount: float = Field(gt=0.0)
    reason: str
    urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    agent_address: str
    timestamp: float = Field(default_factory=time.time)


class TxResponse(BaseModel):
    """Response from a blockchain transaction submission.

    Attributes:
        success: Whether the transaction succeeded.
        tx_hash: Transaction hash.
        height: Block height.
        gas_used: Gas consumed.
        error: Error message if the transaction failed.
        data: Additional response data.
    """

    success: bool = True
    tx_hash: str = ""
    height: int = 0
    gas_used: int = 0
    error: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class HealthCheck(BaseModel):
    """Health check result for an agent.

    Attributes:
        agent_address: Address of the agent.
        healthy: Whether the agent is healthy.
        latency_ms: Response latency in milliseconds.
        error: Error message if unhealthy.
        last_heartbeat_age_seconds: Seconds since last heartbeat.
        timestamp: When the health check was performed.
    """

    agent_address: str
    healthy: bool = True
    latency_ms: float = 0.0
    error: Optional[str] = None
    last_heartbeat_age_seconds: float = 0.0
    timestamp: float = Field(default_factory=time.time)


class MarketState(BaseModel):
    """Current state of a prediction market.

    Attributes:
        market_id: Unique market identifier.
        question: Market question / description.
        outcomes: List of possible outcomes.
        prices: Current prices for each outcome.
        liquidity: Total liquidity in the market.
        volume_24h: 24-hour trading volume.
        resolution_time: Unix timestamp of planned resolution.
        resolved: Whether the market has been resolved.
        winning_outcome: The winning outcome (if resolved).
    """

    market_id: str
    question: str
    outcomes: List[str]
    prices: Dict[str, float] = Field(default_factory=dict)
    liquidity: float = 0.0
    volume_24h: float = 0.0
    resolution_time: Optional[float] = None
    resolved: bool = False
    winning_outcome: Optional[str] = None
