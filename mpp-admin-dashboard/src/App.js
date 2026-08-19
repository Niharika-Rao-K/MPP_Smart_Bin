import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';

const API_BASE =
  process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

export default function App() {
  const [logs, setLogs] = useState([]);

  const [depositWeight, setDepositWeight] = useState(1.85);
  const [depositMaterial, setDepositMaterial] = useState('Plastic');
  const [walletAddress, setWalletAddress] = useState('');
  const [depositFile, setDepositFile] = useState(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const [analysis, setAnalysis] = useState(null);

  const fileInputRef = useRef(null);

  const totalDetections = logs.length;

  const totalRejections = logs.filter(
    (log) => log.isContaminated || log.route === 'R'
  ).length;

  /*
   * ---------------------------------------------------------
   * DEPOSIT / RAG EVALUATION
   * ---------------------------------------------------------
   */

  const handleUserDeposit = async (e) => {
    e.preventDefault();

    setIsSubmitting(true);
    setErrorMessage(null);

    const formData = new FormData();

    formData.append('label', depositMaterial);
    formData.append('real_weight_g', String(depositWeight));
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
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();

      setAnalysis({
        material: data.predicted_label || depositMaterial,
        weight: data.stable_weight_g || depositWeight,
        route: data.hardware_route_signal || 'M',
        contaminated: data.fusion_result?.decision === 'REJECT',
        confidence: data.fusion_result?.confidence || null,
        explorerUrl: data.web3_reward?.explorer_url || null,
      });

      const newLog = {
        id: Date.now(),
        timestamp: new Date().toLocaleTimeString(),
        material: data.predicted_label || depositMaterial,
        weight: data.stable_weight_g || depositWeight,
        route: data.hardware_route_signal || 'M',
        isContaminated: data.fusion_result?.decision === 'REJECT',
        explorerUrl: data.web3_reward?.explorer_url || null,
      };

      setLogs((previousLogs) => [newLog, ...previousLogs]);

      setDepositFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      console.error(err);

      setErrorMessage(
        err.message || 'Unable to evaluate the deposit.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  /*
   * ---------------------------------------------------------
   * REACT PORTAL HELPER
   * ---------------------------------------------------------
   */

  const renderPortal = (id, children) => {
    const element = document.getElementById(id);

    if (!element) {
      return null;
    }

    return createPortal(children, element);
  };

  /*
   * ---------------------------------------------------------
   * RENDER
   * ---------------------------------------------------------
   */

  return (
    <>
      {/* TOTAL DEPOSITS */}
      {renderPortal(
        'portal-total-deposits',
        <span>{totalDetections}</span>
      )}

      {/* REJECTIONS */}
      {renderPortal(
        'portal-rejections',
        <span>{totalRejections}</span>
      )}

      {/* ANALYSIS STATUS */}
      {renderPortal(
        'portal-analysis-status',
        analysis ? (
          <div className="react-analysis-result">
            <div className="analysis-result-title">
              {analysis.material}
            </div>

            <div className="analysis-result-row">
              <span>Weight</span>
              <strong>{analysis.weight} g</strong>
            </div>

            <div className="analysis-result-row">
              <span>Route</span>
              <strong>{analysis.route}</strong>
            </div>

            <div
              className={
                analysis.contaminated
                  ? 'analysis-rejected'
                  : 'analysis-approved'
              }
            >
              {analysis.contaminated ? 'REJECTED' : 'APPROVED'}
            </div>

            {/* ETHERSCAN TRANSACTION LINK */}
            {analysis.explorerUrl ? (
              <a
                href={analysis.explorerUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-block',
                  marginTop: '12px',
                  padding: '8px 12px',
                  backgroundColor: '#6200ee',
                  color: '#ffffff',
                  borderRadius: '6px',
                  textDecoration: 'none',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  textAlign: 'center'
                }}
              >
                View on Etherscan ↗
              </a>
            ) : (
              <div style={{ fontSize: '11px', color: '#888', marginTop: '8px' }}>
                No blockchain transaction recorded
              </div>
            )}
          </div>
        ) : (
          <div className="analysis-idle">
            Waiting for next deposit...
          </div>
        )
      )}

      {/* QUICK DEPOSIT FORM */}
      {renderPortal(
        'portal-deposit-form',
        <form
          onSubmit={handleUserDeposit}
          className="deposit-form"
        >
          {errorMessage && (
            <div className="deposit-error">{errorMessage}</div>
          )}

          <div className="upload-area">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={(e) =>
                setDepositFile(e.target.files?.[0] || null)
              }
            />

            <div className="upload-icon">↑</div>

            <div className="upload-title">
              {depositFile
                ? depositFile.name
                : 'Drop image here'}
            </div>

            <div className="upload-subtitle">
              Click to upload recyclable item
            </div>

            <div className="upload-format">
              JPG, PNG up to 5MB
            </div>
          </div>

          <div className="deposit-fields">
            <label>
              Weight (kg)
              <input
                type="number"
                step="0.01"
                min="0"
                value={depositWeight}
                onChange={(e) =>
                  setDepositWeight(
                    parseFloat(e.target.value) || 0
                  )
                }
                required
              />
            </label>

            <label>
              Material
              <select
                value={depositMaterial}
                onChange={(e) =>
                  setDepositMaterial(e.target.value)
                }
              >
                <option value="Plastic">Plastic</option>
                <option value="Metal">Metal</option>
                <option value="E-Waste">E-Waste</option>
                <option value="Waste">Waste</option>
              </select>
            </label>

            <label>
              Wallet Address
              <input
                type="text"
                placeholder="0x..."
                value={walletAddress}
                onChange={(e) =>
                  setWalletAddress(e.target.value)
                }
              />
            </label>

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? 'ANALYZING...'
                : 'ANALYZE ITEM ✦'}
            </button>
          </div>
        </form>
      )}

      {/* ACTIVITY TABLE */}
      {renderPortal(
        'portal-activity-table',
        logs.length === 0 ? (
          <div className="activity-empty">
            <div className="activity-empty-icon">♻</div>
            <div>No deposits yet</div>
            <small>
              Your recycling activity will appear here.
            </small>
          </div>
        ) : (
          <div className="activity-list">
            {logs.slice(0, 5).map((log) => (
              <div
                className="activity-row"
                key={log.id}
              >
                <div className="activity-material-icon">
                  ♻
                </div>

                <div className="activity-main">
                  <strong>{log.material}</strong>
                  <span>{log.weight} kg</span>
                </div>

                <div className="activity-time">
                  {log.timestamp}
                </div>

                <div
                  className={
                    log.isContaminated
                      ? 'activity-status rejected'
                      : 'activity-status'
                  }
                >
                  {log.isContaminated
                    ? 'Rejected'
                    : `+${(
                        Number(log.weight) * 6
                      ).toFixed(2)} R2E`}
                </div>

                {log.explorerUrl ? (
                  <a
                    href={log.explorerUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="activity-link"
                    style={{
                      fontSize: '12px',
                      color: '#6200ee',
                      textDecoration: 'underline',
                      fontWeight: 'bold'
                    }}
                  >
                    View Tx ↗
                  </a>
                ) : (
                  <span style={{ fontSize: '11px', color: '#aaa' }}>N/A</span>
                )}
              </div>
            ))}
          </div>
        )
      )}
    </>
  );
}
