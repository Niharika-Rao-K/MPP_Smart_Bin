import React, { useState } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, Cell 
} from 'recharts';
import { 
  ShieldAlert, HardDrive, RefreshCw, Layers, 
  Upload, Wallet, CheckCircle2, XCircle, Activity, Award, User, LayoutDashboard 
} from 'lucide-react';

export default function App() {
  // Navigation State: 'USER_TERMINAL' or 'OPERATOR_PORTAL'
  const [activeTab, setActiveTab] = useState('USER_TERMINAL');

  // Backend Configuration
  const [backendUrl, setBackendUrl] = useState('http://127.0.0.1:8000');

  // Live System Execution Logs
  const [logs, setLogs] = useState([
    { 
      id: 1, 
      label: "coca_cola_can", 
      matched: "coca_cola_can", 
      weight: 13.5, 
      status: "VERIFIED_CLEAN", 
      route: "M", 
      action: "Accept item. Route to METAL bin.", 
      tokens: 10, 
      timestamp: "10:14:22 AM" 
    },
    { 
      id: 2, 
      label: "snack_wrapper", 
      matched: "snack_wrapper", 
      weight: 5.2, 
      status: "VERIFIED_CLEAN", 
      route: "W", 
      action: "Accept item. Route to WRAPPER bin.", 
      tokens: 10, 
      timestamp: "10:18:05 AM" 
    },
    { 
      id: 3, 
      label: "water_bottle", 
      matched: "water_bottle", 
      weight: 145.0, 
      status: "CONTAMINATION_DETECTED", 
      route: "R", 
      action: "Reject item. Anomaly or liquid remaining inside.", 
      tokens: 0, 
      timestamp: "10:22:41 AM" 
    }
  ]);

  // Dynamic Bin Capacities (Updated on verified deposits)
  const [binCapacities, setBinCapacities] = useState([
    { name: 'Plastic/Wrappers (W)', current: 36, max: 100, color: '#4CAF50', signal: 'W' },
    { name: 'Metal Waste (M)', current: 63, max: 100, color: '#2196F3', signal: 'M' },
    { name: 'E-Waste (E)', current: 18, max: 100, color: '#9C27B0', signal: 'E' },
    { name: 'Reject Tray (R)', current: 9, max: 50, color: '#F44336', signal: 'R' },
  ]);

  // Total Web3 Rewards Minted Counter
  const [totalTokensMinted, setTotalTokensMinted] = useState(20);

  // --- Customer Deposit Terminal State ---
  const [depositFile, setDepositFile] = useState(null);
  const [depositWeight, setDepositWeight] = useState("13.5");
  const [walletAddress, setWalletAddress] = useState("0x71C7656EC7ab88b098defB751B7401B5f6d8976F");
  const [depositStatus, setDepositStatus] = useState("IDLE"); // IDLE | PROCESSING | SUCCESS | REJECTED
  const [latestResult, setLatestResult] = useState(null);

  // --- Sandbox Sandbox Engine State ---
  const [inputLabel, setInputLabel] = useState("coca_cola_can");
  const [inputWeight, setInputWeight] = useState(13.5);
  const [isTesting, setIsTesting] = useState(false);

  // Helper to update bin capacity visually when items are deposited
  const incrementBinCapacity = (routeSignal) => {
    setBinCapacities(prev => prev.map(bin => {
      if (bin.signal === routeSignal && bin.current < bin.max) {
        return { ...bin, current: bin.current + 1 };
      }
      return bin;
    }));
  };

  // 1. Live Deposit API Handler (Multipart / File + Scale payload)
  const handleUserDeposit = async (e) => {
    e.preventDefault();
    if (!depositFile) {
      alert("Please select or capture an image snapshot first!");
      return;
    }

    setDepositStatus("PROCESSING");
    setLatestResult(null);

    const formData = new FormData();
    formData.append("image", depositFile);
    formData.append("weight", depositWeight);
    formData.append("wallet_address", walletAddress);

    try {
      const response = await fetch(`${backendUrl}/deposit`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Server returned an error status.");

      const data = await response.json();
      setLatestResult(data);

      const route = data.hardware_route_signal;
      const isClean = route !== "R";

      setDepositStatus(isClean ? "SUCCESS" : "REJECTED");

      // Update Bin Capacity
      incrementBinCapacity(route);

      // Award tokens if clean deposit
      if (isClean && data.web3_reward?.tokens_minted) {
        setTotalTokensMinted(prev => prev + data.web3_reward.tokens_minted);
      }

      // Prepend to Live Logs
      const newLog = {
        id: Date.now(),
        label: data.predicted_label || "unknown_item",
        matched: data.fusion_result?.rag_result?.matched_label || data.predicted_label,
        weight: data.stable_weight_g || parseFloat(depositWeight),
        status: data.fusion_result?.decision || (isClean ? "VERIFIED_CLEAN" : "CONTAMINATION_DETECTED"),
        route: route,
        action: data.fusion_result?.action || "Evaluated by sensor fusion.",
        tokens: isClean ? (data.web3_reward?.tokens_minted || 10) : 0,
        timestamp: new Date().toLocaleTimeString()
      };
      setLogs(prev => [newLog, ...prev]);

    } catch (err) {
      console.error("Deposit submission failed:", err);
      setDepositStatus("IDLE");
      alert("Could not connect to FastAPI backend at " + backendUrl + ". Ensure server is running!");
    }
  };

  // 2. Local RAG Sandbox Engine Handler
  const handleSimulateScan = async (e) => {
    e.preventDefault();
    setIsTesting(true);

    try {
      // Create a dummy text file to test the multipart /deposit endpoint directly from the sandbox
      const dummyFile = new File([inputLabel], "sandbox_test.jpg", { type: "image/jpeg" });
      const formData = new FormData();
      formData.append("image", dummyFile);
      formData.append("weight", inputWeight);
      formData.append("wallet_address", walletAddress);

      const response = await fetch(`${backendUrl}/deposit`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        const route = data.hardware_route_signal;
        const isClean = route !== "R";

        incrementBinCapacity(route);
        if (isClean) setTotalTokensMinted(prev => prev + 10);

        const newLog = {
          id: Date.now(),
          label: inputLabel,
          matched: data.fusion_result?.rag_result?.matched_label || inputLabel,
          weight: parseFloat(inputWeight),
          status: data.fusion_result?.decision || (isClean ? "VERIFIED_CLEAN" : "CONTAMINATION_DETECTED"),
          route: route,
          action: data.fusion_result?.action || "Sandbox manual evaluation complete.",
          tokens: isClean ? 10 : 0,
          timestamp: new Date().toLocaleTimeString()
        };
        setLogs(prev => [newLog, ...prev]);
      } else {
        alert("Server responded with an error. Verify that database seeding is complete.");
      }
    } catch (err) {
      alert("Could not connect to FastAPI server at port 8000!");
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div style={{ padding: '24px', fontFamily: 'Segoe UI, Roboto, sans-serif', background: '#f4f6f9', minHeight: '100vh', color: '#333' }}>
      
      {/* Navigation & Header Panel */}
      <header style={{ background: '#fff', padding: '16px 24px', borderRadius: '12px', boxShadow: '0 2px 4px rgba(0,0,0,0.04)', marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '22px', color: '#1a202c', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Layers color="#4CAF50" /> Smart Automated Recycling Terminal
            </h1>
            <p style={{ margin: '4px 0 0 0', color: '#718096', fontSize: '13px' }}>
              FastAPI + ChromaDB RAG Engine + ESP32 Actuation + Sepolia Web3 Rewards
            </p>
          </div>

          {/* Mode Switcher Buttons */}
          <div style={{ display: 'flex', gap: '10px', background: '#edf2f7', padding: '4px', borderRadius: '8px' }}>
            <button 
              onClick={() => setActiveTab('USER_TERMINAL')}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: 'none',
                fontWeight: '600', cursor: 'pointer', transition: '0.2s',
                background: activeTab === 'USER_TERMINAL' ? '#4CAF50' : 'transparent',
                color: activeTab === 'USER_TERMINAL' ? '#fff' : '#4a5568'
              }}
            >
              <User size={16} /> Customer Deposit Screen
            </button>
            <button 
              onClick={() => setActiveTab('OPERATOR_PORTAL')}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: 'none',
                fontWeight: '600', cursor: 'pointer', transition: '0.2s',
                background: activeTab === 'OPERATOR_PORTAL' ? '#2196F3' : 'transparent',
                color: activeTab === 'OPERATOR_PORTAL' ? '#fff' : '#4a5568'
              }}
            >
              <LayoutDashboard size={16} /> Operator Analytics Portal
            </button>
          </div>
        </div>
      </header>

      {/* Analytics KPI Summary Banner */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: '#fff', padding: '16px 20px', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ background: '#e8f5e9', padding: '12px', borderRadius: '8px' }}><Activity color="#2e7d32" size={24} /></div>
          <div>
            <div style={{ fontSize: '12px', color: '#718096', fontWeight: '600' }}>TOTAL DEPOSITS</div>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#2d3748' }}>{logs.length} Items</div>
          </div>
        </div>

        <div style={{ background: '#fff', padding: '16px 20px', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ background: '#fff8e1', padding: '12px', borderRadius: '8px' }}><Award color="#ffa000" size={24} /></div>
          <div>
            <div style={{ fontSize: '12px', color: '#718096', fontWeight: '600' }}>WEB3 REWARDS MINTED</div>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#2d3748' }}>{totalTokensMinted} $RECYCLE</div>
          </div>
        </div>

        <div style={{ background: '#fff', padding: '16px 20px', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ background: '#ffebee', padding: '12px', borderRadius: '8px' }}><ShieldAlert color="#c62828" size={24} /></div>
          <div>
            <div style={{ fontSize: '12px', color: '#718096', fontWeight: '600' }}>REJECTED ANOMALIES</div>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#2d3748' }}>
              {logs.filter(l => l.route === 'R').length} Detected
            </div>
          </div>
        </div>
      </div>

      {/* TAB 1: CUSTOMER ACTIVE DEPOSIT TERMINAL */}
      {activeTab === 'USER_TERMINAL' && (
        <div style={{ maxWidth: '750px', margin: '0 auto', background: '#fff', padding: '28px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <h2 style={{ marginTop: 0, color: '#1a202c', display: 'flex', alignItems: 'center', gap: '8px' }}>
            ♻️ Deposit Item & Earn Crypto Rewards
          </h2>
          <p style={{ color: '#718096', fontSize: '14px', marginBottom: '20px' }}>
            Simulate an ESP32-CAM snapshot capture and HX711 load-cell reading to send to the FastAPI Sensor Fusion pipeline.
          </p>

          <form onSubmit={handleUserDeposit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            
            {/* Wallet Integration Card */}
            <div style={{ background: '#f8fafc', padding: '14px 18px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 'bold', color: '#4a5568', marginBottom: '6px' }}>
                <Wallet size={16} color="#2196F3" /> Recipient Web3 Wallet Address:
              </label>
              <input 
                type="text" 
                value={walletAddress} 
                onChange={(e) => setWalletAddress(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e0', fontFamily: 'monospace', fontSize: '13px', boxSizing: 'border-box' }}
                required 
              />
            </div>

            {/* Camera File Upload */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', fontWeight: 'bold', marginBottom: '6px' }}>
                <Upload size={16} color="#4CAF50" /> 1. Upload Item Snapshot (ESP32-CAM Simulation):
              </label>
              <input 
                type="file" 
                accept="image/*" 
                onChange={(e) => setDepositFile(e.target.files[0])}
                style={{ width: '100%', padding: '10px', background: '#f7fafc', border: '1px dashed #cbd5e0', borderRadius: '6px' }}
                required 
              />
            </div>

            {/* Load Cell Weight Input */}
            <div>
              <label style={{ display: 'block', fontSize: '14px', fontWeight: 'bold', marginBottom: '6px' }}>
                ⚖️ 2. Physical Scale Weight Reading (grams):
              </label>
              <input 
                type="number" 
                step="0.1" 
                value={depositWeight} 
                onChange={(e) => setDepositWeight(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e0', boxSizing: 'border-box' }}
                required 
              />
            </div>

            <button 
              type="submit" 
              disabled={depositStatus === "PROCESSING"}
              style={{ 
                padding: '14px', background: depositStatus === "PROCESSING" ? "#a5d6a7" : "#4CAF50", 
                color: '#fff', border: 'none', borderRadius: '8px', fontSize: '15px', fontWeight: 'bold', 
                cursor: 'pointer', transition: '0.2s', marginTop: '10px'
              }}
            >
              {depositStatus === "PROCESSING" ? "Evaluating YOLOv8 + ChromaDB RAG..." : "Submit Deposit Payload"}
            </button>
          </form>

          {/* Real-Time Result Banner */}
          {latestResult && (
            <div style={{ 
              marginTop: '24px', padding: '20px', borderRadius: '8px', 
              background: depositStatus === "SUCCESS" ? "#f0fdf4" : "#fef2f2",
              border: depositStatus === "SUCCESS" ? "1px solid #bbf7d0" : "1px solid #fecaca"
            }}>
              <h3 style={{ margin: '0 0 12px 0', display: 'flex', alignItems: 'center', gap: '8px', color: depositStatus === "SUCCESS" ? "#15803d" : "#991b1b" }}>
                {depositStatus === "SUCCESS" ? <CheckCircle2 color="#16a34a" /> : <XCircle color="#dc2626" />}
                {depositStatus === "SUCCESS" ? "Deposit Verified & Hardware Sorting Triggered" : "Deposit Rejected — Anomaly / Contamination"}
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '14px', marginBottom: '12px' }}>
                <div><strong>Detected Item:</strong> <code style={{ background: '#e2e8f0', padding: '2px 6px', borderRadius: '4px' }}>{latestResult.predicted_label}</code></div>
                <div><strong>Scale Weight:</strong> {latestResult.stable_weight_g} g</div>
                <div><strong>Actuator Route Code:</strong> <span style={{ fontWeight: 'bold', color: '#2563eb' }}>"{latestResult.hardware_route_signal}"</span></div>
                <div><strong>YOLO Confidence:</strong> {latestResult.confidence ? (latestResult.confidence * 100).toFixed(1) + "%" : "N/A"}</div>
              </div>

              <p style={{ margin: '8px 0', fontSize: '13px', color: '#4b5563' }}>
                <strong>Decision Details:</strong> {latestResult.fusion_result?.action}
              </p>

              {latestResult.web3_reward && depositStatus === "SUCCESS" && (
                <div style={{ marginTop: '12px', padding: '12px', background: '#fff', borderRadius: '6px', border: '1px solid #86efac', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 'bold', color: '#166534' }}>🪙 Web3 Reward Tokens Minted:</span>
                  <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#15803d' }}>+{latestResult.web3_reward.tokens_minted} $RECYCLE</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: OPERATOR ANALYTICS & SANDBOX PORTAL */}
      {activeTab === 'OPERATOR_PORTAL' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px', marginBottom: '24px' }}>
            
            {/* Module A: Live Sandbox Testing Console */}
            <div style={{ background: '#fff', padding: '24px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.02)' }}>
              <h3 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <RefreshCw size={20} color="#2196F3" /> RAG Database Sandbox Engine
              </h3>
              <p style={{ fontSize: '13px', color: '#666', marginTop: '-8px' }}>
                Manually test ChromaDB similarity queries and load-cell weight limits against your running backend.
              </p>
              
              <form onSubmit={handleSimulateScan} style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '6px' }}>Target Label / String</label>
                  <input 
                    type="text" 
                    value={inputLabel} 
                    onChange={e => setInputLabel(e.target.value)} 
                    style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e0', boxSizing: 'border-box' }} 
                    required 
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', marginBottom: '6px' }}>Physical Weight (grams)</label>
                  <input 
                    type="number" 
                    step="0.1" 
                    value={inputWeight} 
                    onChange={e => setInputWeight(e.target.value)} 
                    style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e0', boxSizing: 'border-box' }} 
                    required 
                  />
                </div>
                <button 
                  type="submit" 
                  disabled={isTesting} 
                  style={{ background: '#2196F3', color: '#fff', border: 'none', padding: '12px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer', marginTop: '8px', transition: '0.2s' }}
                >
                  {isTesting ? 'Querying local server...' : 'Submit Sandbox Event Payload'}
                </button>
              </form>
            </div>

            {/* Module B: Real-Time Bin Capacity Chart */}
            <div style={{ background: '#fff', padding: '24px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.02)' }}>
              <h3 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <HardDrive size={20} color="#4CAF50" /> Internal Bin Capacities
              </h3>
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={binCapacities} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} />
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

          {/* Module C: System Execution Logs */}
          <div style={{ background: '#fff', padding: '24px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.02)' }}>
            <h3 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={20} color="#F44336" /> Live System Execution Log
            </h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
                <thead>
                  <tr style={{ background: '#f7fafc', borderBottom: '2px solid #e2e8f0' }}>
                    <th style={{ padding: '12px' }}>Timestamp</th>
                    <th style={{ padding: '12px' }}>Input Label</th>
                    <th style={{ padding: '12px' }}>Matched Metadata</th>
                    <th style={{ padding: '12px' }}>Weight (g)</th>
                    <th style={{ padding: '12px' }}>Anomaly Decision</th>
                    <th style={{ padding: '12px' }}>Actuator Route</th>
                    <th style={{ padding: '12px' }}>Tokens Awarded</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} style={{ borderBottom: '1px solid #edf2f7' }}>
                      <td style={{ padding: '12px', color: '#718096', fontSize: '12px' }}>{log.timestamp}</td>
                      <td style={{ padding: '12px', fontWeight: '600' }}>"{log.label}"</td>
                      <td style={{ padding: '12px', color: '#4a5568' }}>{log.matched}</td>
                      <td style={{ padding: '12px', color: '#2b6cb0', fontWeight: '600' }}>{log.weight} g</td>
                      <td style={{ padding: '12px' }}>
                        <span style={{ 
                          padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', 
                          background: log.route !== 'R' ? '#e6fffa' : '#fff5f5', 
                          color: log.route !== 'R' ? '#00875a' : '#de350b' 
                        }}>
                          {log.status}
                        </span>
                      </td>
                      <td style={{ padding: '12px', fontWeight: 'bold' }}>
                        <span style={{ background: '#edf2f7', padding: '4px 10px', borderRadius: '6px' }}>
                          {log.route}
                        </span>
                      </td>
                      <td style={{ padding: '12px', fontWeight: 'bold', color: log.tokens > 0 ? '#2e7d32' : '#a0aec0' }}>
                        +{log.tokens} $RECYCLE
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

    </div>
  );
}
