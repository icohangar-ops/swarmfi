"""SwarmFi Consensus Module

Implements weighted median consensus with adversarial validation.

The swarm reaches consensus through a multi-step process:
1. Collect all agent submissions for an asset pair
2. Weight by agent reputation scores
3. Compute weighted median as consensus value
4. Identify outliers (deviation > threshold) as potential adversarial agents
5. If outlier count > threshold, flag for investigation
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from shared.logger import COLORS, get_logger
from shared.types import (
    AgentInfo,
    ConsensusResult,
    PriceSubmission,
    RiskAssessment,
)

logger = get_logger("CONSENSUS")


class SwarmConsensus:
    """Achieves consensus through weighted median with adversarial validation.

    This module implements a Byzantine-fault-tolerant consensus mechanism
    inspired by swarm intelligence. Agents with higher reputation have more
    influence on the final consensus value. Outlier detection helps identify
    potentially malicious or malfunctioning agents.

    Attributes:
        threshold: Minimum fraction of agents needed for valid consensus.
        outlier_deviation: Fraction deviation to flag outlier submissions.
        min_submissions: Minimum number of submissions required.
    """

    def __init__(
        self,
        threshold: float = 0.67,
        outlier_deviation: float = 0.05,
        min_submissions: int = 2,
    ) -> None:
        """Initialize the consensus engine.

        Args:
            threshold: Fraction of agents that must agree (0.0 to 1.0).
            outlier_deviation: Deviation from consensus to flag outlier (0.0 to 1.0).
            min_submissions: Minimum submissions needed to compute consensus.
        """
        self.threshold = threshold
        self.outlier_deviation = outlier_deviation
        self.min_submissions = min_submissions
        self._history: List[ConsensusResult] = []

    def compute_consensus(
        self,
        submissions: List[PriceSubmission],
        agents: Optional[List[AgentInfo]] = None,
    ) -> Optional[ConsensusResult]:
        """Compute weighted median consensus from price submissions.

        Process:
        1. Filter submissions by asset pair
        2. Build weight map from agent reputations
        3. Compute weighted median
        4. Detect and flag outliers
        5. Calculate confidence score
        6. Return consensus result

        Args:
            submissions: List of price submissions from agents.
            agents: List of agent info for reputation weighting.
                If None, all agents get equal weight.

        Returns:
            ConsensusResult if valid consensus reached, None otherwise.
        """
        if len(submissions) < self.min_submissions:
            logger.warning(
                f"Cannot compute consensus: only {len(submissions)} submissions "
                f"(min={self.min_submissions})"
            )
            return None

        # Group by asset pair
        by_pair: Dict[str, List[PriceSubmission]] = {}
        for sub in submissions:
            by_pair.setdefault(sub.asset_pair, []).append(sub)

        results: List[ConsensusResult] = []
        for pair, pair_subs in by_pair.items():
            if len(pair_subs) < self.min_submissions:
                logger.debug(f"Skipping {pair}: insufficient submissions ({len(pair_subs)})")
                continue

            result = self._compute_pair_consensus(pair, pair_subs, agents)
            if result:
                results.append(result)

        if not results:
            return None

        # Return the first result (usually only one pair in practice)
        result = results[0]
        self._history.append(result)
        return result

    def _compute_pair_consensus(
        self,
        asset_pair: str,
        submissions: List[PriceSubmission],
        agents: Optional[List[AgentInfo]] = None,
    ) -> Optional[ConsensusResult]:
        """Compute consensus for a single asset pair.

        Args:
            asset_pair: The trading pair.
            submissions: Submissions for this pair.
            agents: Agent info for weighting.

        Returns:
            ConsensusResult or None.
        """
        prices = np.array([s.price for s in submissions])
        confidences = np.array([s.confidence for s in submissions])

        # Build weights from agent reputations
        weights = self._get_submission_weights(submissions, agents)

        # Compute weighted median
        weighted_median = self._weighted_median(prices, weights)
        std_dev = float(np.std(prices))

        # Identify outliers
        outliers = self._identify_outliers(submissions, weighted_median)

        # Filter out outliers and recompute if necessary
        if outliers and len(submissions) - len(outliers) >= self.min_submissions:
            clean_subs = [s for s in submissions if s not in outliers]
            clean_prices = np.array([s.price for s in clean_subs])
            clean_weights = self._get_submission_weights(clean_subs, agents)
            weighted_median = self._weighted_median(clean_prices, clean_weights)
            std_dev = float(np.std(clean_prices))
            submissions = clean_subs

        # Calculate confidence
        # Higher when: more submissions, lower std dev, higher avg confidence
        n_subs = len(submissions)
        avg_confidence = float(np.mean([s.confidence for s in submissions]))
        participation_factor = min(n_subs / 5.0, 1.0)  # Max out at 5 agents
        precision_factor = max(0.0, 1.0 - std_dev / weighted_median) if weighted_median > 0 else 0.0

        overall_confidence = (
            0.3 * participation_factor
            + 0.4 * precision_factor
            + 0.3 * avg_confidence
        )

        participating = [s.agent_address for s in submissions]

        result = ConsensusResult(
            asset_pair=asset_pair,
            consensus_price=round(weighted_median, 8),
            participating_agents=participating,
            confidence=round(overall_confidence, 4),
            timestamp=time.time(),
            std_deviation=round(std_dev, 8),
            num_outliers=len(outliers),
            weighted_median=round(weighted_median, 8),
        )

        logger.info(
            f"Consensus for {asset_pair}: "
            f"price={weighted_median:.4f}, "
            f"confidence={overall_confidence:.2%}, "
            f"agents={n_subs}, "
            f"outliers={len(outliers)}, "
            f"std={std_dev:.6f}"
        )

        return result

    def compute_risk_consensus(
        self,
        assessments: List[RiskAssessment],
        agents: Optional[List[AgentInfo]] = None,
    ) -> Dict[str, float]:
        """Compute consensus risk scores from multiple assessments.

        Averages risk scores weighted by agent reputation, providing a
        more robust risk assessment than any single agent.

        Args:
            assessments: List of risk assessments from agents.
            agents: Agent info for reputation weighting.

        Returns:
            Dictionary mapping risk metric names to consensus values.
        """
        if not assessments:
            return {}

        # Group by asset pair
        by_pair: Dict[str, List[RiskAssessment]] = {}
        for a in assessments:
            by_pair.setdefault(a.asset_pair, []).append(a)

        # Use the first pair's results (typically all assessments for same pair)
        pair_assessments = list(by_pair.values())[0] if by_pair else []
        if not pair_assessments:
            return {}

        weights = self._get_risk_weights(pair_assessments, agents)

        result: Dict[str, float] = {}
        metrics = ["volatility_score", "correlation_score", "liquidation_risk"]

        for metric in metrics:
            values = [getattr(a, metric) for a in pair_assessments]
            if not values:
                continue
            weighted_avg = sum(v * w for v, w in zip(values, weights)) / sum(weights)
            result[metric] = round(weighted_avg, 4)

        asset_pair = pair_assessments[0].asset_pair
        logger.info(
            f"Risk consensus for {asset_pair}: {result}"
        )

        return result

    def validate_submission(
        self,
        submission: PriceSubmission,
        known_range: Tuple[float, float],
    ) -> bool:
        """Validate a single price submission against known range.

        Used as a quick sanity check before including a submission
        in consensus computation.

        Args:
            submission: The price submission to validate.
            known_range: Tuple of (min_price, max_price).

        Returns:
            True if the submission is within bounds, False otherwise.
        """
        min_price, max_price = known_range

        if submission.price < min_price or submission.price > max_price:
            logger.warning(
                f"Invalid submission from {submission.agent_address[:12]}: "
                f"price={submission.price} outside range [{min_price}, {max_price}]"
            )
            return False

        if submission.confidence < 0.0 or submission.confidence > 1.0:
            logger.warning(
                f"Invalid confidence from {submission.agent_address[:12]}: "
                f"confidence={submission.confidence}"
            )
            return False

        return True

    def get_agent_weights(
        self,
        agents: List[AgentInfo],
    ) -> Dict[str, float]:
        """Get normalized reputation weights for agents.

        Converts raw reputation scores to normalized weights that sum to 1.0.

        Args:
            agents: List of agent info objects.

        Returns:
            Dictionary mapping agent addresses to normalized weights.
        """
        if not agents:
            return {}

        raw_weights = {a.address: a.reputation for a in agents}
        total = sum(raw_weights.values())

        if total == 0:
            # Equal weights if all reputations are zero
            n = len(agents)
            return {a.address: 1.0 / n for a in agents}

        return {addr: w / total for addr, w in raw_weights.items()}

    # ─── Private Methods ───────────────────────────────────────────────

    def _get_submission_weights(
        self,
        submissions: List[PriceSubmission],
        agents: Optional[List[AgentInfo]],
    ) -> np.ndarray:
        """Build weight array for submissions.

        Args:
            submissions: Price submissions.
            agents: Agent info for reputation weighting.

        Returns:
            Numpy array of weights.
        """
        if not agents:
            return np.ones(len(submissions)) / len(submissions)

        rep_map = {a.address: a.reputation for a in agents}
        weights = []
        for sub in submissions:
            rep = rep_map.get(sub.agent_address, 0.5)
            weights.append(rep)

        total = sum(weights)
        if total == 0:
            return np.ones(len(submissions)) / len(submissions)

        return np.array([w / total for w in weights])

    def _get_risk_weights(
        self,
        assessments: List[RiskAssessment],
        agents: Optional[List[AgentInfo]],
    ) -> np.ndarray:
        """Build weight array for risk assessments.

        Args:
            assessments: Risk assessments.
            agents: Agent info for reputation weighting.

        Returns:
            Numpy array of weights.
        """
        if not agents:
            return np.ones(len(assessments)) / len(assessments)

        rep_map = {a.address: a.reputation for a in agents}
        weights = []
        for a in assessments:
            rep = rep_map.get(a.agent_address, 0.5)
            weights.append(rep)

        total = sum(weights)
        if total == 0:
            return np.ones(len(assessments)) / len(assessments)

        return np.array([w / total for w in weights])

    def _weighted_median(
        self,
        values: np.ndarray,
        weights: np.ndarray,
    ) -> float:
        """Compute the weighted median of values.

        Args:
            values: Array of values.
            weights: Array of corresponding weights.

        Returns:
            Weighted median value.
        """
        if len(values) == 0:
            return 0.0

        if len(values) == 1:
            return float(values[0])

        # Sort values by weight
        sorted_indices = np.argsort(values)
        sorted_values = values[sorted_indices]
        sorted_weights = weights[sorted_indices]

        cumulative_weight = np.cumsum(sorted_weights)
        half_weight = cumulative_weight[-1] / 2.0

        # Find the median
        median_idx = np.searchsorted(cumulative_weight, half_weight)
        median_idx = min(median_idx, len(sorted_values) - 1)

        return float(sorted_values[median_idx])

    def _identify_outliers(
        self,
        submissions: List[PriceSubmission],
        median: float,
    ) -> List[PriceSubmission]:
        """Identify outlier submissions that deviate too far from median.

        Args:
            submissions: Price submissions to check.
            median: The consensus median price.

        Returns:
            List of outlier submissions.
        """
        if median == 0:
            return []

        outliers: List[PriceSubmission] = []
        threshold = self.outlier_deviation

        for sub in submissions:
            deviation = abs(sub.price - median) / median
            if deviation > threshold:
                outliers.append(sub)
                logger.debug(
                    f"Outlier detected: {sub.agent_address[:12]} "
                    f"price={sub.price:.4f} median={median:.4f} "
                    f"deviation={deviation:.2%}"
                )

        if outliers:
            logger.warning(
                f"{len(outliers)} outlier(s) detected out of {len(submissions)} submissions"
            )

        return outliers

    def get_consensus_history(self, limit: int = 100) -> List[ConsensusResult]:
        """Get recent consensus results.

        Args:
            limit: Maximum number of results to return.

        Returns:
            List of recent consensus results.
        """
        return self._history[-limit:]

    def get_average_confidence(self, window: int = 10) -> float:
        """Get average confidence over recent consensus results.

        Args:
            window: Number of recent results to average.

        Returns:
            Average confidence score.
        """
        recent = self._history[-window:]
        if not recent:
            return 0.0
        return sum(r.confidence for r in recent) / len(recent)
