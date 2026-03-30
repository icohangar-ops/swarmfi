"use client";

import React, { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import { vaults, type Vault } from "@/lib/mock-data";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  Shield,
  TrendingUp,
  Zap,
  Bot,
  X,
  ArrowRightLeft,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

function formatTVL(v: number): string {
  if (v >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(2)}B`;
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  return `$${v.toLocaleString()}`;
}

function riskLabel(score: number): { label: string; className: string } {
  if (score <= 3) return { label: "Low", className: "risk-low" };
  if (score <= 6) return { label: "Medium", className: "risk-medium" };
  return { label: "High", className: "risk-high" };
}

const strategyIcons: Record<string, React.ElementType> = {
  Conservative: Shield,
  Balanced: TrendingUp,
  Aggressive: Zap,
};

const strategyGradients: Record<string, string> = {
  Conservative: "from-green-500 to-emerald-500",
  Balanced: "from-cyan-500 to-blue-500",
  Aggressive: "from-purple-500 to-pink-500",
};

function VaultCard({
  vault,
  onSelect,
}: {
  vault: Vault;
  onSelect: () => void;
}) {
  const Icon = strategyIcons[vault.strategy] || Shield;
  const risk = riskLabel(vault.riskScore);

  return (
    <div
      onClick={onSelect}
      className="glass-card glass-card-hover p-6 cursor-pointer transition-all group"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl bg-gradient-to-br ${strategyGradients[vault.strategy]} flex items-center justify-center`}
          >
            <Icon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-cyan-400 transition-colors">
              {vault.name}
            </h3>
            <span className="text-xs text-slate-400">{vault.strategy} Strategy</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-slate-400 mb-0.5">Risk</div>
          <span className={`text-sm font-bold ${risk.className}`}>{risk.label} ({vault.riskScore}/10)</span>
        </div>
      </div>

      <p className="text-sm text-slate-400 mb-4 line-clamp-2">{vault.description}</p>

      {/* Asset allocation mini bars */}
      <div className="flex gap-1 mb-4 h-2 rounded-full overflow-hidden">
        {vault.assetAllocation.map((asset) => (
          <div
            key={asset.name}
            className="h-full transition-all"
            style={{ width: `${asset.value}%`, backgroundColor: asset.color }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        {vault.assetAllocation.map((asset) => (
          <span key={asset.name} className="text-xs text-slate-400 flex items-center gap-1">
            <span
              className="w-2 h-2 rounded-full inline-block"
              style={{ backgroundColor: asset.color }}
            />
            {asset.name} {asset.value}%
          </span>
        ))}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="text-center p-2 bg-slate-800/50 rounded-lg">
          <div className="text-sm font-bold text-white">{formatTVL(vault.tvl)}</div>
          <div className="text-xs text-slate-400">TVL</div>
        </div>
        <div className="text-center p-2 bg-slate-800/50 rounded-lg">
          <div className="text-sm font-bold text-green-400">+{vault.returns24h}%</div>
          <div className="text-xs text-slate-400">24h</div>
        </div>
        <div className="text-center p-2 bg-slate-800/50 rounded-lg">
          <div className="text-sm font-bold text-cyan-400 flex items-center justify-center gap-1">
            <Bot className="w-3 h-3" />
            {vault.agentCount}
          </div>
          <div className="text-xs text-slate-400">Agents</div>
        </div>
      </div>
    </div>
  );
}

function DepositWithdrawModal({
  vault,
  open,
  onClose,
  mode,
}: {
  vault: Vault | null;
  open: boolean;
  onClose: () => void;
  mode: "deposit" | "withdraw";
}) {
  const [amount, setAmount] = useState("");

  if (!open || !vault) return null;

  return (
    <div className="fixed inset-0 z-50 modal-overlay flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-card p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-white">
            {mode === "deposit" ? "Deposit" : "Withdraw"} to {vault.name}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-slate-400 mb-1 block">Amount (USDC)</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              className="w-full px-3 py-3 rounded-lg bg-slate-800 border border-border text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 text-lg"
            />
            <div className="flex gap-2 mt-2">
              {["1000", "5000", "10000", "50000"].map((preset) => (
                <button
                  key={preset}
                  onClick={() => setAmount(preset)}
                  className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                >
                  ${Number(preset).toLocaleString()}
                </button>
              ))}
            </div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Vault TVL</span>
              <span className="text-white">{formatTVL(vault.tvl)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">24h Returns</span>
              <span className="text-green-400">+{vault.returns24h}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Risk Score</span>
              <span className={riskLabel(vault.riskScore).className}>
                {vault.riskScore}/10
              </span>
            </div>
          </div>
          <button className="w-full py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold hover:from-cyan-400 hover:to-purple-400 transition-all">
            {mode === "deposit" ? "Deposit" : "Withdraw"} {amount ? `$${Number(amount).toLocaleString()}` : ""}
          </button>
        </div>
      </div>
    </div>
  );
}

function VaultDetailModal({
  vault,
  open,
  onClose,
}: {
  vault: Vault | null;
  open: boolean;
  onClose: () => void;
}) {
  const [modalMode, setModalMode] = useState<"deposit" | "withdraw">("deposit");
  const [showDepositModal, setShowDepositModal] = useState(false);

  if (!open || !vault) return null;

  return (
    <>
      <div className="fixed inset-0 z-50 modal-overlay flex items-center justify-center p-4" onClick={onClose}>
        <div className="glass-card p-6 w-full max-w-3xl max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-white">{vault.name}</h2>
              <p className="text-sm text-slate-400 mt-1">{vault.description}</p>
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-white ml-4">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-white">{formatTVL(vault.tvl)}</div>
              <div className="text-xs text-slate-400">TVL</div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-green-400">+{vault.returns24h}%</div>
              <div className="text-xs text-slate-400">24h</div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-green-400">+{vault.returns7d}%</div>
              <div className="text-xs text-slate-400">7d</div>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-green-400">+{vault.returns30d}%</div>
              <div className="text-xs text-slate-400">30d</div>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6 mb-6">
            {/* Pie chart */}
            <div>
              <h3 className="text-sm font-medium text-slate-300 mb-3">Asset Allocation</h3>
              <div className="flex items-center justify-center">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={vault.assetAllocation}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      dataKey="value"
                      stroke="none"
                    >
                      {vault.assetAllocation.map((entry, index) => (
                        <Cell key={index} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        border: "1px solid #1e293b",
                        borderRadius: "8px",
                        color: "#f1f5f9",
                        fontSize: 12,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap justify-center gap-3 mt-2">
                {vault.assetAllocation.map((asset) => (
                  <span key={asset.name} className="text-xs text-slate-400 flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: asset.color }} />
                    {asset.name} ({asset.value}%)
                  </span>
                ))}
              </div>
            </div>

            {/* Performance chart */}
            <div>
              <h3 className="text-sm font-medium text-slate-300 mb-3">Performance History</h3>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={vault.performanceHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} domain={["auto", "auto"]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border: "1px solid #1e293b",
                      borderRadius: "8px",
                      color: "#f1f5f9",
                      fontSize: 12,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#06B6D4"
                    strokeWidth={2}
                    dot={{ fill: "#06B6D4", r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Rebalance history */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-slate-300 mb-3">Rebalance History</h3>
            <div className="space-y-2">
              {vault.rebalanceHistory.map((rb, i) => (
                <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-slate-800/30 text-xs">
                  <ArrowRightLeft className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                  <span className="text-slate-400 flex-shrink-0">{rb.date}</span>
                  <span className="text-white">
                    {rb.from} → {rb.to}
                  </span>
                  <span className="text-cyan-400 ml-auto font-medium">
                    ${rb.amount.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={() => {
                setModalMode("deposit");
                setShowDepositModal(true);
              }}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold hover:from-cyan-400 hover:to-purple-400 transition-all"
            >
              <ArrowDownRight className="w-4 h-4" />
              Deposit
            </button>
            <button
              onClick={() => {
                setModalMode("withdraw");
                setShowDepositModal(true);
              }}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-lg border border-border text-slate-300 font-semibold hover:border-cyan-500/50 hover:text-white transition-all"
            >
              <ArrowUpRight className="w-4 h-4" />
              Withdraw
            </button>
          </div>
        </div>
      </div>

      <DepositWithdrawModal
        vault={vault}
        open={showDepositModal}
        onClose={() => setShowDepositModal(false)}
        mode={modalMode}
      />
    </>
  );
}

export default function VaultsPage() {
  const [selectedVault, setSelectedVault] = useState<Vault | null>(null);

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white">Vaults</h1>
            <p className="text-slate-400 text-sm mt-1">
              Auto-rebalancing vaults managed by AI swarm intelligence
            </p>
          </div>

          {/* Total TVL */}
          <div className="glass-card glow-cyan p-6 mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="text-sm text-slate-400 mb-1">Total Value Locked Across All Vaults</div>
                <div className="text-3xl font-bold text-white">
                  {formatTVL(vaults.reduce((a, v) => a + v.tvl, 0))}
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm text-green-400">
                <TrendingUp className="w-4 h-4" />
                <span>Avg 24h: +{((vaults.reduce((a, v) => a + v.returns24h, 0) / vaults.length)).toFixed(2)}%</span>
              </div>
            </div>
          </div>

          {/* Vault Cards */}
          <div className="grid lg:grid-cols-3 gap-6">
            {vaults.map((vault) => (
              <VaultCard
                key={vault.id}
                vault={vault}
                onSelect={() => setSelectedVault(vault)}
              />
            ))}
          </div>
        </div>
      </div>

      <VaultDetailModal
        vault={selectedVault}
        open={!!selectedVault}
        onClose={() => setSelectedVault(null)}
      />
    </div>
  );
}
