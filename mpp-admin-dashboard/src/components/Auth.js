import React, { useState } from 'react';
import './Auth.css';

const Auth = ({ onLoginSuccess }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [formData, setFormData] = useState({
    fullName: '',
    username: '',
    password: '',
    walletAddress: ''
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleMetaMaskConnect = async () => {
    if (window.ethereum) {
      try {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const wallet = accounts[0];
        setFormData((prev) => ({ ...prev, walletAddress: wallet }));
        
        if (!isRegister) {
          // Direct login via Web3 signature/wallet address
          onLoginSuccess({ username: wallet, walletAddress: wallet });
        }
      } catch (err) {
        alert('MetaMask connection failed: ' + err.message);
      }
    } else {
      alert('MetaMask is not installed!');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Call FastAPI authentication backend here
    onLoginSuccess({ username: formData.username, walletAddress: formData.walletAddress });
  };

  return (
    <div className="auth-container">
      <div className="auth-header">
        <h1 className="brand-title">Recycle<span>2</span>Earn</h1>
        <p className="brand-subtitle">Recycle waste. Earn tokens.<br/>Build a cleaner tomorrow.</p>
        <div className="eco-illustration">🌱 ♻️ 🪙</div>
      </div>

      <div className="auth-card">
        <h2>{isRegister ? 'Create Account' : 'Welcome Back!'}</h2>
        <p className="card-sub">{isRegister ? 'Join Recycle2Earn and start earning!' : 'Login to continue'}</p>

        <form onSubmit={handleSubmit}>
          {isRegister && (
            <div className="input-group">
              <span className="input-icon">👤</span>
              <input 
                type="text" 
                name="fullName" 
                placeholder="Full Name" 
                value={formData.fullName} 
                onChange={handleChange} 
                required 
              />
            </div>
          )}

          <div className="input-group">
            <span className="input-icon">👤</span>
            <input 
              type="text" 
              name="username" 
              placeholder="Username" 
              value={formData.username} 
              onChange={handleChange} 
              required 
            />
          </div>

          <div className="input-group">
            <span className="input-icon">🔒</span>
            <input 
              type="password" 
              name="password" 
              placeholder="Password" 
              value={formData.password} 
              onChange={handleChange} 
              required 
            />
          </div>

          {isRegister && (
            <div className="input-group">
              <span className="input-icon">👛</span>
              <input 
                type="text" 
                name="walletAddress" 
                placeholder="MetaMask Wallet Address" 
                value={formData.walletAddress} 
                onChange={handleChange} 
              />
            </div>
          )}

          {!isRegister && <div className="forgot-pass">Forgot Password?</div>}

          <button type="submit" className="btn-primary">
            {isRegister ? 'Register' : 'Login'}
          </button>
        </form>

        <div className="divider"><span>or</span></div>

        <button className="btn-metamask" onClick={handleMetaMaskConnect}>
          <img src="https://upload.wikimedia.org/wikipedia/commons/3/36/MetaMask_Fox.svg" alt="MetaMask" />
          {isRegister ? 'Connect with MetaMask' : 'Login with MetaMask'}
        </button>

        <div className="toggle-auth">
          {isRegister ? (
            <p>Already have an account? <span onClick={() => setIsRegister(false)}>Login</span></p>
          ) : (
            <p>Don't have an account? <span onClick={() => setIsRegister(true)}>Register</span></p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Auth;
