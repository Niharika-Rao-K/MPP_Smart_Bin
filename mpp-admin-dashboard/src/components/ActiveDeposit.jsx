import React, { useState } from 'react';

const ActiveDeposit = ({ backendUrl = "https://solid-succotash-97w5vgqj54vr277wv-8000.app.github.dev" }) => {
  const [file, setFile] = useState(null);
  const [weightInput, setWeightInput] = useState("13.5");
  const [status, setStatus] = useState("IDLE"); // IDLE | SCANNING | SUCCESS | REJECTED
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDepositSubmit = async (e) => {
    e.preventDefault();
    if (!file) return alert("Please select or capture an image snapshot first.");

    setStatus("SCANNING");
    setResult(null);

    const formData = new FormData();
    formData.append("image", file);
    formData.append("weight", weightInput);
    formData.append("wallet_address", "0x71C7656EC7ab88b098defB751B7401B5f6d8976F");

    try {
      const response = await fetch(`${backendUrl}/deposit`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      setResult(data);

      if (data.hardware_route_signal === "R") {
        setStatus("REJECTED");
      } else {
        setStatus("SUCCESS");
      }
    } catch (err) {
      console.error("Deposit submission error:", err);
      setStatus("IDLE");
      alert("Failed to reach backend server. Ensure FastAPI is running.");
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '20px auto', padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
      <h2>♻️ Smart Recycling Deposit Terminal</h2>
      
      {/* Simulation Input Controls */}
      <form onSubmit={handleDepositSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>1. Upload Item Photo (ESP32-CAM Simulation):</label>
          <input type="file" accept="image/*" onChange={handleFileChange} />
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>2. Scale Weight (Grams):</label>
          <input 
            type="number" 
            step="0.1" 
            value={weightInput} 
            onChange={(e) => setWeightInput(e.target.value)} 
            style={{ width: '100%', padding: '8px' }}
          />
        </div>

        <button 
          type="submit" 
          disabled={status === "SCANNING"}
          style={{ padding: '12px', background: '#2e7d32', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {status === "SCANNING" ? "Processing RAG & Sensor Fusion..." : "Submit Deposit"}
        </button>
      </form>

      {/* Real-time Processing Feedback */}
      {status === "SCANNING" && (
        <div style={{ marginTop: '20px', color: '#0288d1' }}>
          <p>⏳ Analyzing item with YOLOv8 & cross-checking ChromaDB reference weight...</p>
        </div>
      )}

      {/* Result Card */}
      {result && (
        <div style={{ marginTop: '20px', padding: '15px', borderRadius: '6px', background: status === "SUCCESS" ? "#e8f5e9" : "#ffebee" }}>
          <h3 style={{ color: status === "SUCCESS" ? "#2e7d32" : "#c62828" }}>
            {status === "SUCCESS" ? "✅ Item Verified & Sorted" : "❌ Deposit Rejected (Anomaly / Liquid Contamination)"}
          </h3>
          
          <ul style={{ listStyle: 'none', paddingLeft: 0 }}>
            <li><strong>Detected Item:</strong> {result.predicted_label}</li>
            <li><strong>Stable Weight:</strong> {result.stable_weight_g} g</li>
            <li><strong>Hardware Signal Code:</strong> <code style={{ fontSize: '1.2em' }}>{result.hardware_route_signal}</code></li>
            <li><strong>Decision Action:</strong> {result.fusion_result?.action}</li>
          </ul>

          {result.web3_reward && (
            <div style={{ marginTop: '10px', padding: '10px', background: '#fff', borderRadius: '4px', border: '1px solid #c8e6c9' }}>
              <strong>🪙 Web3 Reward Minted:</strong> {result.web3_reward.tokens_minted} $RECYCLE Tokens
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ActiveDeposit;
