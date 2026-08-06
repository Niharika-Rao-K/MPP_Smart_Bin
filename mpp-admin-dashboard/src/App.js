import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { ShieldAlert, Trash2, HardDrive, RefreshCw, Layers } from 'lucide-react';

export default function App() {
  // Local state to track incoming logs, simulated hardware capacities, and UI forms
  const [logs, setLogs] = useState([
    { id: 1, label: "crushed chip packet", matched: "Lay's Potato Chip Packet", score: 94, status: "Valid", route: "W" },
    { id: 2, label: "old phone battery", matched: "Dead Smartphone Lithium Battery", score: 88, status: "Valid", route: "E" }
  ]);

  const [inputLabel, setInputLabel] = useState("broken computer mouse");
  const [inputWeight, setInputWeight] = useState(82.5);
  const [isTesting, setIsTesting] = useState(false);

  // Hardcoded storage volumes to simulate physical bin capacity status
  const binCapacities = [
    { name: 'Plastic Wrappers (W)', current: 35, max: 100, color: '#4CAF50' },
    { name: 'Metal Waste (M)', current: 62, max: 100, color: '#2196F3' },
    { name: 'E-Waste (E)', current: 18, max: 100, color: '#9C27B0' },
    { name: 'Reject Tray (R)', current: 8, max: 50, color: '#F44336' },
  ];

  // Function to test your local RAG API in real-time straight from the dashboard interface
  const handleSimulateScan = async (e) => {
    e.preventDefault();
    setIsTesting(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/rag/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: inputLabel,
          real_weight_g: parseFloat(inputWeight)
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        const newLog = {
          id: Date.now(),
          label: data.semantic_match.input_queried,
          matched: data.semantic_match.closest_matched_profile,
          score: data.semantic_match.similarity_score_pct,
          status: data.final_decision.status,
          route: data.final_decision.hardware_route_signal
        };
        setLogs(prev => [newLog, ...prev]);
      } else {
        alert("Server responded with an error. Ensure database profiles are seeded.");
      }
    } catch (err) {
      alert("Could not connect to FastAPI server. Make sure your server terminal is running at port 8000!");
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div style={{ padding: '24px', fontFamily: 'Segoe UI, sans-serif', background: '#f4f6f9', minHeight: '100vh', color: '#333' }}>
      
      {/* Header Panel */}
      <header style={{ display: 'flex', justifyContent: 'between', alignItems: 'center', background: '#fff', padding: '16px 24px', borderRadius: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.04)', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', color: '#1a202c', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Layers color="#4CAF50" /> Smart Recycling Machine — Operator Portal
          </h1>
          <p style={{ margin: '4px 0 0 0', color: '#718096', fontSize: '14px' }}>Niharika's Dashboard Component (Independent Environment)</p>
        </div>
      </header>

      {/* Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px', marginBottom: '24px' }}>
        
        {/* Module A: Live Sandbox Testing Console */}
        <div style={{ background: '#fff', padding: '24px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.02)' }}>
          <h3 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}><RefreshCw size={20} color="#2196F3" /> Local RAG Sandbox Engine</h3>
          <p style={{ fontSize: '13px', color: '#666', marginTop: '-8px' }}>Simulate a camera string detection and a load cell scale reading directly to your running FastAPI server backend.</p>
          <form onSubmit={handleSimulateScan} style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '6px' }}>Camera String (Label)</label>
              <input type="text" value={inputLabel} onChange={e => setInputLabel(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e0', boxSizing: 'border-box' }} required />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '6px' }}>Physical Load-Cell Weight (grams)</label>
              <input type="number" step="0.1" value={inputWeight} onChange={e => setInputWeight(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e0', boxSizing: 'border-box' }} required />
            </div>
            <button type="submit" disabled={isTesting} style={{ background: '#2196F3', color: '#fff', border: 'none', padding: '12px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer', marginTop: '8px', transition: '0.2s' }}>
              {isTesting ? 'Querying local server...' : 'Submit Hardware Event payload'}
            </button>
          </form>
        </div>

        {/* Module B: Real-Time Capacity Infrastructure Levels */}
        <div style={{ background: '#fff', padding: '24px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.02)' }}>
          <h3 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}><HardDrive size={20} color="#4CAF50" /> Machine Compartment Status</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={binCapacities} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="current" radius={[4, 4, 0, 0]}>
                {binCapacities.map((entry, idx) => (
                  <Cell key={`cell-${idx}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

      </div>

      {/* Module C: Semantic Diagnostics & Fallback Records Logs */}
      <div style={{ background: '#fff', padding: '24px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.02)' }}>
        <h3 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}><ShieldAlert size={20} color="#F44336" /> Live System Execution Log</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
            <thead>
              <tr style={{ background: '#f7fafc', borderBottom: '2px solid #e2e8f0' }}>
                <th style={{ padding: '12px' }}>Camera Input String</th>
                <th style={{ padding: '12px' }}>ChromaDB Nearest Profile</th>
                <th style={{ padding: '12px' }}>Confidence</th>
                <th style={{ padding: '12px' }}>Anomaly Check</th>
                <th style={{ padding: '12px' }}>Actuator Target Code</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} style={{ borderBottom: '1px solid #edf2f7', transition: '0.1s' }}>
                  <td style={{ padding: '12px', fontWeight: '500' }}>"{log.label}"</td>
                  <td style={{ padding: '12px', color: '#4a5568' }}>{log.matched}</td>
                  <td style={{ padding: '12px', color: '#2b6cb0', fontWeight: '600' }}>{log.score}%</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', background: log.status === 'Valid' ? '#e6fffa' : '#fff5f5', color: log.status === 'Valid' ? '#00875a' : '#de350b' }}>
                      {log.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px', fontWeight: 'bold', color: '#2d3748' }}>
                    <span style={{ background: '#edf2f7', padding: '4px 10px', borderRadius: '6px' }}>
                      {log.route}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}