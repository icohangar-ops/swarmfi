"use client";

import React, { useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/layout/Sidebar";
import {
  dashboardOverview,
  predictionMarkets,
  transactions,
  swarmEvents,
} from "@/lib/mock-data";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Wallet,
  BarChart3,
  Gift,
  HeartPulse,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
  Landmark,
  Bot,
  ExternalLink,
} from "lucide-react";

const typeIcons: Record<string, React.ElementType> = {
  trade: BarChart3,
  deposit: ArrowUpRight,
  withdraw: ArrowDownRight,
  reward: Gift,
  market_create: Plus,
};

const typeColors: Record<string, string> = {
  trade: "text-cyan-400 bg-cyan-400/10",
  deposit: "text-green-400 bg-green-400/10",
  withdraw: "text-red-400 bg-red-400/10",
  reward: "text-amber-400 bg-amber-400/10",
  market_create: "text-purple-400 bg-purple-400/10",
};

export default function DashboardPage() {
  const [chartMetric, setChartMetric] = useState<"agentCount" | "consensusLevel" | "signalStrength">("agentCount");

  const topMarkets = predictionMarkets
    .filter((m) => m.status === "active")
    .slice(0, 5);

  const recentTx = transactions.slice(0, 8);

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white">Dashboard</h1>
            <p className="text-slate-400 text-sm mt-1">
              Overview of your swarm portfolio and activity
            </p>
          </div>

          {/* Overview Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[
              {
                label: "Portfolio Value",
                value: `$${dashboardOverview.portfolioValue.toLocaleString()}`,
                icon: Wallet,
                change: "+5.2%",
                positive: true,
              },
              {
                label: "Active Positions",
                value: dashboardOverview.activePositions.toString(),
                icon: BarChart3,
                change: "2 markets",
                positive: true,
              },
              {
                label: "Pending Rewards",
                value: `${dashboardOverview.pendingRewards.toLocaleString()} INIT`,
                icon: Gift,
                change: "~$4,637",
                positive: true,
              },
              {
                label: "Agent Health Score",
                value: `${dashboardOverview.agentHealthScore}%`,
                icon: HeartPulse,
                change: "All systems",
                positive: true,
              },
            ].map((card) => (
              <div key={card.label} className="glass-card glass-card-hover p-5 transition-all">
                <div className="flex items-center justify-between mb-3">
                  <card.icon className="w-5 h-5 text-cyan-400" />
                  <span className={`text-xs font-medium ${card.positive ? "text-green-400" : "text-red-400"}`}>
                    {card.change}
                  </span>
                </div>
                <div className="text-2xl font-bold text-white">{card.value}</div>
                <div className="text-sm text-slate-400 mt-1">{card.label}</div>
              </div>
            ))}
          </div>

          {/* Swarm Activity Chart */}
          <div className="glass-card p-6 mb-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-bold text-white">Swarm Activity</h2>
                <p className="text-sm text-slate-400">Agent coordination over the past 24 hours</p>
              </div>
              <div className="flex gap-1">
                {(["agentCount", "consensusLevel", "signalStrength"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setChartMetric(m)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      chartMetric === m
                        ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {m === "agentCount"
                      ? "Agents"
                      : m === "consensusLevel"
                      ? "Consensus"
                      : "Signal"}
                  </button>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={swarmEvents}>
                <defs>
                  <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#06B6D4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #1e293b",
                    borderRadius: "8px",
                    color: "#f1f5f9",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey={chartMetric}
                  stroke="#06B6D4"
                  strokeWidth={2}
                  fill="url(#chartGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid lg:grid-cols-5 gap-6">
            {/* Top Markets Table */}
            <div className="lg:col-span-3 glass-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-white">Top Markets</h2>
                <Link
                  href="/prediction-markets"
                  className="text-sm text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                >
                  View All <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-400 border-b border-border">
                      <th className="pb-3 font-medium">Market</th>
                      <th className="pb-3 font-medium">Volume</th>
                      <th className="pb-3 font-medium">Outcome</th>
                      <th className="pb-3 font-medium">Position</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topMarkets.map((market) => (
                      <tr
                        key={market.id}
                        className="border-b border-border/50 hover:bg-slate-800/30 transition-colors"
                      >
                        <td className="py-3 pr-4">
                          <div className="font-medium text-white truncate max-w-[200px]">
                            {market.title}
                          </div>
                          <div className="text-xs text-muted">{market.participants} participants</div>
                        </td>
                        <td className="py-3 pr-4 text-slate-300">
                          ${(market.totalVolume / 1_000_000).toFixed(1)}M
                        </td>
                        <td className="py-3 pr-4">
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-2 rounded-full bg-slate-700 overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400 rounded-full"
                                style={{ width: `${market.outcomes[0].probability * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-cyan-400">
                              {Math.round(market.outcomes[0].probability * 100)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-3">
                          {market.myPosition ? (
                            <span
                              className={`text-xs font-medium px-2 py-1 rounded ${
                                market.myPosition.pnl >= 0
                                  ? "text-green-400 bg-green-400/10"
                                  : "text-red-400 bg-red-400/10"
                              }`}
                            >
                              {market.myPosition.pnl >= 0 ? "+" : ""}
                              ${market.myPosition.pnl.toLocaleString()}
                            </span>
                          ) : (
                            <span className="text-xs text-muted">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recent Transactions */}
            <div className="lg:col-span-2 glass-card p-6">
              <h2 className="text-lg font-bold text-white mb-4">Recent Activity</h2>
              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
                {recentTx.map((tx) => {
                  const Icon = typeIcons[tx.type] || BarChart3;
                  const colorClass = typeColors[tx.type] || "text-slate-400 bg-slate-400/10";
                  return (
                    <div
                      key={tx.id}
                      className="flex items-start gap-3 p-2.5 rounded-lg hover:bg-slate-800/30 transition-colors"
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${colorClass}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-white truncate">{tx.description}</div>
                        <div className="text-xs text-muted">{tx.timestamp}</div>
                      </div>
                      <div className="text-right">
                        <div
                          className={`text-sm font-medium ${
                            tx.type === "withdraw" ? "text-red-400" : "text-green-400"
                          }`}
                        >
                          {tx.type === "withdraw" ? "-" : "+"}${tx.amount.toLocaleString()}
                        </div>
                        <div className="text-xs text-muted">{tx.token}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
            {[
              {
                label: "Create Market",
                description: "Launch a new prediction market",
                icon: Plus,
                href: "/prediction-markets",
              },
              {
                label: "Deposit to Vault",
                description: "Invest in auto-rebalancing strategies",
                icon: Landmark,
                href: "/vaults",
              },
              {
                label: "View Agents",
                description: "Monitor AI swarm activity",
                icon: Bot,
                href: "/agents",
              },
            ].map((action) => (
              <Link
                key={action.label}
                href={action.href}
                className="glass-card glass-card-hover p-5 flex items-center gap-4 transition-all group"
              >
                <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center group-hover:bg-cyan-500/20 transition-colors">
                  <action.icon className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                  <div className="font-medium text-white text-sm">{action.label}</div>
                  <div className="text-xs text-slate-400">{action.description}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
