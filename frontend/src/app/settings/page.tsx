"use client";

import React, { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import { useInitiaWallet, useBalance } from "@/lib/wallet";
import {
  User,
  Wallet,
  Bell,
  Sliders,
  ExternalLink,
  AtSign,
} from "lucide-react";

export default function SettingsPage() {
  const { isConnected, address, initiaAddress, username, connect, disconnect } = useInitiaWallet();
  const balance = useBalance();
  const [riskTolerance, setRiskTolerance] = useState(5);
  const [notifications, setNotifications] = useState({
    marketResolution: true,
    vaultRebalance: true,
    agentAlerts: true,
    priceAlerts: false,
    weeklyReport: true,
  });

  const riskLabel = (v: number) => {
    if (v <= 3) return "Conservative";
    if (v <= 6) return "Balanced";
    if (v <= 8) return "Aggressive";
    return "Maximum Risk";
  };

  const riskColor = (v: number) => {
    if (v <= 3) return "text-green-400";
    if (v <= 6) return "text-cyan-400";
    if (v <= 8) return "text-amber-400";
    return "text-red-400";
  };

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 lg:ml-64 min-h-screen">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white">Settings</h1>
            <p className="text-slate-400 text-sm mt-1">
              Manage your account, wallet, and preferences
            </p>
          </div>

          {/* .init Username */}
          <div className="glass-card p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                <AtSign className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">.init Username</h2>
                <p className="text-sm text-slate-400">Your Initia identity</p>
              </div>
            </div>
            {isConnected && username ? (
              <div className="bg-slate-800/50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-lg font-semibold text-cyan-400">{username}.init</div>
                    <div className="text-xs text-slate-400 mt-1">Registered on Initia Name Service</div>
                  </div>
                  <ExternalLink className="w-4 h-4 text-slate-400" />
                </div>
              </div>
            ) : (
              <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                <p className="text-sm text-slate-400 mb-3">Connect your wallet to view or register a .init username</p>
                <button
                  onClick={connect}
                  className="px-4 py-2 rounded-lg bg-cyan-500/10 text-cyan-400 text-sm font-medium border border-cyan-500/30 hover:bg-cyan-500/20 transition-all"
                >
                  Connect Wallet
                </button>
              </div>
            )}
          </div>

          {/* Wallet Info */}
          <div className="glass-card p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center">
                <Wallet className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Wallet</h2>
                <p className="text-sm text-slate-400">Connected wallet information</p>
              </div>
            </div>

            {isConnected ? (
              <div className="space-y-3">
                <div className="bg-slate-800/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-slate-400">Status</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-green-400/10 text-green-400 border border-green-400/30">
                      Connected
                    </span>
                  </div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-slate-400">Balance</span>
                    <span className="text-sm text-white font-medium">
                      {balance.balance} {balance.symbol} <span className="text-muted">(~${balance.usdValue})</span>
                    </span>
                  </div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-slate-400">Initia Address</span>
                    <span className="text-xs text-slate-300 font-mono">{initiaAddress}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Hex Address</span>
                    <span className="text-xs text-slate-300 font-mono truncate max-w-[180px]">{address}</span>
                  </div>
                </div>
                <button
                  onClick={disconnect}
                  className="w-full py-2.5 rounded-lg border border-red-500/30 text-red-400 text-sm font-medium hover:bg-red-500/10 transition-all"
                >
                  Disconnect Wallet
                </button>
              </div>
            ) : (
              <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                <p className="text-sm text-slate-400 mb-3">No wallet connected</p>
                <button
                  onClick={connect}
                  className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-semibold hover:from-cyan-400 hover:to-purple-400 transition-all"
                >
                  Connect Wallet
                </button>
              </div>
            )}
          </div>

          {/* Notification Preferences */}
          <div className="glass-card p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                <Bell className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Notifications</h2>
                <p className="text-sm text-slate-400">Manage alert preferences</p>
              </div>
            </div>

            <div className="space-y-3">
              {(Object.entries(notifications) as [keyof typeof notifications, boolean][]).map(([key, value]) => {
                const labels: Record<string, string> = {
                  marketResolution: "Market Resolution Alerts",
                  vaultRebalance: "Vault Rebalance Notifications",
                  agentAlerts: "Agent Status Alerts",
                  priceAlerts: "Price Alert Thresholds",
                  weeklyReport: "Weekly Performance Report",
                };
                const icons: Record<string, string> = {
                  marketResolution: "Get notified when markets resolve",
                  vaultRebalance: "Updates on vault rebalancing events",
                  agentAlerts: "Agent status changes and maintenance",
                  priceAlerts: "Custom price threshold notifications",
                  weeklyReport: "Summary of portfolio performance",
                };
                return (
                  <div key={key} className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                    <div>
                      <div className="text-sm text-white">{labels[key]}</div>
                      <div className="text-xs text-slate-400">{icons[key]}</div>
                    </div>
                    <button
                      onClick={() => setNotifications({ ...notifications, [key]: !value })}
                      className={`w-11 h-6 rounded-full transition-all relative ${
                        value ? "bg-cyan-500" : "bg-slate-600"
                      }`}
                    >
                      <div
                        className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${
                          value ? "left-5.5" : "left-0.5"
                        }`}
                      />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Risk Tolerance */}
          <div className="glass-card p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center">
                <Sliders className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Risk Tolerance</h2>
                <p className="text-sm text-slate-400">Configure vault strategy risk level</p>
              </div>
            </div>

            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-slate-400">Risk Level</span>
                <span className={`text-sm font-bold ${riskColor(riskTolerance)}`}>
                  {riskLabel(riskTolerance)} ({riskTolerance}/10)
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={riskTolerance}
                onChange={(e) => setRiskTolerance(Number(e.target.value))}
                className="w-full h-2 rounded-full appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, #10B981 0%, #06B6D4 30%, #F59E0B 60%, #EF4444 100%)`,
                }}
              />
              <div className="flex justify-between text-xs text-muted mt-2">
                <span>Conservative</span>
                <span>Balanced</span>
                <span>Aggressive</span>
              </div>
              <p className="text-xs text-slate-400 mt-3">
                {riskTolerance <= 3
                  ? "Your vaults will prioritize capital preservation with stable yields."
                  : riskTolerance <= 6
                  ? "Your vaults will balance risk and reward across mixed asset strategies."
                  : riskTolerance <= 8
                  ? "Your vaults will seek higher returns with increased exposure to volatile assets."
                  : "Your vaults will pursue maximum yield with the highest risk exposure."}
              </p>
            </div>
          </div>

          {/* Profile */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center">
                <User className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Profile</h2>
                <p className="text-sm text-slate-400">Your SwarmFi account</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-white">6</div>
                <div className="text-xs text-slate-400">Active Positions</div>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-white">3</div>
                <div className="text-xs text-slate-400">Vault Deposits</div>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-white">10</div>
                <div className="text-xs text-slate-400">Markets Traded</div>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-green-400">+18.4%</div>
                <div className="text-xs text-slate-400">Total Returns</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
