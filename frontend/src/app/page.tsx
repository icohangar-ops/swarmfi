"use client";

import React from "react";
import Link from "next/link";
import { useInitiaWallet } from "@/lib/wallet";
import SwarmVisualization from "@/components/SwarmVisualization";
import {
  platformStats,
} from "@/lib/mock-data";
import {
  TrendingUp,
  BarChart3,
  Landmark,
  Brain,
  ArrowRight,
  Zap,
  Shield,
  Bot,
  Activity,
} from "lucide-react";

function formatNumber(n: number): string {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

export default function LandingPage() {
  const { isConnected, connect } = useInitiaWallet();

  return (
    <div className="relative overflow-hidden">
      {/* Hero */}
      <section className="relative min-h-[90vh] flex items-center justify-center">
        <SwarmVisualization className="absolute inset-0" particleCount={50} />

        <div className="relative z-10 max-w-5xl mx-auto px-4 text-center">
          <div className="animate-fade-in-up opacity-0">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 text-sm mb-8">
              <Zap className="w-3.5 h-3.5" />
              INITIATE Hackathon — Initia Blockchain
            </div>
          </div>

          <h1 className="animate-fade-in-up opacity-0 animate-delay-100 text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-tight mb-6">
            <span className="bg-gradient-to-r from-cyan-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
              AI Swarm Intelligence
            </span>
            <br />
            <span className="text-slate-100">Oracle & Predictions</span>
          </h1>

          <p className="animate-fade-in-up opacity-0 animate-delay-200 text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10">
            Decentralized AI agents coordinate through stigmergy to power
            prediction markets, real-time oracles, and auto-rebalancing vaults — all on Initia.
          </p>

          <div className="animate-fade-in-up opacity-0 animate-delay-300 flex flex-col sm:flex-row items-center justify-center gap-4">
            {!isConnected ? (
              <button
                onClick={connect}
                className="px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold text-lg hover:from-cyan-400 hover:to-purple-400 transition-all shadow-xl shadow-cyan-500/20 flex items-center gap-2"
              >
                <Zap className="w-5 h-5" />
                Connect Wallet
              </button>
            ) : (
              <Link
                href="/dashboard"
                className="px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold text-lg hover:from-cyan-400 hover:to-purple-400 transition-all shadow-xl shadow-cyan-500/20 flex items-center gap-2"
              >
                Go to Dashboard
                <ArrowRight className="w-5 h-5" />
              </Link>
            )}
            <Link
              href="/prediction-markets"
              className="px-8 py-3.5 rounded-xl border border-slate-600 text-slate-300 font-semibold text-lg hover:border-cyan-500/50 hover:text-white transition-all"
            >
              Explore Markets
            </Link>
          </div>
        </div>
      </section>

      {/* Live Stats */}
      <section className="relative py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Total Value Locked", value: formatNumber(platformStats.totalValueLocked), icon: Landmark, color: "cyan" },
              { label: "Active Markets", value: platformStats.activeMarkets.toString(), icon: BarChart3, color: "purple" },
              { label: "AI Agents", value: platformStats.agentCount.toString(), icon: Bot, color: "green" },
              { label: "Prediction Accuracy", value: `${platformStats.predictionAccuracy}%`, icon: TrendingUp, color: "amber" },
            ].map((stat) => (
              <div
                key={stat.label}
                className="glass-card glass-card-hover p-5 text-center transition-all duration-300"
              >
                <stat.icon
                  className={`w-6 h-6 mx-auto mb-3 ${
                    stat.color === "cyan"
                      ? "text-cyan-400"
                      : stat.color === "purple"
                      ? "text-purple-400"
                      : stat.color === "green"
                      ? "text-green-400"
                      : "text-amber-400"
                  }`}
                />
                <div className="text-2xl sm:text-3xl font-bold text-white mb-1">
                  {stat.value}
                </div>
                <div className="text-sm text-slate-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Value Props */}
      <section className="relative py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Powered by{" "}
              <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
                Swarm Intelligence
              </span>
            </h2>
            <p className="text-slate-400 max-w-xl mx-auto">
              Multiple AI agents collaborate through stigmergy — a natural coordination mechanism
              inspired by ant colonies and bee swarms.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Brain,
                title: "AI-Powered Oracles",
                description:
                  "Swarm of AI agents aggregates data from 23+ sources in real-time, achieving 94%+ accuracy with sub-20ms latency.",
                gradient: "from-cyan-500 to-blue-500",
                glow: "glow-cyan",
              },
              {
                icon: BarChart3,
                title: "Prediction Markets",
                description:
                  "Create and participate in prediction markets resolved by decentralized AI consensus — no single point of failure.",
                gradient: "from-purple-500 to-pink-500",
                glow: "glow-purple",
              },
              {
                icon: Shield,
                title: "Auto-Rebalancing Vaults",
                description:
                  "Vault strategies managed by agent swarms that continuously monitor risk and optimize yields across DeFi protocols.",
                gradient: "from-green-500 to-emerald-500",
                glow: "glow-cyan",
              },
            ].map((item) => (
              <div
                key={item.title}
                className={`glass-card glass-card-hover p-6 transition-all duration-300 ${item.glow}`}
              >
                <div
                  className={`w-12 h-12 rounded-xl bg-gradient-to-br ${item.gradient} flex items-center justify-center mb-5`}
                >
                  <item.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-3">{item.title}</h3>
                <p className="text-slate-400 leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="relative py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-16">
            How{" "}
            <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              SwarmFi
            </span>{" "}
            Works
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                step: "01",
                title: "Agent Network",
                description: "12+ specialized AI agents form a decentralized intelligence network",
              },
              {
                step: "02",
                title: "Stigmergy Signals",
                description: "Agents communicate through pheromone-like signals on-chain",
              },
              {
                step: "03",
                title: "Consensus",
                description: "Swarm reaches consensus on oracle prices, market outcomes, and risk levels",
              },
              {
                step: "04",
                title: "Execution",
                description: "Decisions execute autonomously — vault rebalancing, market resolution, and trading",
              },
            ].map((item) => (
              <div key={item.step} className="relative glass-card p-5">
                <div className="text-4xl font-black text-cyan-500/20 mb-2">{item.step}</div>
                <h4 className="text-lg font-bold text-white mb-2">{item.title}</h4>
                <p className="text-sm text-slate-400">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative py-20 px-4">
        <div className="max-w-3xl mx-auto text-center glass-card glow-cyan p-10 sm:p-16">
          <Activity className="w-10 h-10 text-cyan-400 mx-auto mb-6" />
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Ready to Join the Swarm?
          </h2>
          <p className="text-slate-400 mb-8 max-w-md mx-auto">
            Connect your wallet and start participating in AI-powered prediction markets
            and auto-rebalancing vaults.
          </p>
          {!isConnected ? (
            <button
              onClick={connect}
              className="px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold text-lg hover:from-cyan-400 hover:to-purple-400 transition-all shadow-xl shadow-cyan-500/20 inline-flex items-center gap-2"
            >
              Get Started <ArrowRight className="w-5 h-5" />
            </button>
          ) : (
            <Link
              href="/dashboard"
              className="px-8 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-500 text-white font-semibold text-lg hover:from-cyan-400 hover:to-purple-400 transition-all shadow-xl shadow-cyan-500/20 inline-flex items-center gap-2"
            >
              Go to Dashboard <ArrowRight className="w-5 h-5" />
            </Link>
          )}
        </div>
      </section>
    </div>
  );
}
