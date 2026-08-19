import React, { useState, useRef } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

// Configuration for Bin Capacities and Signals
const INITIAL_BINS = [
  { id: 'plastic', name: 'Plastic / Wrappers', current: 36, max: 100, color: 'bg-emerald-500', signal: 'W' },
  { id: 'metal', name: 'Metal / Cans', current: 20, max: 100, color: 'bg-sky-500', signal: 'M' },
  { id: 'e-waste', name: 'E-Waste', current: 15, max: 100, color: 'bg-amber-500', signal: 'E' },
  { id: 'reject', name: 'Reject Bin', current: 5, max: 100, color: 'bg-rose-500', signal: 'R' }
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
  const [walletAddress, setWalletAddress] = useState('0x2f45eF660233ebD3fe2ff5370fC41A1477f5f400');
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

  const truncatedWallet = walletAddress
    ? `${walletAddress.substring(0, 6)}...${walletAddress.substring(walletAddress.length - 4)}`
    : 'Not Connected';

  return (
    <div className="bg-slate-100 font-sans text-slate-800 min-h-screen flex">
      {/* SIDEBAR */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between p-5 hidden md:flex shrink-0">
        <div>
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-emerald-200">
              <i className="fa-solid fa-recycle"></i>
            </div>
            <div>
              <h1 className="font-extrabold text-slate-900 text-lg leading-none">SmartBin AI</h1>
              <span className="text-xs text-slate-400 font-medium">Sort. Earn. Verify.</span>
            </div>
          </div>

          <nav className="space-y-1.5">
            <a href="#dashboard" className="flex items-center gap-3 px-4 py-3 bg-violet-50 text-violet-700 font-semibold rounded-xl border border-violet-100 shadow-sm">
              <i className="fa-solid fa-chart-pie w-5"></i> Dashboard
            </a>
            <a href="#deposit-section" className="flex items-center gap-3 px-4 py-3 text-slate-600 hover:bg-slate-50 font-medium rounded-xl transition">
              <i className="fa-solid fa-bolt w-5 text-amber-500"></i> Deposit Waste
            </a>
            <a href="#capacity" className="flex items-center gap-3 px-4 py-3 text-slate-600 hover:bg-slate-50 font-medium rounded-xl transition">
              <i className="fa-solid fa-dumpster w-5 text-emerald-500"></i> Bin Capacities
            </a>
            <a href="#logs" className="flex items-center gap-3 px-4 py-3 text-slate-600 hover:bg-slate-50 font-medium rounded-xl transition">
              <i className="fa-solid fa-clock-rotate-left w-5 text-sky-500"></i> Audit Logs
            </a>
          </nav>
        </div>

        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-bold">
            <i className="fa-solid fa-wallet text-sm"></i>
          </div>
          <div className="overflow-hidden">
            <p className="text-xs text-slate-400 font-medium truncate">{truncatedWallet}</p>
            <p className="text-xs font-bold text-emerald-600">{totalCreditsEarned} $RECYCLE</p>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* HEADER */}
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Smart Bin Control Center</h2>
            <p className="text-xs text-slate-500">AI-Driven Waste Sorting & Web3 Incentive Network</p>
          </div>

          <div className="flex items-center gap-2 bg-slate-100 border border-slate-200 text-slate-700 px-3 py-1.5 rounded-full text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            API: <span className="font-mono font-bold text-slate-900">{API_BASE}</span>
          </div>
        </header>

        <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
          {/* ANALYTICS KPI CARDS */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-slate-200 p-5 rounded-2xl flex items-center justify-between shadow-sm">
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Total Deposits</p>
                <h3 className="text-2xl font-black text-slate-900">{totalDeposits}</h3>
              </div>
              <div className="w-12 h-12 bg-amber-500 text-white rounded-2xl flex items-center justify-center text-xl shadow-md shadow-amber-200">
                <i className="fa-solid fa-box-archive"></i>
              </div>
            </div>

            <div className="bg-white border border-slate-200 p-5 rounded-2xl flex items-center justify-between shadow-sm">
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Recycled Mass</p>
                <h3 className="text-2xl font-black text-sky-600">
                  {totalWeightGrams >= 1000 ? `${(totalWeightGrams / 1000).toFixed(2)} kg` : `${totalWeightGrams.toFixed(1)} g`}
                </h3>
              </div>
              <div className="w-12 h-12 bg-sky-500 text-white rounded-2xl flex items-center justify-center text-xl shadow-md shadow-sky-200">
                <i className="fa-solid fa-scale-balanced"></i>
              </div>
            </div>

            <div className="bg-white border border-slate-200 p-5 rounded-2xl flex items-center justify-between shadow-sm">
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Tokens Minted</p>
                <h3 className="text-2xl font-black text-emerald-600">+{totalCreditsEarned}</h3>
              </div>
              <div className="w-12 h-12 bg-emerald-500 text-white rounded-2xl flex items-center justify-center text-xl shadow-md shadow-emerald-200">
                <i className="fa-solid fa-coins"></i>
              </div>
            </div>

            <div className="bg-white border border-slate-200 p-5 rounded-2xl flex items-center justify-between shadow-sm">
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Rejections / Contaminated</p>
                <h3 className="text-2xl font-black text-rose-600">{totalRejections}</h3>
              </div>
              <div className="w-12 h-12 bg-rose-500 text-white rounded-2xl flex items-center justify-center text-xl shadow-md shadow-rose-200">
                <i className="fa-solid fa-triangle-exclamation"></i>
              </div>
            </div>
          </div>

          {/* BIN CAPACITY MONITOR */}
          <section id="capacity" className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="font-extrabold text-slate-800 text-base mb-4 flex items-center gap-2">
              <i className="fa-solid fa-dumpster text-emerald-500"></i> Bin Capacity Monitor
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {binCapacities.map(bin => {
                const percentage = Math.min(100, Math.round((bin.current / bin.max) * 100));
                return (
                  <div key={bin.id} className="p-4 border border-slate-200 rounded-xl bg-slate-50/50">
                    <div className="flex justify-between items-center mb-2">
                      <strong className="text-sm text-slate-800">{bin.name}</strong>
                      <span className="text-[10px] font-bold bg-slate-200 text-slate-700 px-2 py-0.5 rounded">
                        Signal: [{bin.signal}]
                      </span>
                    </div>
                    <div className="w-full bg-slate-200 h-2.5 rounded-full overflow-hidden mb-2">
                      <div className={`${bin.color} h-full transition-all duration-500`} style={{ width: `${percentage}%` }}></div>
                    </div>
                    <div className="flex justify-between text-xs text-slate-500 font-medium">
                      <span>{bin.current} / {bin.max} units</span>
                      <span className="font-bold text-slate-700">{percentage}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* SIMULATION FORM */}
          <section id="deposit-section" className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-extrabold text-slate-800 text-base flex items-center gap-2">
                <i className="fa-solid fa-bolt text-amber-500"></i> Simulate Material Deposit
              </h3>
              <span className="text-xs bg-violet-100 text-violet-700 font-bold px-2.5 py-1 rounded-full">
                RAG Pipeline Active
              </span>
            </div>

            {/* Quick Presets */}
            <div className="mb-4 flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold text-slate-400">Quick Presets:</span>
              {PRESET_ITEMS.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => applyPreset(item)}
                  className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1 rounded-full border border-slate-200 font-medium transition"
                >
                  + {item.name} ({item.weight}g)
                </button>
              ))}
            </div>

            {errorMessage && (
              <div className="bg-rose-50 border border-rose-200 text-rose-700 p-3 rounded-xl mb-4 text-xs font-semibold flex items-center gap-2">
                <i className="fa-solid fa-circle-exclamation text-base"></i> {errorMessage}
              </div>
            )}

            <form onSubmit={handleUserDeposit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Measured Weight (grams)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={depositWeight}
                    onChange={(e) => setDepositWeight(parseFloat(e.target.value) || 0)}
                    required
                    className="w-full bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl text-sm font-bold focus:outline-none focus:ring-2 focus:ring-violet-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Material Classification</label>
                  <select
                    value={depositMaterial}
                    onChange={(e) => setDepositMaterial(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl text-sm font-bold focus:outline-none focus:ring-2 focus:ring-violet-500"
                  >
                    <option value="Metal">Metal (Signal: M)</option>
                    <option value="Plastic">Plastic / Wrapper (Signal: W)</option>
                    <option value="E-Waste">E-Waste (Signal: E)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Sepolia Wallet Address</label>
                <input
                  type="text"
                  placeholder="0x..."
                  value={walletAddress}
                  onChange={(e) => setWalletAddress(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 px-3 py-2 rounded-xl font-mono text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Verification Image (Optional)</label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => setDepositFile(e.target.files[0] || null)}
                  className="w-full bg-slate-50 border border-slate-200 p-2 rounded-xl text-xs text-slate-600 file:mr-4 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100 cursor-pointer"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-violet-600 hover:bg-violet-700 text-white font-bold py-3 px-4 rounded-xl shadow-lg shadow-violet-200 flex items-center justify-center gap-2 transition disabled:opacity-70"
              >
                {isSubmitting ? (
                  <>
                    <i className="fa-solid fa-spinner animate-spin"></i> Evaluating RAG & Minting Tokens...
                  </>
                ) : (
                  <>
                    <i className="fa-solid fa-paper-plane"></i> Submit Deposit Simulation
                  </>
                )}
              </button>
            </form>
          </section>

          {/* AUDIT LOGS TABLE */}
          <section id="logs" className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="font-extrabold text-slate-800 text-base mb-4 flex items-center gap-2">
              <i className="fa-solid fa-clock-rotate-left text-violet-500"></i> Recent Audit Logs
            </h3>

            {logs.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-4 text-center">No processing records logged yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-100 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      <th className="pb-3 px-2">Time</th>
                      <th className="pb-3 px-2">Material</th>
                      <th className="pb-3 px-2">Weight</th>
                      <th className="pb-3 px-2">Route</th>
                      <th className="pb-3 px-2">Credits</th>
                      <th className="pb-3 px-2">Decision</th>
                      <th className="pb-3 px-2 text-right">Web3 Explorer</th>
                    </tr>
                  </thead>
                  <tbody className="text-xs divide-y divide-slate-100 font-medium text-slate-700">
                    {logs.map(log => (
                      <tr key={log.id} className="hover:bg-slate-50 transition">
                        <td className="py-3 px-2 font-mono text-slate-400">{log.timestamp}</td>
                        <td className="py-3 px-2 font-bold text-slate-800">{log.material}</td>
                        <td className="py-3 px-2">{log.weight}g</td>
                        <td className="py-3 px-2">
                          <span className="bg-slate-100 text-slate-700 font-bold px-2 py-0.5 rounded font-mono text-[10px]">
                            [{log.route}]
                          </span>
                        </td>
                        <td className="py-3 px-2 font-bold text-emerald-600">+{log.credits}</td>
                        <td className="py-3 px-2">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            log.isContaminated ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
                          }`}>
                            {log.decision}
                          </span>
                        </td>
                        <td className="py-3 px-2 text-right">
                          {log.explorerUrl ? (
                            <a
                              href={log.explorerUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sky-600 font-bold hover:underline"
                            >
                              View Tx <i className="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                            </a>
                          ) : (
                            <span className="text-slate-400">No Tx</span>
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
      </main>
    </div>
  );
}
