"use client";

import React, { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import { agents, stigmergyFeed, type Agent, type StigmergySignal } from "@/lib/mock-data";
import {
  Bot,
  Activity,
  Clock,
  CheckCircle,
  Wrench,
  X,
  Target,
  Radio,
  AlertTriangle,
  ArrowRightLeft,
  BarChart3,
} from "lucide-react";

const typeColors: Record<string, string> = {
  "Price Oracle": "text-cyan-400 bg-cyan-400/10 border-cyan-400/30",
  "Risk Analyzer": "text-amber-400 bg-amber-400/10 border-amber-400/30",
  "Market Maker": "text-purple-400 bg-purple-400/10 border-purple-400/30",
  "Resolution": "text-green-400 bg-green-400/10 border-green-400/30",
};

const statusIcons: Record<string, React.ElementType> = {
  active: CheckCircle,
  idle: Clock,
  maintenance: Wrench,
};

const statusColors: Record<string, string> = {
  active: "text-green-400",
  idle: "text-slate-400",
  maintenance: "text-amber-400",
};

const signalTypeIcons: Record<string, React.ElementType> = {
  pheromone: Radio,
  alert: AlertTriangle,
  consensus: Target,
  rebalance: ArrowRightLeft,
};

const signalTypeColors: Record<string, string> = {
  pheromone: "text-cyan-400",
  alert: "text-amber-400",
  consensus: "text-green-400",
  rebalance: "text-purple-400",
};

// SVG swarm network graph
function SwarmNetworkGraph() {
  const graphNodes = agents.slice(0, 12).map((agent, i) => {
    const angle = (i / 12) * Math.PI * 2;
    const radius = 120 + (i % 3) * 40;
    return {
      id: agent.id,
      name: agent.name,
      x: 250 + Math.cos(angle) * radius,
      y: 200 + Math.sin(angle) * radius,
      type: agent.type,
      status: agent.status,
      accuracy: agent.accuracy,
    };
  });

  // Generate some edges
  const edges: { from: string; to: string }[] = [];
  for (let i = 0; i < graphNodes.length; i++) {
    const connections = 2 + Math.floor(Math.random() * 2);
    for (let j = 0; j < connections; j++) {
      const target = (i + j + 1) % graphNodes.length;
      const edge = { from: graphNodes[i].id, to: graphNodes[target].id };
      if (!edges.find((e) => (e.from === edge.from && e.to === edge.to) || (e.from === edge.to && e.to === edge.from))) {
        edges.push(edge);
      }
    }
  }

  const nodeColor = (type: string) => {
    switch (type) {
      case "Price Oracle": return "#06B6D4";
      case "Risk Analyzer": return "#F59E0B";
      case "Market Maker": return "#8B5CF6";
      case "Resolution": return "#10B981";
      default: return "#64748b";
    }
  };

  return (
    <svg viewBox="0 0 500 400" className="w-full h-auto">
      {/* Edges */}
      {edges.map((edge, i) => {
        const from = graphNodes.find((n) => n.id === edge.from);
        const to = graphNodes.find((n) => n.id === edge.to);
        if (!from || !to) return null;
        return (
          <line
            key={i}
            x1={from.x}
            y1={from.y}
            x2={to.x}
            y2={to.y}
            stroke="#1e293b"
            strokeWidth="1"
            opacity="0.6"
          >
            <animate
              attributeName="opacity"
              values="0.3;0.7;0.3"
              dur={`${2 + Math.random() * 3}s`}
              repeatCount="indefinite"
            />
          </line>
        );
      })}
      {/* Nodes */}
      {graphNodes.map((node) => (
        <g key={node.id}>
          {/* Glow */}
          <circle cx={node.x} cy={node.y} r="14" fill={nodeColor(node.type)} opacity="0.15">
            <animate
              attributeName="r"
              values="14;18;14"
              dur="3s"
              repeatCount="indefinite"
            />
          </circle>
          {/* Main circle */}
          <circle
            cx={node.x}
            cy={node.y}
            r="10"
            fill="#0f172a"
            stroke={nodeColor(node.type)}
            strokeWidth="2"
          />
          {/* Inner dot */}
          <circle cx={node.x} cy={node.y} r="4" fill={nodeColor(node.type)}>
            {node.status === "active" && (
              <animate
                attributeName="opacity"
                values="0.7;1;0.7"
                dur="2s"
                repeatCount="indefinite"
              />
            )}
          </circle>
          {/* Label */}
          <text
            x={node.x}
            y={node.y + 24}
            textAnchor="middle"
            fill="#94a3b8"
            fontSize="10"
            fontFamily="system-ui"
          >
            {node.name}
          </text>
        </g>
      ))}
    </svg>
  );
}

function AgentDetailModal({
  agent,
  open,
  onClose,
}: {
  agent: Agent | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!open || !agent) return null;

  return (
    <div className="fixed inset-0 z-50 modal-overlay flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-card p-6 w-full max-w-lg max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${typeColors[agent.type].split(" ")[1]}`}>
              <Bot className="w-5 h-5" style={{ color: typeColors[agent.type].split(" ")[0].replace("text-", "") }} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">{agent.name}</h2>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full border ${typeColors[agent.type]}`}>
                  {agent.type}
                </span>
                <span className={`text-xs flex items-center gap-1 ${statusColors[agent.status]}`}>
                  {(() => { const StatusIcon = statusIcons[agent.status]; return <StatusIcon className="w-3 h-3" />; })()}
                  {agent.status}
                </span>
              </div>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-slate-800/50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-cyan-400">{agent.accuracy}%</div>
            <div className="text-xs text-slate-400">Accuracy</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-green-400">{agent.uptime}%</div>
            <div className="text-xs text-slate-400">Uptime</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-white">{agent.decisions24h}</div>
            <div className="text-xs text-slate-400">Decisions/24h</div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-purple-400">{agent.consensusRate}%</div>
            <div className="text-xs text-slate-400">Consensus</div>
          </div>
        </div>

        {/* Performance metrics */}
        <div className="mb-6">
          <h3 className="text-sm font-medium text-slate-300 mb-3">Performance Metrics</h3>
          <div className="grid grid-cols-2 gap-2">
            {agent.performanceMetrics.map((m) => (
              <div key={m.metric} className="flex items-center justify-between p-2.5 bg-slate-800/30 rounded-lg text-xs">
                <span className="text-slate-400">{m.metric}</span>
                <span className="text-white font-medium">{m.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent decisions */}
        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-3">Recent Decisions</h3>
          <div className="space-y-2">
            {agent.recentDecisions.map((d, i) => (
              <div key={i} className="flex items-center justify-between p-2.5 bg-slate-800/30 rounded-lg text-xs">
                <div>
                  <div className="text-white">{d.action}</div>
                  <div className="text-muted">{d.time}</div>
                </div>
                <span className="text-cyan-400 font-medium">{d.outcome}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const filteredAgents =
    typeFilter === "all" ? agents : agents.filter((a) => a.type === typeFilter);

  const activeAgents = agents.filter((a) => a.status === "active").length;
  const avgAccuracy = (agents.reduce((a, b) => a + b.accuracy, 0) / agents.length).toFixed(1);
  const totalDecisions = agents.reduce((a, b) => a + b.decisions24h, 0);

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white">AI Agent Swarm</h1>
            <p className="text-slate-400 text-sm mt-1">
              {activeAgents} active agents • {avgAccuracy}% avg accuracy • {totalDecisions.toLocaleString()} decisions today
            </p>
          </div>

          {/* Swarm Visualization */}
          <div className="glass-card glow-purple p-6 mb-8">
            <h2 className="text-lg font-bold text-white mb-1">Swarm Network</h2>
            <p className="text-sm text-slate-400 mb-4">
              Real-time agent coordination graph — nodes are agents, edges are active communication channels
            </p>
            <div className="flex justify-center">
              <div className="w-full max-w-xl">
                <SwarmNetworkGraph />
              </div>
            </div>
            <div className="flex flex-wrap justify-center gap-4 mt-4">
              {Object.entries(typeColors).map(([type, classes]) => (
                <span key={type} className={`text-xs px-2.5 py-1 rounded-full border ${classes}`}>
                  {type}
                </span>
              ))}
            </div>
          </div>

          {/* Type Filter */}
          <div className="flex items-center gap-2 mb-6">
            <BarChart3 className="w-4 h-4 text-slate-400" />
            {["all", "Price Oracle", "Risk Analyzer", "Market Maker", "Resolution"].map((type) => (
              <button
                key={type}
                onClick={() => setTypeFilter(type)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  typeFilter === type
                    ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                    : "text-slate-400 hover:text-white border border-transparent"
                }`}
              >
                {type === "all" ? "All Types" : type}
                <span className="ml-1 text-muted">
                  ({type === "all" ? agents.length : agents.filter((a) => a.type === type).length})
                </span>
              </button>
            ))}
          </div>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Agent Table */}
            <div className="lg:col-span-2 glass-card p-6">
              <h2 className="text-lg font-bold text-white mb-4">Agent Directory</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-400 border-b border-border">
                      <th className="pb-3 font-medium">Agent</th>
                      <th className="pb-3 font-medium">Type</th>
                      <th className="pb-3 font-medium">Status</th>
                      <th className="pb-3 font-medium text-right">Accuracy</th>
                      <th className="pb-3 font-medium text-right">Uptime</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAgents.map((agent) => (
                      <tr
                        key={agent.id}
                        className="border-b border-border/50 hover:bg-slate-800/30 cursor-pointer transition-colors"
                        onClick={() => setSelectedAgent(agent)}
                      >
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${statusColors[agent.status]} ${
                              agent.status === "active" ? "status-pulse-active" : ""
                            }`} />
                            <span className="font-medium text-white">{agent.name}</span>
                          </div>
                        </td>
                        <td className="py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full border ${typeColors[agent.type]}`}>
                            {agent.type}
                          </span>
                        </td>
                        <td className="py-3">
                          <span className={`text-xs flex items-center gap-1 ${statusColors[agent.status]}`}>
                            {(() => { const StatusIcon = statusIcons[agent.status]; return <StatusIcon className="w-3 h-3" />; })()}
                            {agent.status}
                          </span>
                        </td>
                        <td className="py-3 text-right">
                          <span className={`font-medium ${agent.accuracy >= 93 ? "text-green-400" : agent.accuracy >= 88 ? "text-cyan-400" : "text-amber-400"}`}>
                            {agent.accuracy}%
                          </span>
                        </td>
                        <td className="py-3 text-right text-slate-300">{agent.uptime}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Stigmergy Feed */}
            <div className="glass-card p-6">
              <h2 className="text-lg font-bold text-white mb-4">
                <Radio className="w-4 h-4 inline mr-2 text-cyan-400" />
                Stigmergy Feed
              </h2>
              <p className="text-xs text-slate-400 mb-4">Recent agent communications (pheromone signals)</p>
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {stigmergyFeed.map((signal: StigmergySignal) => {
                  const Icon = signalTypeIcons[signal.type] || Radio;
                  return (
                    <div key={signal.id} className="p-3 bg-slate-800/30 rounded-lg hover:bg-slate-800/50 transition-colors">
                      <div className="flex items-center gap-2 mb-1.5">
                        <Icon className={`w-3.5 h-3.5 ${signalTypeColors[signal.type]}`} />
                        <span className="text-xs font-medium text-white">{signal.agentName}</span>
                        <span className="text-xs text-muted ml-auto">{signal.timestamp}</span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">{signal.message}</p>
                      <div className="mt-1.5 flex items-center gap-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded border ${signalTypeColors[signal.type]} bg-slate-800 border-slate-700`}>
                          {signal.type}
                        </span>
                        <div className="flex items-center gap-1">
                          <Activity className="w-3 h-3 text-slate-500" />
                          <div className="w-12 h-1.5 rounded bg-slate-800 overflow-hidden">
                            <div
                              className="h-full rounded bg-cyan-500"
                              style={{ width: `${signal.strength * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-muted">{(signal.strength * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      <AgentDetailModal
        agent={selectedAgent}
        open={!!selectedAgent}
        onClose={() => setSelectedAgent(null)}
      />
    </div>
  );
}
