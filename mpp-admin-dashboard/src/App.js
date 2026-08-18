import React, { useState, useRef } from 'react';

// Configuration for Bin Capacities and Signals
const INITIAL_BINS = [
  { id: 'plastic', name: 'Plastic/Wrappers', current: 36, max: 100, color: '#4CAF50', signal: 'W' },
  { id: 'metal', name: 'Metal', current: 20, max: 100, color: '#2196F3', signal: 'M' },
  { id: 'e-waste', name: 'E-Waste', current: 15, max: 100, color: '#FF9800', signal: 'E' },
  { id: 'reject', name: 'Reject Bin', current: 5, max: 100, color: '#F44336', signal: 'R' }
];

export default function App() {
  const [binCapacities, setBinCapacities] = useState(INITIAL_BINS);
  const [logs, setLogs] = useState([]);
  
  // Deposit Form State (Normalized types)
  const [depositWeight, setDepositWeight] = useState(13.5);
  const [depositMaterial, setDepositMaterial] = useState('Plastic');
  const [depositFile, setDepositFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Ref to programmatically clear the uncontrolled file input DOM element
  const fileInputRef = useRef(null);

  /**
   * Evaluates backend response and routes item to correct bin.
   */
  const processEvaluationResult = (data, weightInput) => {
    const isReject = data.fusion_result?.decision === "REJECT" || data.status === "CONTAMINATION_DETECTED";
    
    // Explicit signal mapping fallback
    let routeSignal = data.hardware_route_signal;
    if (!routeSignal) {
      if (isReject) {
        routeSignal = "R";
      } else {
        // Map default non-reject materials explicitly
        const materialMap = {
          Plastic: "W",
          Metal: "M",
          "E-Waste": "E"
        };
        routeSignal = materialMap[depositMaterial] || "M";
      }
    }

    const itemWeight = typeof data.stable_weight_g === 'number' 
      ? data.stable_weight_g 
      : parseFloat(weightInput) || 0;

    // Update bin capacity based on route signal
    setBinCapacities(prevBins =>
      prevBins.map(bin => {
        if (bin.signal === routeSignal) {
          return { ...bin, current: Math.min(bin.max, bin.current + 1) };
        }
        return bin;
      })
    );

    // Append log with precise status metadata
    const newLog = {
      id: Date.now(),
      timestamp: new Date().toLocaleTimeString(),
      material: depositMaterial,
      weight: itemWeight,
      route: routeSignal,
      isContaminated: isReject,
      decision: data.fusion_result?.decision || "ACCEPTED",
      details: data.fusion_result?.reason || "Processed successfully"
    };

    setLogs(prevLogs => [newLog, ...prevLogs]);
  };

  /**
   * Handles user submission, API call, error handling, and form state reset.
   */
  const handleUserDeposit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('weight', depositWeight);
    formData.append('material', depositMaterial);
    if (depositFile) {
      formData.append('image', depositFile);
    }

    try {
      const response = await fetch('/api/evaluate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        // Parse backend JSON error payload (e.g., FastAPI 422/500 validation errors)
        let backendError = `Server returned status ${response.status}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            backendError = typeof errorData.detail === 'string' 
              ? errorData.detail 
              : JSON.stringify(errorData.detail);
          }
        } catch {
          // Response body was not JSON
        }
        throw new Error(backendError);
      }

      const data = await response.json();
      processEvaluationResult(data, depositWeight);

      // Reset form state and UI file input DOM node after successful deposit
      setDepositFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      setErrorMessage(err.message || "An unexpected error occurred during deposit.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // KPI Calculations
  const totalDetections = logs.length;
  const totalRejections = logs.filter(l => l.isContaminated || l.route === 'R').length;

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '900px', margin: '0 auto' }}>
      <h1>Smart Recycling Node Dashboard</h1>

      {/* KPI Summary Cards */}
      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
        <div style={{ padding: '15px', border: '1px solid #ccc', borderRadius: '8px', flex: 1 }}>
          <h3>Total Processed</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>{totalDetections}</p>
        </div>
        <div style={{ padding: '15px', border: '1px solid #ccc', borderRadius: '8px', flex: 1 }}>
          <h3>Rejections / Anomalies</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#F44336', margin: 0 }}>
            {totalRejections} Detected
          </p>
        </div>
      </div>

      {/* Bin Status Overview */}
      <section style={{ marginBottom: '30px' }}>
        <h2>Bin Capacities</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '15px' }}>
          {binCapacities.map(bin => (
            <div key={bin.id} style={{ padding: '12px', border: '1px solid #ddd', borderRadius: '6px' }}>
              <strong>{bin.name}</strong>
              <div style={{ background: '#eee', height: '10px', borderRadius: '5px', marginTop: '8px' }}>
                <div 
                  style={{ 
                    width: `${Math.min(100, (bin.current / bin.max) * 100)}%`, 
                    background: bin.color, 
                    height: '100%', 
                    borderRadius: '5px' 
                  }} 
                />
              </div>
              <small>{bin.current} / {bin.max} units (Signal: '{bin.signal}')</small>
            </div>
          ))}
        </div>
      </section>

      {/* Deposit Form */}
      <section style={{ marginBottom: '30px', padding: '20px', border: '1px solid #eee', borderRadius: '8px' }}>
        <h2>Simulate Material Deposit</h2>
        {errorMessage && (
          <div style={{ color: '#F44336', padding: '10px', border: '1px solid #F44336', borderRadius: '4px', marginBottom: '10px' }}>
            {errorMessage}
          </div>
        )}
        <form onSubmit={handleUserDeposit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '4px' }}>Weight (g):</label>
            <input 
              type="number" 
              step="0.1"
              value={depositWeight} 
              onChange={(e) => setDepositWeight(parseFloat(e.target.value) || 0)} 
              required 
              style={{ width: '100%', padding: '8px' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '4px' }}>Material:</label>
            <select 
              value={depositMaterial} 
              onChange={(e) => setDepositMaterial(e.target.value)}
              style={{ width: '100%', padding: '8px' }}
            >
              <option value="Plastic">Plastic/Wrapper (Signal: W)</option>
              <option value="Metal">Metal (Signal: M)</option>
              <option value="E-Waste">E-Waste (Signal: E)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '4px' }}>Sample Image:</label>
            <input 
              ref={fileInputRef}
              type="file" 
              accept="image/*" 
              onChange={(e) => setDepositFile(e.target.files[0] || null)}
              style={{ width: '100%' }}
            />
          </div>

          <button 
            type="submit" 
            disabled={isSubmitting}
            style={{ padding: '10px 20px', background: '#2196F3', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            {isSubmitting ? 'Evaluating...' : 'Submit Deposit'}
          </button>
        </form>
      </section>

      {/* Activity Logs */}
      <section>
        <h2>Recent Operations</h2>
        {logs.length === 0 ? (
          <p>No activity logged yet.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '2px solid #ccc' }}>
                <th style={{ padding: '8px' }}>Time</th>
                <th style={{ padding: '8px' }}>Material</th>
                <th style={{ padding: '8px' }}>Weight</th>
                <th style={{ padding: '8px' }}>Signal</th>
                <th style={{ padding: '8px' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '8px' }}>{log.timestamp}</td>
                  <td style={{ padding: '8px' }}>{log.material}</td>
                  <td style={{ padding: '8px' }}>{log.weight}g</td>
                  <td style={{ padding: '8px' }}><code>{log.route}</code></td>
                  <td style={{ padding: '8px', color: log.isContaminated ? '#F44336' : '#4CAF50' }}>
                    {log.isContaminated ? 'REJECTED' : 'ACCEPTED'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
