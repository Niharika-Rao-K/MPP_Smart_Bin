import React, { useState, useRef } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

// Configuration for Bin Capacities and Signals
const INITIAL_BINS = [
  { id: 'plastic', name: 'Plastic / Wrappers', current: 36, max: 100, color: '#4CAF50', signal: 'W' },
  { id: 'metal', name: 'Metal / Cans', current: 20, max: 100, color: '#2196F3', signal: 'M' },
  { id: 'e-waste', name: 'E-Waste', current: 15, max: 100, color: '#FF9800', signal: 'E' },
  { id: 'reject', name: 'Reject Bin', current: 5, max: 100, color: '#F44336', signal: 'R' }
];

// Fallback material-to-signal mapping
const MATERIAL_SIGNAL_MAP = {
  Plastic: 'W',
  Metal: 'M',
  'E-Waste': 'E'
};

// Preset quick-test items matching KNOWN_ITEMS_DB
const PRESET_ITEMS = [
  { name: 'Coca-Cola Can', material: 'Metal', weight: 13.0 },
  { name: 'Plastic Bottle (500ml)', material: 'Plastic', weight: 18.5 },
  { name: 'PCB / E-Waste', material: 'E-Waste', weight: 50.0 }
];

export default function App() {
  const [binCapacities, setBinCapacities] = useState(INITIAL_BINS);
  const [logs, setLogs] = useState([]);
  
  // Form State
  const [depositWeight, setDepositWeight] = useState(13.5);
  const [depositMaterial, setDepositMaterial] = useState('Metal');
  const [walletAddress, setWalletAddress] = useState('');
  const [depositFile, setDepositFile] = useState(null);
  
  // Network/UI State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Ref to reset uncontrolled file input
  const fileInputRef = useRef(null);

  /**
   * Process the verification output from main.py
   */
  const processEvaluationResult = (data, fallbackWeight) => {
    const isReject = 
      data.fusion_result?.decision === "REJECT" || 
      data.fusion_result?.decision === "CONTAMINATED";
    
    let routeSignal = data.hardware_route_signal;
    if (!routeSignal) {
      routeSignal = isReject ? "R" : (MATERIAL_SIGNAL_MAP[depositMaterial] || "M");
    }

    const itemWeight = typeof data.stable_weight_g === 'number' 
      ? data.stable_weight_g 
      : parseFloat(fallbackWeight) || 0;

    const creditsEarned = data.calculated_credits || data.web3_reward?.tokens_minted || 0;

    // Increment bin item counts
    setBinCapacities(prevBins =>
      prevBins.map(bin => {
        if (bin.signal === routeSignal) {
          return { ...bin, current: Math.min(bin.max, bin.current + 1) };
        }
        return bin;
      })
    );

    // Append standard log entry
    const newLog = {
      id: Date.now(),
      timestamp: new Date().toLocaleTimeString(),
      material: data.predicted_label || depositMaterial,
      weight: itemWeight,
      route: routeSignal,
      credits: creditsEarned,
      isContaminated: isReject,
      decision: data.fusion_result?.decision || "VERIFIED_CLEAN",
      action: data.fusion_result?.action || "Processed",
      txHash: data.web3_reward?.tx_hash || null,
      explorerUrl: data.web3_reward?.explorer_url || null
    };

    setLogs(prevLogs => [newLog, ...prevLogs]);
  };

  /**
   * Submit deposit payload to FastAPI (/api/rag/evaluate)
   */
  const handleUserDeposit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('label', depositMaterial);
    formData.append('real_weight_g', depositWeight);
    formData.append('wallet_address', walletAddress);
    if (depositFile) {
      formData.append('image', depositFile);
    }

    try {
      const response = await fetch(`${API_BASE}/api/rag/evaluate`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let backendError = `Server error: ${response.status}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            backendError = typeof errorData.detail === 'string' 
              ? errorData.detail 
              : JSON.stringify(errorData.detail);
          }
        } catch {
          // Response body non-JSON
        }
        throw new Error(backendError);
      }

      const data = await response.json();
      processEvaluationResult(data, depositWeight);

      // Reset file input
      setDepositFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setErrorMessage(err.message || "Unable to reach FastAPI service.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Quick preset button click handler
  const applyPreset = (preset) => {
    setDepositMaterial(preset.material);
    setDepositWeight(preset.weight);
  };

  // Summary Metrics
  const totalDeposits = logs.length;
  const totalRejections = logs.filter(l => l.isContaminated || l.route === 'R').length;
  const totalWeightGrams = logs.reduce((acc, curr) => acc + curr.weight, 0);
  const totalCreditsEarned = logs.reduce((acc, curr) => acc + curr.credits, 0);

  return (
    <div style={{ padding: '24px', fontFamily: 'system-ui, -apple-system, sans-serif', maxWidth: '1000px', margin: '0 auto', color: '#1a1a1a' }}>
      
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '2px solid #eaeaea', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '28px', color: '#0f172a' }}>Smart Bin Control Center</h1>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '14px' }}>AI-Driven Waste Sorting & Web3 Incentive Network</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', backgroundColor: '#f1f5f9', padding: '6px 12px', borderRadius: '20px' }}>
          <span style={{ height: '8px', width: '8px', borderRadius: '50%', backgroundColor: '#22c55e' }}></span>
          Backend API: <strong>{API_BASE}</strong>
        </div>
      </header>

      {/* Analytics KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '28px' }}>
        <div style={kpiCardStyle}>
          <span style={kpiLabelStyle}>Total Deposits</span>
          <p style={kpiValueStyle}>{totalDeposits}</p>
        </div>
        <div style={kpiCardStyle}>
          <span style={kpiLabelStyle}>Recycled Mass</span>
          <p style={{ ...kpiValueStyle, color: '#0284c7' }}>
            {totalWeightGrams >= 1000 ? `${(totalWeightGrams / 1000).toFixed(2)} kg` : `${totalWeightGrams.toFixed(1)} g`}
          </p>
        </div>
        <div style={kpiCardStyle}>
          <span style={kpiLabelStyle}>Tokens/Credits Minted</span>
          <p style={{ ...kpiValueStyle, color: '#16a34a' }}>{totalCreditsEarned}</p>
        </div>
        <div style={kpiCardStyle}>
          <span style={kpiLabelStyle}>Contaminations / Rejects</span>
          <p style={{ ...kpiValueStyle, color: '#dc2626' }}>{totalRejections}</p>
        </div>
      </div>

      {/* Bin Capacities Grid */}
      <section style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>Bin Capacity Monitor</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '16px' }}>
          {binCapacities.map(bin => {
            const percentage = Math.min(100, Math.round((bin.current / bin.max) * 100));
            return (
              <div key={bin.id} style={{ padding: '16px', border: '1px solid #e2e8f0', borderRadius: '8px', backgroundColor: '#ffffff', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <strong style={{ fontSize: '15px' }}>{bin.name}</strong>
                  <span style={{ fontSize: '12px', padding: '2px 6px', borderRadius: '4px', background: '#f1f5f9', fontWeight: 'bold' }}>Signal: {bin.signal}</span>
                </div>
                <div style={{ background: '#e2e8f0', height: '10px', borderRadius: '5px', overflow: 'hidden', marginBottom: '8px' }}>
                  <div style={{ width: `${percentage}%`, background: bin.color, height: '100%', transition: 'width 0.4s ease' }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#64748b' }}>
                  <span>{bin.current} / {bin.max} units</span>
                  <span>{percentage}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Simulation Form */}
      <section style={{ marginBottom: '36px', padding: '24px', border: '1px solid #e2e8f0', borderRadius: '12px', backgroundColor: '#f8fafc' }}>
        <h2 style={{ fontSize: '20px', marginTop: 0, marginBottom: '12px' }}>Simulate Material Deposit</h2>
        
        {/* Quick Presets */}
        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '13px', color: '#64748b', fontWeight: 500 }}>Quick Presets:</span>
          {PRESET_ITEMS.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => applyPreset(item)}
              style={{ padding: '4px 10px', fontSize: '12px', border: '1px solid #cbd5e1', borderRadius: '16px', backgroundColor: '#fff', cursor: 'pointer' }}
            >
              + {item.name} ({item.weight}g)
            </button>
          ))}
        </div>

        {errorMessage && (
          <div style={{ color: '#dc2626', backgroundColor: '#fef2f2', padding: '12px', border: '1px solid #fecaca', borderRadius: '6px', marginBottom: '16px', fontSize: '14px' }}>
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleUserDeposit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={labelStyle}>Weight (grams):</label>
              <input 
                type="number" 
                step="0.1"
                value={depositWeight} 
                onChange={(e) => setDepositWeight(parseFloat(e.target.value) || 0)} 
                required 
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>Material Classification:</label>
              <select 
                value={depositMaterial} 
                onChange={(e) => setDepositMaterial(e.target.value)}
                style={inputStyle}
              >
                <option value="Metal">Metal (Signal: M)</option>
                <option value="Plastic">Plastic / Wrapper (Signal: W)</option>
                <option value="E-Waste">E-Waste (Signal: E)</option>
              </select>
            </div>
          </div>

          <div>
            <label style={labelStyle}>Sepolia Wallet Address (Web3 Tokens):</label>
            <input 
              type="text"
              placeholder="0x..."
              value={walletAddress} 
              onChange={(e) => setWalletAddress(e.target.value)} 
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>Verification Image (Optional):</label>
            <input 
              ref={fileInputRef}
              type="file" 
              accept="image/*" 
              onChange={(e) => setDepositFile(e.target.files[0] || null)}
              style={{ ...inputStyle, padding: '6px' }}
            />
          </div>

          <button 
            type="submit" 
            disabled={isSubmitting}
            style={{
              padding: '12px 24px',
              backgroundColor: isSubmitting ? '#94a3b8' : '#2563eb',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '15px',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              marginTop: '8px'
            }}
          >
            {isSubmitting ? 'Evaluating RAG & Minting Tokens...' : 'Submit Deposit Simulation'}
          </button>
        </form>
      </section>

      {/* Activity Logs Table */}
      <section>
        <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>Recent Audit Logs</h2>
        {logs.length === 0 ? (
          <p style={{ color: '#64748b', fontStyle: 'italic' }}>No processing records logged yet.</p>
        ) : (
          <div style={{ overflowX: 'auto', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                  <th style={thStyle}>Time</th>
                  <th style={thStyle}>Material</th>
                  <th style={thStyle}>Weight</th>
                  <th style={thStyle}>Route</th>
                  <th style={thStyle}>Credits</th>
                  <th style={thStyle}>Decision</th>
                  <th style={thStyle}>Web3 Explorer</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={tdStyle}>{log.timestamp}</td>
                    <td style={tdStyle}><strong>{log.material}</strong></td>
                    <td style={tdStyle}>{log.weight}g</td>
                    <td style={tdStyle}>
                      <span style={{ backgroundColor: '#f1f5f9', padding: '2px 8px', borderRadius: '4px', fontFamily: 'monospace' }}>
                        {log.route}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, color: '#16a34a', fontWeight: 'bold' }}>+{log.credits}</td>
                    <td style={tdStyle}>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: '600',
                        backgroundColor: log.isContaminated ? '#fef2f2' : '#f0fdf4',
                        color: log.isContaminated ? '#dc2626' : '#16a34a'
                      }}>
                        {log.decision}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      {log.explorerUrl ? (
                        <a href={log.explorerUrl} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', textDecoration: 'none', fontWeight: '500' }}>
                          View Tx ↗
                        </a>
                      ) : (
                        <span style={{ color: '#94a3b8', fontSize: '12px' }}>No Tx</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

// Reusable Styles
const kpiCardStyle = {
  padding: '16px',
  border: '1px solid #e2e8f0',
  borderRadius: '8px',
  backgroundColor: '#ffffff',
  boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
};

const kpiLabelStyle = {
  fontSize: '13px',
  color: '#64748b',
  fontWeight: '500'
};

const kpiValueStyle = {
  fontSize: '24px',
  fontWeight: 'bold',
  margin: '8px 0 0 0',
  color: '#0f172a'
};

const labelStyle = {
  display: 'block',
  marginBottom: '6px',
  fontSize: '14px',
  fontWeight: '500',
  color: '#334155'
};

const inputStyle = {
  width: '100%',
  padding: '10px',
  border: '1px solid #cbd5e1',
  borderRadius: '6px',
  fontSize: '14px',
  boxSizing: 'border-box'
};

const thStyle = {
  padding: '12px',
  fontWeight: '600'
};

const tdStyle = {
  padding: '12px'
};
