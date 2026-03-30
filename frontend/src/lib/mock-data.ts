// ============================================================
// SwarmFi Mock Data — comprehensive demo data for all pages
// ============================================================

// ---- Types ----
export interface PredictionMarket {
  id: string;
  title: string;
  description: string;
  outcomes: { name: string; probability: number }[];
  totalVolume: number;
  timeRemaining: string;
  participants: number;
  status: "active" | "resolved" | "upcoming";
  category: string;
  myPosition?: { outcome: string; amount: number; pnl: number };
  priceHistory: { time: string; yes: number; no: number }[];
}

export interface Vault {
  id: string;
  name: string;
  strategy: string;
  description: string;
  tvl: number;
  returns24h: number;
  returns7d: number;
  returns30d: number;
  riskScore: number;
  agentCount: number;
  assetAllocation: { name: string; value: number; color: string }[];
  performanceHistory: { date: string; value: number }[];
  rebalanceHistory: { date: string; from: string; to: string; amount: number }[];
}

export interface Agent {
  id: string;
  name: string;
  type: "Price Oracle" | "Risk Analyzer" | "Market Maker" | "Resolution";
  status: "active" | "idle" | "maintenance";
  accuracy: number;
  uptime: number;
  decisions24h: number;
  consensusRate: number;
  recentDecisions: { time: string; action: string; outcome: string }[];
  performanceMetrics: { metric: string; value: string }[];
}

export interface Transaction {
  id: string;
  type: "trade" | "deposit" | "withdraw" | "reward" | "market_create";
  description: string;
  amount: number;
  token: string;
  timestamp: string;
  status: "confirmed" | "pending" | "failed";
}

export interface SwarmEvent {
  time: string;
  agentCount: number;
  consensusLevel: number;
  signalStrength: number;
  coordinationEvents: number;
}

export interface PriceFeed {
  time: string;
  price: number;
  volume: number;
}

// ---- Prediction Markets ----
export const predictionMarkets: PredictionMarket[] = [
  {
    id: "pm-1",
    title: "Will BTC reach $100K by end of Q2 2025?",
    description: "Bitcoin price prediction market based on aggregated AI oracle signals.",
    outcomes: [
      { name: "Yes", probability: 0.62 },
      { name: "No", probability: 0.38 },
    ],
    totalVolume: 2450000,
    timeRemaining: "43d 12h",
    participants: 12847,
    status: "active",
    category: "Crypto Price",
    myPosition: { outcome: "Yes", amount: 5000, pnl: 1240 },
    priceHistory: [
      { time: "Day 1", yes: 0.45, no: 0.55 },
      { time: "Day 2", yes: 0.48, no: 0.52 },
      { time: "Day 3", yes: 0.51, no: 0.49 },
      { time: "Day 4", yes: 0.55, no: 0.45 },
      { time: "Day 5", yes: 0.53, no: 0.47 },
      { time: "Day 6", yes: 0.58, no: 0.42 },
      { time: "Day 7", yes: 0.62, no: 0.38 },
    ],
  },
  {
    id: "pm-2",
    title: "Will ETH flip BTC in market cap by 2026?",
    description: "Long-term market cap comparison between Ethereum and Bitcoin.",
    outcomes: [
      { name: "Yes", probability: 0.18 },
      { name: "No", probability: 0.82 },
    ],
    totalVolume: 1890000,
    timeRemaining: "180d 0h",
    participants: 8932,
    status: "active",
    category: "Crypto Price",
    myPosition: { outcome: "No", amount: 3000, pnl: 450 },
    priceHistory: [
      { time: "Day 1", yes: 0.22, no: 0.78 },
      { time: "Day 2", yes: 0.20, no: 0.80 },
      { time: "Day 3", yes: 0.19, no: 0.81 },
      { time: "Day 4", yes: 0.21, no: 0.79 },
      { time: "Day 5", yes: 0.18, no: 0.82 },
      { time: "Day 6", yes: 0.17, no: 0.83 },
      { time: "Day 7", yes: 0.18, no: 0.82 },
    ],
  },
  {
    id: "pm-3",
    title: "Will Initia TVL exceed $500M by June 2025?",
    description: "Total Value Locked prediction for the Initia ecosystem.",
    outcomes: [
      { name: "Yes", probability: 0.41 },
      { name: "No", probability: 0.59 },
    ],
    totalVolume: 890000,
    timeRemaining: "72d 8h",
    participants: 5421,
    status: "active",
    category: "DeFi",
    priceHistory: [
      { time: "Day 1", yes: 0.35, no: 0.65 },
      { time: "Day 2", yes: 0.37, no: 0.63 },
      { time: "Day 3", yes: 0.39, no: 0.61 },
      { time: "Day 4", yes: 0.42, no: 0.58 },
      { time: "Day 5", yes: 0.40, no: 0.60 },
      { time: "Day 6", yes: 0.41, no: 0.59 },
      { time: "Day 7", yes: 0.41, no: 0.59 },
    ],
  },
  {
    id: "pm-4",
    title: "Will the Fed cut rates in June 2025?",
    description: "Federal Reserve interest rate decision prediction.",
    outcomes: [
      { name: "Cut", probability: 0.73 },
      { name: "Hold", probability: 0.22 },
      { name: "Hike", probability: 0.05 },
    ],
    totalVolume: 5420000,
    timeRemaining: "15d 6h",
    participants: 34521,
    status: "active",
    category: "Macro",
    myPosition: { outcome: "Cut", amount: 10000, pnl: 3200 },
    priceHistory: [
      { time: "Day 1", yes: 0.65, no: 0.35 },
      { time: "Day 2", yes: 0.68, no: 0.32 },
      { time: "Day 3", yes: 0.70, no: 0.30 },
      { time: "Day 4", yes: 0.69, no: 0.31 },
      { time: "Day 5", yes: 0.71, no: 0.29 },
      { time: "Day 6", yes: 0.72, no: 0.28 },
      { time: "Day 7", yes: 0.73, no: 0.27 },
    ],
  },
  {
    id: "pm-5",
    title: "Will SOL outperform ETH in next 30 days?",
    description: "Relative performance prediction between Solana and Ethereum.",
    outcomes: [
      { name: "SOL Wins", probability: 0.55 },
      { name: "ETH Wins", probability: 0.45 },
    ],
    totalVolume: 1230000,
    timeRemaining: "28d 0h",
    participants: 7823,
    status: "active",
    category: "Crypto Price",
    priceHistory: [
      { time: "Day 1", yes: 0.50, no: 0.50 },
      { time: "Day 2", yes: 0.52, no: 0.48 },
      { time: "Day 3", yes: 0.54, no: 0.46 },
      { time: "Day 4", yes: 0.53, no: 0.47 },
      { time: "Day 5", yes: 0.56, no: 0.44 },
      { time: "Day 6", yes: 0.54, no: 0.46 },
      { time: "Day 7", yes: 0.55, no: 0.45 },
    ],
  },
  {
    id: "pm-6",
    title: "Will Uniswap v4 launch on Initia by Q3 2025?",
    description: "DeFi protocol deployment prediction.",
    outcomes: [
      { name: "Yes", probability: 0.28 },
      { name: "No", probability: 0.72 },
    ],
    totalVolume: 320000,
    timeRemaining: "90d 0h",
    participants: 2134,
    status: "active",
    category: "DeFi",
  },
  {
    id: "pm-7",
    title: "Will AI agents manage >$1B in DeFi by EOY 2025?",
    description: "Autonomous agent TVL prediction across all chains.",
    outcomes: [
      { name: "Yes", probability: 0.47 },
      { name: "No", probability: 0.53 },
    ],
    totalVolume: 2100000,
    timeRemaining: "245d 12h",
    participants: 15678,
    status: "active",
    category: "AI / DeFi",
    myPosition: { outcome: "Yes", amount: 8000, pnl: -1200 },
    priceHistory: [
      { time: "Day 1", yes: 0.52, no: 0.48 },
      { time: "Day 2", yes: 0.50, no: 0.50 },
      { time: "Day 3", yes: 0.48, no: 0.52 },
      { time: "Day 4", yes: 0.49, no: 0.51 },
      { time: "Day 5", yes: 0.47, no: 0.53 },
      { time: "Day 6", yes: 0.46, no: 0.54 },
      { time: "Day 7", yes: 0.47, no: 0.53 },
    ],
  },
  {
    id: "pm-8",
    title: "Did BTC dominance stay above 55% in Q1 2025?",
    description: "Resolved market — BTC dominance tracker.",
    outcomes: [
      { name: "Yes", probability: 1.0 },
      { name: "No", probability: 0.0 },
    ],
    totalVolume: 3450000,
    timeRemaining: "Expired",
    participants: 23456,
    status: "resolved",
    category: "Crypto Price",
    myPosition: { outcome: "Yes", amount: 15000, pnl: 4500 },
    priceHistory: [
      { time: "Day 1", yes: 0.60, no: 0.40 },
      { time: "Day 2", yes: 0.62, no: 0.38 },
      { time: "Day 3", yes: 0.65, no: 0.35 },
      { time: "Day 4", yes: 0.68, no: 0.32 },
      { time: "Day 5", yes: 0.70, no: 0.30 },
      { time: "Day 6", yes: 0.75, no: 0.25 },
      { time: "Day 7", yes: 1.0, no: 0.0 },
    ],
  },
  {
    id: "pm-9",
    title: "Will stETH depeg exceed 2% in 2025?",
    description: "Lido stETH depeg risk prediction.",
    outcomes: [
      { name: "Yes", probability: 0.12 },
      { name: "No", probability: 0.88 },
    ],
    totalVolume: 670000,
    timeRemaining: "247d 0h",
    participants: 4521,
    status: "active",
    category: "DeFi",
  },
  {
    id: "pm-10",
    title: "Will a major L2 suffer a chain halt in 2025?",
    description: "L2 network reliability prediction.",
    outcomes: [
      { name: "Yes", probability: 0.34 },
      { name: "No", probability: 0.66 },
    ],
    totalVolume: 980000,
    timeRemaining: "210d 0h",
    participants: 6789,
    status: "active",
    category: "Infrastructure",
    myPosition: { outcome: "No", amount: 2000, pnl: 680 },
  },
];

// ---- Vaults ----
export const vaults: Vault[] = [
  {
    id: "v-1",
    name: "Conservative Alpha",
    strategy: "Conservative",
    description:
      "Low-risk stablecoin yield with AI-optimized allocation across blue-chip DeFi protocols. Focuses on capital preservation with steady returns.",
    tvl: 45200000,
    returns24h: 0.04,
    returns7d: 0.28,
    returns30d: 1.12,
    riskScore: 2,
    agentCount: 3,
    assetAllocation: [
      { name: "USDC", value: 45, color: "#06B6D4" },
      { name: "USDT", value: 25, color: "#8B5CF6" },
      { name: "DAI", value: 20, color: "#10B981" },
      { name: "INIT", value: 10, color: "#F59E0B" },
    ],
    performanceHistory: [
      { date: "Jan", value: 100 },
      { date: "Feb", value: 100.3 },
      { date: "Mar", value: 100.8 },
      { date: "Apr", value: 101.1 },
      { date: "May", value: 101.5 },
      { date: "Jun", value: 101.9 },
      { date: "Jul", value: 102.3 },
    ],
    rebalanceHistory: [
      { date: "2025-03-15", from: "USDT", to: "USDC", amount: 2500000 },
      { date: "2025-03-28", from: "INIT", to: "DAI", amount: 800000 },
      { date: "2025-04-10", from: "DAI", to: "USDC", amount: 1200000 },
      { date: "2025-04-22", from: "USDC", to: "INIT", amount: 500000 },
      { date: "2025-05-05", from: "USDT", to: "DAI", amount: 1800000 },
    ],
  },
  {
    id: "v-2",
    name: "Balanced Growth",
    strategy: "Balanced",
    description:
      "Mixed asset strategy balancing crypto exposure with stable yields. AI agents dynamically adjust between volatile and stable assets based on market conditions.",
    tvl: 78900000,
    returns24h: 0.32,
    returns7d: 2.15,
    returns30d: 8.67,
    riskScore: 5,
    agentCount: 6,
    assetAllocation: [
      { name: "INIT", value: 30, color: "#06B6D4" },
      { name: "BTC", value: 25, color: "#F59E0B" },
      { name: "ETH", value: 20, color: "#8B5CF6" },
      { name: "USDC", value: 15, color: "#10B981" },
      { name: "SOL", value: 10, color: "#EF4444" },
    ],
    performanceHistory: [
      { date: "Jan", value: 100 },
      { date: "Feb", value: 102.5 },
      { date: "Mar", value: 105.1 },
      { date: "Apr", value: 103.8 },
      { date: "May", value: 106.2 },
      { date: "Jun", value: 107.9 },
      { date: "Jul", value: 108.7 },
    ],
    rebalanceHistory: [
      { date: "2025-03-12", from: "BTC", to: "USDC", amount: 5000000 },
      { date: "2025-03-25", from: "USDC", to: "ETH", amount: 3200000 },
      { date: "2025-04-08", from: "ETH", to: "INIT", amount: 4500000 },
      { date: "2025-04-20", from: "INIT", to: "BTC", amount: 2800000 },
      { date: "2025-05-03", from: "SOL", to: "USDC", amount: 1500000 },
      { date: "2025-05-15", from: "USDC", to: "BTC", amount: 3800000 },
    ],
  },
  {
    id: "v-3",
    name: "Aggressive Swarm",
    strategy: "Aggressive",
    description:
      "Maximum yield strategy leveraging AI swarm intelligence for aggressive market-making and arbitrage across multiple DEXs. Higher risk, higher reward.",
    tvl: 34500000,
    returns24h: 0.89,
    returns7d: 5.43,
    returns30d: 18.92,
    riskScore: 8,
    agentCount: 12,
    assetAllocation: [
      { name: "INIT", value: 35, color: "#06B6D4" },
      { name: "BTC", value: 20, color: "#F59E0B" },
      { name: "ETH", value: 15, color: "#8B5CF6" },
      { name: "Various L2s", value: 20, color: "#10B981" },
      { name: "Memecoins", value: 10, color: "#EF4444" },
    ],
    performanceHistory: [
      { date: "Jan", value: 100 },
      { date: "Feb", value: 106.2 },
      { date: "Mar", value: 112.8 },
      { date: "Apr", value: 108.4 },
      { date: "May", value: 114.1 },
      { date: "Jun", value: 117.5 },
      { date: "Jul", value: 118.9 },
    ],
    rebalanceHistory: [
      { date: "2025-03-10", from: "Memecoins", to: "BTC", amount: 2000000 },
      { date: "2025-03-18", from: "BTC", to: "Various L2s", amount: 3500000 },
      { date: "2025-04-01", from: "Various L2s", to: "INIT", amount: 4200000 },
      { date: "2025-04-15", from: "INIT", to: "Memecoins", amount: 1800000 },
      { date: "2025-04-28", from: "Memecoins", to: "ETH", amount: 2500000 },
      { date: "2025-05-10", from: "ETH", to: "Various L2s", amount: 3000000 },
      { date: "2025-05-22", from: "Various L2s", to: "BTC", amount: 2200000 },
    ],
  },
];

// ---- Agents ----
export const agents: Agent[] = [
  {
    id: "ag-1",
    name: "Nexus Oracle",
    type: "Price Oracle",
    status: "active",
    accuracy: 94.7,
    uptime: 99.9,
    decisions24h: 1247,
    consensusRate: 87,
    recentDecisions: [
      { time: "2m ago", action: "BTC Price Update", outcome: "$98,432" },
      { time: "5m ago", action: "ETH Price Update", outcome: "$3,847" },
      { time: "8m ago", action: "SOL Price Update", outcome: "$178.23" },
      { time: "12m ago", action: "INIT Price Update", outcome: "$2.45" },
    ],
    performanceMetrics: [
      { metric: "Avg Latency", value: "12ms" },
      { metric: "Data Sources", value: "23" },
      { metric: "Price Deviations", value: "0.02%" },
      { metric: "Confidence Score", value: "0.97" },
    ],
  },
  {
    id: "ag-2",
    name: "Sentinel Risk",
    type: "Risk Analyzer",
    status: "active",
    accuracy: 91.3,
    uptime: 99.7,
    decisions24h: 843,
    consensusRate: 82,
    recentDecisions: [
      { time: "3m ago", action: "Risk Alert: BTC Volatility", outcome: "Medium" },
      { time: "7m ago", action: "Vault Rebalance Rec", outcome: "Approved" },
      { time: "15m ago", action: "Liquidation Monitor", outcome: "Safe" },
      { time: "22m ago", action: "Correlation Update", outcome: "BTC-ETH: 0.87" },
    ],
    performanceMetrics: [
      { metric: "Risk Models", value: "8" },
      { metric: "Alerts Sent (24h)", value: "34" },
      { metric: "False Positives", value: "3.2%" },
      { metric: "VaR Accuracy", value: "96.1%" },
    ],
  },
  {
    id: "ag-3",
    name: "Arbitrex",
    type: "Market Maker",
    status: "active",
    accuracy: 88.9,
    uptime: 99.5,
    decisions24h: 3421,
    consensusRate: 79,
    recentDecisions: [
      { time: "30s ago", action: "Place Order: BTC/USDC", outcome: "Filled" },
      { time: "1m ago", action: "Update Spread: ETH/INIT", outcome: "0.3%" },
      { time: "2m ago", action: "Arb: INIT-USDC", outcome: "+$2,340" },
      { time: "3m ago", action: "LP Rebalance", outcome: "Optimal" },
    ],
    performanceMetrics: [
      { metric: "Trading Pairs", value: "47" },
      { metric: "Daily Volume", value: "$12.4M" },
      { metric: "Avg Spread", value: "0.12%" },
      { metric: "Slippage", value: "0.03%" },
    ],
  },
  {
    id: "ag-4",
    name: "Veritas",
    type: "Resolution",
    status: "active",
    accuracy: 97.2,
    uptime: 99.8,
    decisions24h: 156,
    consensusRate: 95,
    recentDecisions: [
      { time: "1h ago", action: "Resolve: BTC Dominance Q1", outcome: "YES" },
      { time: "3h ago", action: "Verify: Chain Halt", outcome: "No Incident" },
      { time: "6h ago", action: "Audit: Oracle Feed", outcome: "Pass" },
      { time: "12h ago", action: "Dispute: Market #42", outcome: "Rejected" },
    ],
    performanceMetrics: [
      { metric: "Markets Resolved", value: "1,247" },
      { metric: "Dispute Rate", value: "0.8%" },
      { metric: "Resolution Time", value: "2.3h avg" },
      { metric: "Data Points Used", value: "5.2M" },
    ],
  },
  {
    id: "ag-5",
    name: "CryptoSage",
    type: "Price Oracle",
    status: "active",
    accuracy: 92.1,
    uptime: 99.6,
    decisions24h: 987,
    consensusRate: 85,
    recentDecisions: [
      { time: "1m ago", action: "AVAX Price Update", outcome: "$42.18" },
      { time: "4m ago", action: "DOT Price Update", outcome: "$8.92" },
      { time: "9m ago", action: "ATOM Price Update", outcome: "$11.34" },
      { time: "15m ago", action: "TIA Price Update", outcome: "$5.67" },
    ],
    performanceMetrics: [
      { metric: "Avg Latency", value: "18ms" },
      { metric: "Data Sources", value: "31" },
      { metric: "Price Deviations", value: "0.03%" },
      { metric: "Confidence Score", value: "0.94" },
    ],
  },
  {
    id: "ag-6",
    name: "HedgeGuard",
    type: "Risk Analyzer",
    status: "active",
    accuracy: 89.8,
    uptime: 99.4,
    decisions24h: 623,
    consensusRate: 78,
    recentDecisions: [
      { time: "5m ago", action: "Hedge Ratio Update", outcome: "0.72" },
      { time: "12m ago", action: "Drawdown Alert", outcome: "Low Risk" },
      { time: "25m ago", action: "Delta Neutral Check", outcome: "Balanced" },
      { time: "40m ago", action: "Exposure Report", outcome: "Within Limits" },
    ],
    performanceMetrics: [
      { metric: "Risk Models", value: "6" },
      { metric: "Hedging Pairs", value: "12" },
      { metric: "Max Drawdown", value: "2.1%" },
      { metric: "Sharpe Ratio", value: "2.4" },
    ],
  },
  {
    id: "ag-7",
    name: "LiquidFlow",
    type: "Market Maker",
    status: "idle",
    accuracy: 86.4,
    uptime: 98.2,
    decisions24h: 0,
    consensusRate: 74,
    recentDecisions: [
      { time: "2h ago", action: "Standby Mode", outcome: "Low Liquidity" },
      { time: "4h ago", action: "Withdraw from INIT-USDC", outcome: "$450K" },
      { time: "6h ago", action: "Reduce Exposure", outcome: "Completed" },
    ],
    performanceMetrics: [
      { metric: "Trading Pairs", value: "32" },
      { metric: "Daily Volume", value: "$8.1M" },
      { metric: "Avg Spread", value: "0.15%" },
      { metric: "Inventory Risk", value: "Low" },
    ],
  },
  {
    id: "ag-8",
    name: "MetaMind",
    type: "Price Oracle",
    status: "active",
    accuracy: 93.5,
    uptime: 99.8,
    decisions24h: 1523,
    consensusRate: 88,
    recentDecisions: [
      { time: "30s ago", action: "Multi-chain Price", outcome: "24 chains" },
      { time: "2m ago", action: "Cross-chain Arb Signal", outcome: "0.4% diff" },
      { time: "5m ago", action: "Gas Oracle Update", outcome: "23 gwei avg" },
    ],
    performanceMetrics: [
      { metric: "Avg Latency", value: "8ms" },
      { metric: "Chains Covered", value: "24" },
      { metric: "Price Deviations", value: "0.01%" },
      { metric: "Confidence Score", value: "0.98" },
    ],
  },
  {
    id: "ag-9",
    name: "Aegis",
    type: "Risk Analyzer",
    status: "active",
    accuracy: 90.7,
    uptime: 99.3,
    decisions24h: 512,
    consensusRate: 81,
    recentDecisions: [
      { time: "8m ago", action: "Smart Contract Audit", outcome: "Safe" },
      { time: "20m ago", action: "Whale Monitor", outcome: "Normal" },
      { time: "35m ago", action: "Flash Loan Alert", outcome: "Detected & Logged" },
    ],
    performanceMetrics: [
      { metric: "Contracts Audited", value: "847" },
      { metric: "Vulnerabilities Found", value: "12" },
      { metric: "False Positives", value: "4.1%" },
      { metric: "Response Time", value: "0.8s" },
    ],
  },
  {
    id: "ag-10",
    name: "Oracle Prime",
    type: "Resolution",
    status: "maintenance",
    accuracy: 95.1,
    uptime: 97.8,
    decisions24h: 45,
    consensusRate: 92,
    recentDecisions: [
      { time: "30m ago", action: "System Update", outcome: "In Progress" },
      { time: "1h ago", action: "Model Retrain", outcome: "92% accuracy" },
      { time: "3h ago", action: "Data Validation", outcome: "Passed" },
    ],
    performanceMetrics: [
      { metric: "Markets Resolved", value: "834" },
      { metric: "Dispute Rate", value: "1.1%" },
      { metric: "Resolution Time", value: "3.1h avg" },
      { metric: "Data Points Used", value: "4.8M" },
    ],
  },
  {
    id: "ag-11",
    name: "DepthSeeker",
    type: "Market Maker",
    status: "active",
    accuracy: 87.2,
    uptime: 99.1,
    decisions24h: 2890,
    consensusRate: 76,
    recentDecisions: [
      { time: "45s ago", action: "Order: SOL/USDC", outcome: "Filled" },
      { time: "2m ago", action: "Inventory Check", outcome: "Balanced" },
      { time: "5m ago", action: "Spread Update", outcome: "0.08%" },
    ],
    performanceMetrics: [
      { metric: "Trading Pairs", value: "38" },
      { metric: "Daily Volume", value: "$9.7M" },
      { metric: "Avg Spread", value: "0.10%" },
      { metric: "Fill Rate", value: "94.2%" },
    ],
  },
  {
    id: "ag-12",
    name: "TruthEngine",
    type: "Resolution",
    status: "active",
    accuracy: 96.8,
    uptime: 99.9,
    decisions24h: 189,
    consensusRate: 94,
    recentDecisions: [
      { time: "45m ago", action: "Resolve: Fed Rate", outcome: "Pending" },
      { time: "2h ago", action: "Cross-verify", outcome: "3/3 oracles agree" },
      { time: "4h ago", action: "Escalation Review", outcome: "Dismissed" },
    ],
    performanceMetrics: [
      { metric: "Markets Resolved", value: "1,089" },
      { metric: "Dispute Rate", value: "0.5%" },
      { metric: "Resolution Time", value: "1.8h avg" },
      { metric: "Data Points Used", value: "6.1M" },
    ],
  },
];

// ---- Transactions ----
export const transactions: Transaction[] = [
  { id: "tx-1", type: "trade", description: "Buy YES — Will BTC reach $100K?", amount: 5000, token: "USDC", timestamp: "2 min ago", status: "confirmed" },
  { id: "tx-2", type: "reward", description: "Vault Yield — Balanced Growth", amount: 342.5, token: "INIT", timestamp: "15 min ago", status: "confirmed" },
  { id: "tx-3", type: "deposit", description: "Deposit to Conservative Alpha", amount: 25000, token: "USDC", timestamp: "1 hour ago", status: "confirmed" },
  { id: "tx-4", type: "trade", description: "Buy NO — ETH flip BTC?", amount: 3000, token: "USDC", timestamp: "2 hours ago", status: "confirmed" },
  { id: "tx-5", type: "withdraw", description: "Withdraw from Aggressive Swarm", amount: 15000, token: "USDC", timestamp: "3 hours ago", status: "confirmed" },
  { id: "tx-6", type: "market_create", description: "Create Market: AI Agent TVL", amount: 1000, token: "INIT", timestamp: "5 hours ago", status: "confirmed" },
  { id: "tx-7", type: "trade", description: "Buy YES — Fed rate cut?", amount: 10000, token: "USDC", timestamp: "6 hours ago", status: "confirmed" },
  { id: "tx-8", type: "reward", description: "Prediction Payout — BTC Dominance", amount: 4500, token: "USDC", timestamp: "8 hours ago", status: "confirmed" },
  { id: "tx-9", type: "deposit", description: "Deposit to Balanced Growth", amount: 50000, token: "INIT", timestamp: "12 hours ago", status: "confirmed" },
  { id: "tx-10", type: "trade", description: "Buy YES — AI agents manage $1B?", amount: 8000, token: "USDC", timestamp: "1 day ago", status: "confirmed" },
  { id: "tx-11", type: "withdraw", description: "Withdraw from Conservative Alpha", amount: 5000, token: "USDC", timestamp: "1 day ago", status: "confirmed" },
  { id: "tx-12", type: "reward", description: "Agent Staking Reward", amount: 127.8, token: "INIT", timestamp: "1 day ago", status: "confirmed" },
  { id: "tx-13", type: "trade", description: "Buy NO — stETH depeg?", amount: 2000, token: "USDC", timestamp: "2 days ago", status: "confirmed" },
  { id: "tx-14", type: "deposit", description: "Deposit to Aggressive Swarm", amount: 100000, token: "USDC", timestamp: "2 days ago", status: "confirmed" },
  { id: "tx-15", type: "trade", description: "Buy YES — Initia TVL $500M?", amount: 7000, token: "USDC", timestamp: "3 days ago", status: "confirmed" },
  { id: "tx-16", type: "market_create", description: "Create Market: L2 Chain Halt", amount: 500, token: "INIT", timestamp: "3 days ago", status: "confirmed" },
  { id: "tx-17", type: "reward", description: "Vault Yield — Conservative Alpha", amount: 89.2, token: "INIT", timestamp: "3 days ago", status: "confirmed" },
  { id: "tx-18", type: "trade", description: "Buy YES — SOL outperform ETH?", amount: 4500, token: "USDC", timestamp: "4 days ago", status: "confirmed" },
  { id: "tx-19", type: "withdraw", description: "Withdraw from Balanced Growth", amount: 20000, token: "INIT", timestamp: "5 days ago", status: "confirmed" },
  { id: "tx-20", type: "deposit", description: "Deposit to Conservative Alpha", amount: 75000, token: "USDC", timestamp: "7 days ago", status: "confirmed" },
];

// ---- Swarm Events ----
export const swarmEvents: SwarmEvent[] = [
  { time: "00:00", agentCount: 8, consensusLevel: 78, signalStrength: 65, coordinationEvents: 12 },
  { time: "02:00", agentCount: 9, consensusLevel: 82, signalStrength: 71, coordinationEvents: 18 },
  { time: "04:00", agentCount: 10, consensusLevel: 85, signalStrength: 68, coordinationEvents: 15 },
  { time: "06:00", agentCount: 11, consensusLevel: 88, signalStrength: 74, coordinationEvents: 22 },
  { time: "08:00", agentCount: 11, consensusLevel: 91, signalStrength: 82, coordinationEvents: 28 },
  { time: "10:00", agentCount: 12, consensusLevel: 89, signalStrength: 79, coordinationEvents: 25 },
  { time: "12:00", agentCount: 12, consensusLevel: 93, signalStrength: 88, coordinationEvents: 34 },
  { time: "14:00", agentCount: 12, consensusLevel: 90, signalStrength: 85, coordinationEvents: 30 },
  { time: "16:00", agentCount: 11, consensusLevel: 87, signalStrength: 77, coordinationEvents: 24 },
  { time: "18:00", agentCount: 11, consensusLevel: 92, signalStrength: 83, coordinationEvents: 32 },
  { time: "20:00", agentCount: 10, consensusLevel: 86, signalStrength: 72, coordinationEvents: 20 },
  { time: "22:00", agentCount: 9, consensusLevel: 84, signalStrength: 69, coordinationEvents: 16 },
];

// ---- Price Feeds ----
export const priceFeeds: PriceFeed[] = [
  { time: "Mon", price: 94200, volume: 28_400_000_000 },
  { time: "Tue", price: 95800, volume: 31_200_000_000 },
  { time: "Wed", price: 95100, volume: 26_800_000_000 },
  { time: "Thu", price: 97300, volume: 34_100_000_000 },
  { time: "Fri", price: 98900, volume: 38_500_000_000 },
  { time: "Sat", price: 98200, volume: 22_700_000_000 },
  { time: "Sun", price: 98432, volume: 24_300_000_000 },
];

// ---- Stigmergy Feed (Agent Communications) ----
export interface StigmergySignal {
  id: string;
  agentId: string;
  agentName: string;
  type: "pheromone" | "alert" | "consensus" | "rebalance";
  message: string;
  timestamp: string;
  strength: number;
}

export const stigmergyFeed: StigmergySignal[] = [
  { id: "sig-1", agentId: "ag-1", agentName: "Nexus Oracle", type: "pheromone", message: "BTC volatility increasing — signal broadcast to risk agents", timestamp: "30s ago", strength: 0.87 },
  { id: "sig-2", agentId: "ag-2", agentName: "Sentinel Risk", type: "alert", message: "Elevated risk score for crypto portfolio — recommending hedge", timestamp: "1m ago", strength: 0.92 },
  { id: "sig-3", agentId: "ag-3", agentName: "Arbitrex", type: "consensus", message: "Arbitrage opportunity confirmed — 3 agents agree on INIT-USDC spread", timestamp: "2m ago", strength: 0.78 },
  { id: "sig-4", agentId: "ag-5", agentName: "CryptoSage", type: "pheromone", message: "AVAX price deviation detected — cross-checking with MetaMind", timestamp: "3m ago", strength: 0.65 },
  { id: "sig-5", agentId: "ag-8", agentName: "MetaMind", type: "pheromone", message: "Multi-chain consensus: All price feeds within 0.01% tolerance", timestamp: "4m ago", strength: 0.95 },
  { id: "sig-6", agentId: "ag-6", agentName: "HedgeGuard", type: "rebalance", message: "Auto-rebalance triggered: Reduce BTC exposure by 5%, increase USDC allocation", timestamp: "5m ago", strength: 0.71 },
  { id: "sig-7", agentId: "ag-4", agentName: "Veritas", type: "consensus", message: "Market #pm-8 resolution verified — 5/5 oracles concur", timestamp: "8m ago", strength: 0.98 },
  { id: "sig-8", agentId: "ag-11", agentName: "DepthSeeker", type: "pheromone", message: "SOL-USDC depth improving — widening spread to 0.12%", timestamp: "10m ago", strength: 0.54 },
  { id: "sig-9", agentId: "ag-9", agentName: "Aegis", type: "alert", message: "Unusual whale activity on INIT-USDC pair — monitoring", timestamp: "15m ago", strength: 0.73 },
  { id: "sig-10", agentId: "ag-12", agentName: "TruthEngine", type: "consensus", message: "Fed rate market resolution data collected — 82% confidence", timestamp: "20m ago", strength: 0.82 },
  { id: "sig-11", agentId: "ag-3", agentName: "Arbitrex", type: "rebalance", message: "Liquidity pool rebalance: ETH/INIT pair optimized", timestamp: "25m ago", strength: 0.61 },
  { id: "sig-12", agentId: "ag-1", agentName: "Nexus Oracle", type: "pheromone", message: "ETH gas fees stabilizing — signal strength normalizing", timestamp: "30m ago", strength: 0.45 },
];

// ---- Stats for Landing ----
export const platformStats = {
  totalValueLocked: 158_600_000,
  activeMarkets: 8,
  agentCount: 12,
  predictionAccuracy: 92.4,
  totalParticipants: 125_000,
  totalVolume: 89_400_000,
};

// ---- Dashboard overview ----
export const dashboardOverview = {
  portfolioValue: 247_890,
  activePositions: 6,
  pendingRewards: 1_892.5,
  agentHealthScore: 94.2,
};
