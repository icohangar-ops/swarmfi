"use client";

import React from "react";

interface SwarmVizProps {
  className?: string;
  particleCount?: number;
}

export default function SwarmVisualization({ className = "", particleCount = 40 }: SwarmVizProps) {
  const nodes = Array.from({ length: particleCount }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: Math.random() * 6 + 2,
    delay: Math.random() * 5,
    duration: Math.random() * 8 + 6,
    opacity: Math.random() * 0.5 + 0.2,
    type: i % 5, // for color cycling
  }));

  const connections = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    from: Math.floor(Math.random() * particleCount),
    to: Math.floor(Math.random() * particleCount),
    opacity: Math.random() * 0.15 + 0.05,
  }));

  const animations = ["swarm-move-1", "swarm-move-2", "swarm-move-3", "swarm-move-4"];
  const colors = [
    "#06B6D4", // cyan
    "#8B5CF6", // purple
    "#06B6D4", // cyan
    "#10B981", // green
    "#8B5CF6", // purple
  ];

  return (
    <div className={`relative overflow-hidden ${className}`} aria-hidden="true">
      {/* Gradient orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-cyan-500/10 blur-3xl animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full bg-purple-500/10 blur-3xl animate-pulse" style={{ animationDelay: "2s" }} />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full bg-cyan-500/5 blur-3xl animate-pulse" style={{ animationDelay: "4s" }} />

      {/* SVG connections */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
        {connections.map((conn) => {
          const fromNode = nodes[conn.from % nodes.length];
          const toNode = nodes[conn.to % nodes.length];
          return (
            <line
              key={conn.id}
              x1={`${fromNode.x}%`}
              y1={`${fromNode.y}%`}
              x2={`${toNode.x}%`}
              y2={`${toNode.y}%`}
              stroke="url(#line-gradient)"
              strokeWidth="1"
              opacity={conn.opacity}
            >
              <animate
                attributeName="opacity"
                values={`${conn.opacity};${conn.opacity * 2};${conn.opacity}`}
                dur="3s"
                repeatCount="indefinite"
              />
            </line>
          );
        })}
        <defs>
          <linearGradient id="line-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#06B6D4" />
            <stop offset="100%" stopColor="#8B5CF6" />
          </linearGradient>
        </defs>
      </svg>

      {/* Particle nodes */}
      {nodes.map((node) => {
        const anim = animations[node.type % animations.length];
        return (
          <div
            key={node.id}
            className="absolute rounded-full"
            style={{
              left: `${node.x}%`,
              top: `${node.y}%`,
              width: `${node.size}px`,
              height: `${node.size}px`,
              backgroundColor: colors[node.type],
              opacity: node.opacity,
              boxShadow: `0 0 ${node.size * 3}px ${colors[node.type]}40`,
              animation: `${anim} ${node.duration}s ease-in-out infinite`,
              animationDelay: `${node.delay}s`,
            }}
          >
            {/* inner glow */}
            <div
              className="w-full h-full rounded-full"
              style={{
                background: `radial-gradient(circle, ${colors[node.type]}, transparent)`,
                animation: "pulse-glow 2s ease-in-out infinite",
                animationDelay: `${node.delay + 1}s`,
              }}
            />
          </div>
        );
      })}
    </div>
  );
}
