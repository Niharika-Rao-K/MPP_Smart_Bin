import React, { useState, useRef } from 'react';
import ReactDOM from 'react-dom';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

export default function App() {
  const [logs, setLogs] = useState([]);
  const [depositWeight, setDepositWeight] = useState(13.5);
  const [depositMaterial, setDepositMaterial] = useState('Metal');
  const [walletAddress, setWalletAddress] = useState('');
  const [depositFile, setDepositFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const fileInputRef = useRef(null);

  const totalDetections = logs.length;
  const totalRejections = logs.filter(l => l.isContaminated || l.route === 'R').length;

  const handleUserDeposit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('label', depositMaterial);
    formData.append('real_weight_g', depositWeight);
    formData.append('wallet_address', walletAddress);
    if (depositFile) formData.append('image', depositFile);

    try {
      const response = await fetch(`${API_BASE}/api/rag/evaluate`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error(`Server returned status ${response.status}`);

      const data = await response.json();
      const newLog = {
        id: Date.now(),
        timestamp: new Date().toLocaleTimeString(),
        material: data.predicted_label || depositMaterial,
        weight: data.stable_weight_g || depositWeight,
        route: data.hardware_route_signal || "M",
        isContaminated: data.fusion_result?.decision === "REJECT",
        explorerUrl: data.web3_reward?.explorer_url || null
      };

      setLogs(prev => [newLog, ...prev]);
      setDepositFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Helper to mount React elements into HTML IDs
  const renderPortal = (id, children) => {
    const el = document.getElementById(id);
    return el ? ReactDOM.createPortal(children, el) : null;
  };

  return (
    <>
      {/* Dynamic KPI Outputs */}
      {renderPortal('portal-total-deposits', 
        <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>{totalDetections}</p>
      )}

      {renderPortal('portal-rejections', 
        <p className="reject-text" style={{ margin: 0 }}>{totalRejections} Detected</p>
      )}

      {/* Dynamic Form */}
      {renderPortal('portal-deposit-form',
        <form onSubmit={handleUserDeposit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {errorMessage && <div style={{ color: '#F44336' }}>{errorMessage}</div>}
          <label>
            Weight (g):
            <input type="number" step="0.1" value={depositWeight} onChange={e => setDepositWeight(parseFloat(e.target.value) || 0)} required />
          </label>
          <label>
            Material:
            <select value={depositMaterial} onChange={e => setDepositMaterial(e.target.value)}>
              <option value="Metal">Metal</option>
              <option value="Plastic">Plastic</option>
              <option value="E-Waste">E-Waste</option>
            </select>
          </label>
          <label>
            Wallet Address:
            <input type="text" placeholder="0x..." value={walletAddress} onChange={e => setWalletAddress(e.target.value)} />
          </label>
          <label>
            Sample Image:
            <input ref={fileInputRef} type="file" accept="image/*" onChange={e => setDepositFile(e.target.files[0] || null)} />
          </label>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Evaluating...' : 'Submit Deposit'}
          </button>
        </form>
      )}

      {/* Dynamic Logs Table */}
      {renderPortal('portal-activity-table',
        logs.length === 0 ? <p>No activity logged yet.</p> : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '2px solid #ccc' }}>
                <th>Time</th><th>Material</th><th>Weight</th><th>Route</th><th>Reward</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td>{log.timestamp}</td>
                  <td>{log.material}</td>
                  <td>{log.weight}g</td>
                  <td><code>{log.route}</code></td>
                  <td>{log.explorerUrl ? <a href={log.explorerUrl} target="_blank" rel="noreferrer">View Tx ↗</a> : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )
      )}
    </>
  );
}
