"use client";

import React, { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import { predictionMarkets, type PredictionMarket } from "@/lib/mock-data";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Plus,
  X,
  Clock,
  Users,
  TrendingUp,
  Filter,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

function formatVolume(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v}`;
}

type FilterTab = "all" | "active" | "resolved" | "my";

function MarketCard({ market, onClick }: { market: PredictionMarket; onClick: () => void }) {
  const statusColors: Record<string, string> = {
    active: "bg-green-400/10 text-green-400 border-green-400/30",
    resolved: "bg-slate-400/10 text-slate-400 border-slate-400/30",
    upcoming: "bg-amber-400/10 text-amber-400 border-amber-400/30",
  };

  return (
    <div
      onClick={onClick}
      className="glass-card glass-card-hover p-5 cursor-pointer transition-all group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0 mr-3">
          <h3 className="font-semibold text-white group-hover:text-cyan-400 transition-colors truncate">
            {market.title}
          </h3>
          <p className="text-sm text-slate-400 mt-1 line-clamp-2">{market.description}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full border whitespace-nowrap ${statusColors[market.status]}`}>
          {market.status}
        </span>
      </div>

      {/* Outcome probabilities */}
      <div className="space-y-2 mb-4">
        {market.outcomes.map((outcome) => (
          <div key={outcome.name} className="flex items-center gap-3">
            <span className="text-xs text-slate-400 w-16 text-right">{outcome.name}</span>
            <div className="flex-1 h-2.5 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${outcome.probability * 100}%`,
                  background:
                    outcome.name === "Yes" || outcome.name === "Cut" || outcome.name === "SOL Wins" || outcome.name === "BTC Wins"
                      ? "linear-gradient(90deg, #06B6D4, #22D3EE)"
                      : outcome.name === "Hold"
                      ? "linear-gradient(90deg, #F59E0B, #FBBF24)"
                      : outcome.name === "Hike"
                      ? "linear-gradient(90deg, #EF4444, #F87171)"
                      : "linear-gradient(90deg, #8B5CF6, #A78BFA)",
                }}
              />
            </div>
            <span className="text-xs font-medium text-white w-10">
              {Math.round(outcome.probability * 100)}%
            </span>
          </div>
        ))}
      </div>

      {/* Meta */}
      <div className="flex items-center gap-4 text-xs text-slate-400">
        <div className="flex items-center gap-1">
          <TrendingUp className="w-3.5 h-3.5" />
          {formatVolume(market.totalVolume)}
        </div>
        <div className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" />
          {market.timeRemaining}
        </div>
        <div className="flex items-center gap-1">
          <Users className="w-3.5 h-3.5" />
          {market.participants.toLocaleString()}
        </div>
      </div>

      {/* My position */}
      {market.myPosition && (
        <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Position: {market.myPosition.outcome} — ${market.myPosition.amount.toLocaleString()}
          </span>
          <span
            className={`text-xs font-semibold ${
              market.myPosition.pnl >= 0 ? "text-green-400" : "text-red-400"
            }`}
          >
            {market.myPosition.pnl >= 0 ? "+" : ""}
            ${market.myPosition.pnl.toLocaleString()} PnL
          </span>
        </div>
      )}
    </div>
  );
}

function CreateMarketModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [outcomes, setOutcomes] = useState(["Yes", "No"]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 modal-overlay flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-card p-6 w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-white">Create Prediction Market</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Question</label>
            <input
              type="text"
              placeholder="e.g. Will BTC reach $150K by EOY 2025?"
              className="w-full px-3 py-2.5 rounded-lg bg-slate-800 border border-border text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 text-sm"
            />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Description</label>
            <textarea
              placeholder="Describe the prediction market..."
              rows={3}
              className="w-full px-3 py-2.5 rounded-lg bg-slate-800 border border-border text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 text-sm resize-none"
            />
          </div>
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Outcomes</label>
            {outcomes.map((outcome, i) => (
              <div key={i} className="flex items-center gap-2 mb-2">
                <input
                  type="text"
                  value={outcome}
                  onChange={(e) => {
                    const next = [...outcomes];
                    next[i] = e.target.value;
                    setOutcomes(next);
                  }}
                  className="flex-1 px-3 py-2 rounded-lg bg-slate-800 border border-border text-white focus:outline-none focus:border-cyan-500/50 text-sm"
                />
                {outcomes.length > 2 && (
                  <button
                    onClick={() => setOutcomes(outcomes.filter((_, idx) => idx !== i))}
                    className="text-red-400 hover:text-red-300"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
            <button
              onClick={() => setOutcomes([...outcomes, ""])}
              className="text-xs text-cyan-400 hover:text-cyan-300"
            >
              + Add Outcome
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-slate-400 mb-1 block">Duration (days)</label>
              <input
                type="number"
                placeholder="30"
                className="w-full px-3 py-2.5 rounded-lg bg-slate-800 border border-border text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 text-sm"
              />
            </div>
            <div>
              <label className="text-sm text-slate-400 mb-1 block">Initial Liquidity (INIT)</label>
              <input
                type="number"
                placeholder="1000"
                className="w-full px-3 py-2.5 rounded-lg bg-slate-800 border border-border text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 text-sm"
              />
            </div>
          </div>
          <button className="w-full py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold hover:from-cyan-400 hover:to-purple-400 transition-all mt-2">
            Create Market
          </button>
        </div>
      </div>
    </div>
  );
}

function MarketDetailModal({
  market,
  open,
  onClose,
}: {
  market: PredictionMarket | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!open || !market) return null;

  return (
    <div className="fixed inset-0 z-50 modal-overlay flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-card p-6 w-full max-w-2xl max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-white">{market.title}</h2>
            <p className="text-sm text-slate-400 mt-1">{market.description}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white ml-4">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Price chart */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Price History (Yes Outcome)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={market.priceHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} domain={[0, 1]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  border: "1px solid #1e293b",
                  borderRadius: "8px",
                  color: "#f1f5f9",
                  fontSize: 12,
                }}
              />
              <Line type="monotone" dataKey="yes" stroke="#06B6D4" strokeWidth={2} dot={false} name="Yes" />
              <Line type="monotone" dataKey="no" stroke="#8B5CF6" strokeWidth={2} dot={false} name="No" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-slate-800/50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-white">{formatVolume(market.totalVolume)}</div>
            <div className="text-xs text-slate-400">Volume</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-white">{market.timeRemaining}</div>
            <div className="text-xs text-slate-400">Remaining</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-white">{market.participants.toLocaleString()}</div>
            <div className="text-xs text-slate-400">Participants</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-cyan-400">{market.category}</div>
            <div className="text-xs text-slate-400">Category</div>
          </div>
        </div>

        {/* Order book mock */}
        <div className="mb-4">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Order Book</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-cyan-400 font-medium mb-2">BUY — Yes</div>
              {[98, 96, 94, 92, 90].map((price) => (
                <div key={price} className="flex items-center justify-between text-xs py-1">
                  <span className="text-slate-400">{(price / 100).toFixed(2)}</span>
                  <div className="flex-1 mx-2 h-1.5 rounded bg-slate-800 overflow-hidden">
                    <div className="h-full bg-cyan-500/30 rounded" style={{ width: `${Math.random() * 60 + 20}%` }} />
                  </div>
                  <span className="text-slate-300">{Math.floor(Math.random() * 5000 + 1000)}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="text-xs text-purple-400 font-medium mb-2">SELL — No</div>
              {[2, 4, 6, 8, 10].map((price) => (
                <div key={price} className="flex items-center justify-between text-xs py-1">
                  <span className="text-slate-400">{(price / 100).toFixed(2)}</span>
                  <div className="flex-1 mx-2 h-1.5 rounded bg-slate-800 overflow-hidden">
                    <div className="h-full bg-purple-500/30 rounded" style={{ width: `${Math.random() * 60 + 20}%` }} />
                  </div>
                  <span className="text-slate-300">{Math.floor(Math.random() * 5000 + 1000)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Activity feed */}
        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-3">Recent Activity</h3>
          <div className="space-y-2">
            {[
              { action: "Bought YES", amount: "$5,000", time: "2m ago" },
              { action: "Bought NO", amount: "$3,200", time: "8m ago" },
              { action: "Bought YES", amount: "$12,000", time: "15m ago" },
              { action: "Sold YES", amount: "$2,100", time: "22m ago" },
              { action: "Bought NO", amount: "$8,500", time: "30m ago" },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between py-1.5 text-xs">
                <div className="flex items-center gap-2">
                  {item.action.startsWith("Bought YES") ? (
                    <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                  ) : item.action.startsWith("Bought NO") ? (
                    <AlertCircle className="w-3.5 h-3.5 text-purple-400" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                  )}
                  <span className="text-slate-300">{item.action}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-white">{item.amount}</span>
                  <span className="text-muted">{item.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PredictionMarketsPage() {
  const [filter, setFilter] = useState<FilterTab>("all");
  const [showCreate, setShowCreate] = useState(false);
  const [selectedMarket, setSelectedMarket] = useState<PredictionMarket | null>(null);

  const filtered =
    filter === "all"
      ? predictionMarkets
      : filter === "my"
      ? predictionMarkets.filter((m) => m.myPosition)
      : predictionMarkets.filter((m) => m.status === filter);

  const tabs: { key: FilterTab; label: string }[] = [
    { key: "all", label: "All Markets" },
    { key: "active", label: "Active" },
    { key: "resolved", label: "Resolved" },
    { key: "my", label: "My Markets" },
  ];

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h1 className="text-2xl font-bold text-white">Prediction Markets</h1>
              <p className="text-slate-400 text-sm mt-1">
                {predictionMarkets.filter((m) => m.status === "active").length} active markets •{" "}
                {predictionMarkets.reduce((a, m) => a + m.totalVolume, 0).toLocaleString()} total volume
              </p>
            </div>
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-semibold hover:from-cyan-400 hover:to-purple-400 transition-all shadow-lg shadow-cyan-500/20"
            >
              <Plus className="w-4 h-4" />
              Create Market
            </button>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2 mb-6">
            <Filter className="w-4 h-4 text-slate-400" />
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  filter === tab.key
                    ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                    : "text-slate-400 hover:text-white border border-transparent"
                }`}
              >
                {tab.label}
                {tab.key === "my" && (
                  <span className="ml-1.5 text-xs bg-slate-700 px-1.5 py-0.5 rounded">
                    {predictionMarkets.filter((m) => m.myPosition).length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Market Grid */}
          <div className="grid md:grid-cols-2 gap-4">
            {filtered.map((market) => (
              <MarketCard
                key={market.id}
                market={market}
                onClick={() => setSelectedMarket(market)}
              />
            ))}
          </div>

          {filtered.length === 0 && (
            <div className="text-center py-16 text-slate-400">
              <Filter className="w-8 h-8 mx-auto mb-3 opacity-50" />
              <p>No markets found for this filter</p>
            </div>
          )}
        </div>
      </div>

      <CreateMarketModal open={showCreate} onClose={() => setShowCreate(false)} />
      <MarketDetailModal
        market={selectedMarket}
        open={!!selectedMarket}
        onClose={() => setSelectedMarket(null)}
      />
    </div>
  );
}
