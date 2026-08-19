import React, { useState } from 'react';

const API_URL = 'http://localhost:8000/api/rag/evaluate';

function App() {
  // Form State
  const [material, setMaterial] = useState('Metal');
  const [weight, setWeight] = useState(13.5);
  const [wallet, setWallet] = useState('0x2f45eF660233ebD3fe2ff5370fC41A1477f5f400');
  const [imageFile, setImageFile] = useState(null);
  const [uploadLabel, setUploadLabel] = useState('Drop item photo or click to browse');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Global Metrics
  const [totalTokens, setTotalTokens] = useState(0);
  const [totalWeight, setTotalWeight] = useState(0);
  const [totalDeposits, setTotalDeposits] = useState(0);

  // Live Hardware & AI Output
  const [activeSignal, setActiveSignal] = useState(null);
  const [fusionDecision, setFusionDecision] = useState('WAITING_FOR_INPUT');
  const [fusionAction, setFusionAction] = useState('Insert material to trigger pipeline.');

  // Web3 Reward Status
  const [txMinted, setTxMinted] = useState(0);
  const [txHash, setTxHash] = useState('0x0000000000000000000000000000000000000000');
  const [explorerUrl, setExplorerUrl] = useState('#');
  const [txConfirmed, setTxConfirmed] = useState(false);

  // Activity Log
  const [activityLog, setActivityLog] = useState([]);

  const handleImageChange = (e) => {
    if (e.target.files.length > 0) {
      setImageFile(e.target.files[0]);
      setUploadLabel(`Selected: ${e.target.files[0].name}`);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    const formData = new FormData();
    formData.append('label', material);
    formData.append('real_weight_g', parseFloat(weight));
    formData.append('wallet_address', wallet);
    if (imageFile) {
      formData.append('image', imageFile);
    }

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Server returned error status ${response.status}`);
      }

      const data = await response.json();
      
      // Update Metrics
      const minted = data.web3_reward?.tokens_minted || 0;
      const stableWeight = data.stable_weight_g || 0;

      setTotalDeposits((prev) => prev + 1);
      setTotalWeight((prev) => prev + stableWeight);
      setTotalTokens((prev) => prev + minted);

      // Update Hardware Feedback
      setActiveSignal(data.hardware_route_signal);
      setFusionDecision(data.fusion_result?.decision || 'N/A');
      setFusionAction(data.fusion_result?.action || 'N/A');

      // Update Web3 Data
      const currentTxHash = data.web3_reward?.tx_hash;
      const currentExplorerUrl = data.web3_reward?.explorer_url || '#';

      if (currentTxHash) {
        setTxMinted(minted);
        setTxHash(currentTxHash);
        setExplorerUrl(currentExplorerUrl);
        setTxConfirmed(true);
      } else {
        setTxMinted(0);
        setTxHash('No wallet provided for minting');
        setTxConfirmed(false);
      }

      // Add to Activity Log Table
      const newEntry = {
        time: new Date().toLocaleTimeString(),
        material: data.predicted_label || material,
        weight: stableWeight,
        signal: data.hardware_route_signal,
        minted: minted,
        txHash: currentTxHash,
        explorerUrl: currentExplorerUrl
      };

      setActivityLog((prev) => [newEntry, ...prev]);

    } catch (err) {
      alert(`API Error: ${err.message}. Ensure backend is running on port 8000.`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div class="bg-slate-100 font-sans text-slate-800 min-h-screen flex">
      {/* SIDEBAR */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between p-5 hidden md:flex shrink-0">
        <div>
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-emerald-200">
              <i className="fa-solid fa-recycle"></i>
            </div>
            <div>
              <h1 className="font-extrabold text-slate-900 text-lg leading-none">Recycle2Earn</h1>
              <span className="text-xs text-slate-400 font-medium">Recycle. Earn. Level Up.</span>
            </div>
          </div>

          <nav className="space-y-1.5">
            <a href="#dashboard" className="flex items-center gap-3 px-4 py-3 bg-violet-50 text-violet-700 font-semibold rounded-xl border border-violet-100 shadow-sm">
              <i className="fa-solid fa-chart-pie w-5"></i> Dashboard
            </a>
            <a href="#deposit-section" className="flex items-center gap-3 px-4 py-3 text-slate-600 hover:bg-slate-50 font-medium rounded-xl transition">
              <i className="fa-solid fa-dumpster-fire w-5 text-amber-500"></i> Deposit Waste
            </a>
            <a href="#ai" className="flex items-center gap-3 px-4 py-3 text-slate-600 hover:bg-slate-50 font-medium rounded-xl transition">
              <i className="fa-solid fa-microchip w-5 text-emerald-500"></i> AI & Hardware
            </a>
            <a href="#web3" className="flex items-center gap-3 px-4 py-3 text-slate-600 hover:bg-slate-50 font-medium rounded-xl transition">
              <i className="fa-solid fa-cubes w-5 text-sky-500"></i> Blockchain
            </a>
          </nav>
        </div>

        <div className="space-y-4">
          <div className="bg-gradient-to-br from-violet-500 to-indigo-600 p-4 rounded-2xl text-white shadow-md">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-violet-200">User Status</span>
              <span className="bg-white/20 text-xs px-2 py-0.5 rounded-full font-bold">Level 2</span>
            </div>
            <p className="font-bold text-sm mb-1">Eco Recycler</p>
            <div className="w-full bg-black/20 h-2 rounded-full overflow-hidden mb-2">
              <div className="bg-emerald-400 h-full w-[65%] rounded-full"></div>
            </div>
            <p className="text-[11px] text-violet-200">350 XP to Level 3</p>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-bold">
              <i className="fa-solid fa-wallet text-sm"></i>
            </div>
            <div className="overflow-hidden">
              <p className="text-xs text-slate-400 font-medium truncate">
                {wallet ? `${wallet.substring(0, 6)}...${wallet.substring(wallet.length - 4)}` : 'Not Connected'}
              </p>
              <p className="text-xs font-bold text-emerald-600">{totalTokens} $RECYCLE</p>
            </div>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Welcome back, Recycler! 👋</h2>
            <p className="text-xs text-slate-500">Here is your recycling impact and web3 rewards overview.</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-700 px-3 py-1.5 rounded-full text-xs font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Sepolia Testnet
            </div>
            <div className="w-10 h-10 rounded-full bg-violet-100 text-violet-600 border border-violet-200 flex items-center justify-center font-bold">
              <i className="fa-solid fa-user"></i>
            </div>
          </div>
        </header>

        <div className="p-6 space-y-6 max-w-7xl mx-auto w-full">
          {/* METRICS */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-emerald-50/80 border border-emerald-200/60 p-5 rounded-2xl flex items-center justify-between shadow-sm">
              <div>
                <p className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-1">Tokens Earned</p>
                <h3 className="text-2xl font-black text-emerald-900">{totalTokens}</h3>
                <p className="text-[11px] text-emerald-700 font-medium mt-1"><i className="fa-solid fa-arrow-up text-emerald-600"></i> $RECYCLE Minted</p>
              </div>
              <div className="w-12 h-12 bg-emerald-500 text-white rounded-2xl flex items-center justify-center text-xl shadow-md shadow-emerald-200">
                <i className="fa-solid fa-coins"></i>
              </div>
            </div>

            <div className="bg-violet-50/80 border border-violet-200/60 p-5 rounded-2xl flex items-center justify-between shadow-sm">
              <div>
                <p className="text-xs font-bold text-violet-600 uppercase tracking-wider mb-1">Weight Recycled</p>
                <h3 className="text-2xl font-black text-violet-900">{totalWeight.toFixed(1)} <span className="text-base font-semibold">g</span></h3>
                <p className="text-[11px] text-violet-700 font-medium mt-1"><i className="fa-solid fa-weight-hanging"></i> Verified by LoadCell</p>
              </div>
              <div className="w-12 h-12 bg-violet-500 text-white rounded-2xl flex items-center justify-center text-xl shadow-md shadow-violet-200">
                <i className="fa-solid fa-scale-balanced"></i>
              </div>
            </div>

            <div className="bg-amber-50/80 border border-amber-200/60 p-5 rounded-2xl flex items-center justify-between shadow-sm">
              <div>
                <p className="text-xs font-bold text-amber-600 uppercase tracking-wider mb-1">Total Deposits</p>
                <h3 className="text-2xl font-black text-amber-900">{totalDeposits}</h3>
                <p className="text-[11px] text-amber-700 font-medium mt-1"><i className="fa-solid fa-circle-check"></i> RAG Verified</p>
              </div>
              <div className="w-12 h-12 bg-amber-500 text-white rounded-2xl flex items-center justify-center text-xl shadow-md shadow-amber-200">
                <i className="fa-solid fa-box-archive"></i>
              </div>
            </div>

            <div className="bg-sky-50/80 border border-sky-200/60 p-5 rounded-2xl flex items-center justify-between shadow-sm">
              <div>
                <p className="text-xs font-bold text-sky-600 uppercase tracking-wider mb-1">CO₂ Offset</p>
                <h3 className="text-2xl font-black text-sky-900">{(totalWeight * 0.0025).toFixed(2)} <span className="text-base font-semibold">kg</span></h3>
                <p className="text-[11px] text-sky-700 font-medium mt-1"><i className="fa-solid fa-leaf"></i> Environmental Impact</p>
              </div>
              <div className="w-12 h-12 bg-sky-500 text-white rounded-2xl flex items-center justify-center text-xl shadow-md shadow-sky-200">
                <i className="fa-solid fa-cloud-sun"></i>
              </div>
            </div>
          </div>

          {/* FORM & HARDWARE FEED */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" id="deposit-section">
            <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-extrabold text-slate-800 text-base flex items-center gap-2">
                    <i className="fa-solid fa-bolt text-amber-500"></i> Quick Deposit Simulation
                  </h3>
                  <span className="text-[11px] bg-slate-100 text-slate-600 font-bold px-2 py-0.5 rounded-full">FastAPI RAG</span>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1">Sample Waste Image</label>
                    <div className="border-2 border-dashed border-violet-200 bg-violet-50/50 hover:bg-violet-50 p-4 rounded-xl text-center cursor-pointer transition relative">
                      <input type="file" accept="image/*" onChange={handleImageChange} className="absolute inset-0 opacity-0 cursor-pointer" />
                      <i className="fa-solid fa-cloud-arrow-up text-2xl text-violet-500 mb-1"></i>
                      <p className={`text-xs font-semibold ${imageFile ? 'text-violet-600 font-bold' : 'text-slate-700'}`}>{uploadLabel}</p>
                      <p className="text-[10px] text-slate-400">JPG, PNG up to 5MB</p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1">Measured Weight (g)</label>
                    <div className="relative">
                      <input type="number" step="0.1" value={weight} onChange={(e) => setWeight(e.target.value)} required className="w-full bg-slate-50 border border-slate-200 px-3 py-2.5 rounded-xl font-bold text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
                      <span className="absolute right-3 top-2.5 text-xs font-bold text-slate-400">grams</span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1">Material Classification</label>
                    <select value={material} onChange={(e) => setMaterial(e.target.value)} className="w-full bg-slate-50 border border-slate-200 px-3 py-2.5 rounded-xl font-bold text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
                      <option value="Metal">Metal (Signal: M)</option>
                      <option value="Plastic">Plastic (Signal: W)</option>
                      <option value="E-Waste">E-Waste (Signal: E)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1">Sepolia Wallet Address</label>
                    <input type="text" value={wallet} onChange={(e) => setWallet(e.target.value)} placeholder="0x..." className="w-full bg-slate-50 border border-slate-200 px-3 py-2.5 rounded-xl font-mono text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-500" />
                  </div>

                  <button type="submit" disabled={isSubmitting} className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white font-bold py-3 px-4 rounded-xl shadow-lg shadow-violet-200 flex items-center justify-center gap-2 transition disabled:opacity-50">
                    {isSubmitting ? (
                      <><i className="fa-solid fa-spinner animate-spin"></i> Processing RAG & Web3...</>
                    ) : (
                      <><i className="fa-solid fa-paper-plane"></i> Submit Deposit & Evaluate</>
                    )}
                  </button>
                </form>
              </div>
            </div>

            <div className="lg:col-span-7 space-y-6">
              {/* HARDWARE ROUTING */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-extrabold text-slate-800 text-base flex items-center gap-2">
                    <i className="fa-solid fa-gears text-emerald-500"></i> Hardware Route & AI Fusion
                  </h3>
                  <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span> Live Conveyor Signal
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-4 text-center">
                  <div className={`p-3 rounded-xl border transition ${activeSignal === 'M' ? 'border-2 border-emerald-500 bg-emerald-50 shadow-md' : 'border-slate-200 bg-slate-50 opacity-50'}`}>
                    <span className="text-xs font-bold text-slate-500">Signal [M]</span>
                    <p className="font-black text-slate-800 text-sm">METAL</p>
                  </div>
                  <div className={`p-3 rounded-xl border transition ${activeSignal === 'W' ? 'border-2 border-emerald-500 bg-emerald-50 shadow-md' : 'border-slate-200 bg-slate-50 opacity-50'}`}>
                    <span className="text-xs font-bold text-slate-500">Signal [W]</span>
                    <p className="font-black text-slate-800 text-sm">PLASTIC</p>
                  </div>
                  <div className={`p-3 rounded-xl border transition ${activeSignal === 'E' ? 'border-2 border-emerald-500 bg-emerald-50 shadow-md' : 'border-slate-200 bg-slate-50 opacity-50'}`}>
                    <span className="text-xs font-bold text-slate-500">Signal [E]</span>
                    <p className="font-black text-slate-800 text-sm">E-WASTE</p>
                  </div>
                </div>

                <div className="p-4 bg-slate-900 rounded-xl text-slate-200 font-mono text-xs space-y-1">
                  <p className="text-slate-500">// Sensor Fusion Output</p>
                  <p>Decision: <span className="text-emerald-400 font-bold">{fusionDecision}</span></p>
                  <p>Action: <span className="text-sky-300">{fusionAction}</span></p>
                </div>
              </div>

              {/* BLOCKCHAIN STATUS */}
              <div className="bg-gradient-to-br from-slate-900 to-indigo-950 p-6 rounded-2xl text-white shadow-lg relative overflow-hidden">
                <div className="absolute -right-6 -bottom-6 text-indigo-800/30 text-9xl font-black pointer-events-none">
                  <i className="fa-brands fa-ethereum"></i>
                </div>

                <div className="flex items-center justify-between mb-4 relative z-10">
                  <h3 className="font-extrabold text-white text-base flex items-center gap-2">
                    <i className="fa-solid fa-link text-sky-400"></i> Web3 Reward Minting
                  </h3>
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold font-mono ${txConfirmed ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-indigo-500/30 border border-indigo-400/30 text-indigo-200'}`}>
                    {txConfirmed ? 'Confirmed' : 'Idle'}
                  </span>
                </div>

                <div className="space-y-3 relative z-10">
                  <div>
                    <span className="text-[11px] text-slate-400 font-medium">Minted Tokens</span>
                    <p className="text-2xl font-black text-emerald-400">+{txMinted} $RECYCLE</p>
                  </div>

                  <div>
                    <span className="text-[11px] text-slate-400 font-medium">Sepolia Transaction Hash</span>
                    <p className="font-mono text-xs text-indigo-300 truncate">{txHash}</p>
                  </div>

                  <a href={explorerUrl} target="_blank" rel="noreferrer" className={`inline-flex items-center gap-2 text-xs font-bold text-sky-400 hover:text-sky-300 transition mt-2 ${!txConfirmed && 'pointer-events-none opacity-50'}`}>
                    View on Sepolia Etherscan <i className="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* ACTIVITY LOG TABLE */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-extrabold text-slate-800 text-base flex items-center gap-2">
                <i className="fa-solid fa-clock-rotate-left text-violet-500"></i> Recent Deposit Operations
              </h3>
              <span className="text-xs text-slate-400 font-medium">Real-time Session Logs</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    <th className="pb-3 px-2">Time</th>
                    <th className="pb-3 px-2">Material</th>
                    <th className="pb-3 px-2">Weight</th>
                    <th className="pb-3 px-2">Hardware Route</th>
                    <th className="pb-3 px-2">Tokens Minted</th>
                    <th className="pb-3 px-2 text-right">Blockchain Tx</th>
                  </tr>
                </thead>
                <tbody className="text-xs divide-y divide-slate-100 font-medium text-slate-700">
                  {activityLog.length === 0 ? (
                    <tr className="text-slate-400 italic">
                      <td colSpan="6" className="py-6 text-center">No deposit operations submitted yet.</td>
                    </tr>
                  ) : (
                    activityLog.map((log, index) => (
                      <tr key={index} className="hover:bg-slate-50/80 transition">
                        <td className="py-3 px-2 font-mono text-slate-400">{log.time}</td>
                        <td className="py-3 px-2 font-bold text-slate-800">{log.material}</td>
                        <td className="py-3 px-2 font-semibold">{log.weight}g</td>
                        <td className="py-3 px-2">
                          <span className="bg-violet-100 text-violet-700 font-bold px-2 py-0.5 rounded-md text-[10px]">
                            Signal [{log.signal}]
                          </span>
                        </td>
                        <td className="py-3 px-2 font-bold text-emerald-600">+{log.minted} RECYCLE</td>
                        <td className="py-3 px-2 text-right">
                          {log.txHash ? (
                            <a href={log.explorerUrl} target="_blank" rel="noreferrer" className="text-sky-600 font-bold hover:underline">
                              View Tx <i className="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                            </a>
                          ) : (
                            <span className="text-slate-400">N/A</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
