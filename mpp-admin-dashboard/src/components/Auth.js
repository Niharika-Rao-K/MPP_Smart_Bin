import React, { useState } from 'react';
import './Auth.css';

const API_BASE =
  process.env.REACT_APP_API_URL ||
  'https://solid-succotash-97w5vgqj54vr277wv-8000.app.github.dev';

export default function Auth({ onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false);

  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [walletAddress, setWalletAddress] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();

    setErrorMessage('');
    setSuccessMessage('');
    setLoading(true);

    try {
      const endpoint = isRegister
        ? `${API_BASE}/api/auth/register`
        : `${API_BASE}/api/auth/login`;

      const body = isRegister
        ? {
            full_name: fullName,
            username,
            password,
            wallet_address: walletAddress,
          }
        : {
            username,
            password,
          };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed.');
      }

      /*
       * Backend returns:
       * data.user = {
       *   id,
       *   full_name,
       *   username,
       *   wallet_address
       * }
       */

      if (data.user) {
        onLoginSuccess({
          id: data.user.id,
          fullName: data.user.full_name,
          username: data.user.username,
          walletAddress: data.user.wallet_address,
        });
      }
    } catch (error) {
      console.error('Authentication error:', error);
      setErrorMessage(
        error.message || 'Unable to connect to the authentication server.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = () => {
    setErrorMessage(
      'Password recovery will be connected to MetaMask in the next step.'
    );
  };

  const handleMetaMask = async () => {
    setErrorMessage('');

    if (!window.ethereum) {
      setErrorMessage(
        'MetaMask is not installed. Please install the MetaMask extension.'
      );
      return;
    }

    try {
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts',
      });

      if (accounts && accounts.length > 0) {
        setWalletAddress(accounts[0]);
      }
    } catch (error) {
      console.error('MetaMask connection failed:', error);
      setErrorMessage('MetaMask connection was cancelled or failed.');
    }
  };

  return (
    <div className="auth-wrapper-body">
      <div className="mobile-frame">

        {/* Background leaves */}
        <img
          src="/assets/leaf-bg-tl.svg"
          className="leaf-bg-tl"
          alt=""
        />

        <img
          src="/assets/leaf-bg-tr.svg"
          className="leaf-bg-tr"
          alt=""
        />

        <img
          src="/assets/leaf-bg-bottom.svg"
          className="leaf-bg-bottom"
          alt=""
        />

        {/* Header */}
        <div className="brand-header">
          <div className="brand-title">
            Recycle2Earn
            <span className="sprout-icon">🌱</span>
          </div>

          <div className="brand-subtitle">
            Recycle responsibly. Earn rewards.
          </div>
        </div>

        {/* Hero artwork */}
        <div className="hero-art">
          <img
            src="/assets/recycle-hero.png"
            alt="Recycle2Earn"
          />
        </div>

        {/* Authentication card */}
        <div className="auth-card">

          <div className="card-title">
            {isRegister ? 'Create Account' : 'Welcome Back'}
          </div>

          <div className="card-subtitle">
            {isRegister
              ? 'Join the recycling rewards community'
              : 'Login to continue recycling'}
          </div>

          {errorMessage && (
            <div
              style={{
                background: '#fff1f1',
                color: '#b42318',
                border: '1px solid #f3c2c2',
                borderRadius: '10px',
                padding: '9px 10px',
                marginBottom: '10px',
                fontSize: '12px',
                textAlign: 'center',
              }}
            >
              {errorMessage}
            </div>
          )}

          {successMessage && (
            <div
              style={{
                background: '#eefaf1',
                color: '#176b38',
                border: '1px solid #c5e6cf',
                borderRadius: '10px',
                padding: '9px 10px',
                marginBottom: '10px',
                fontSize: '12px',
                textAlign: 'center',
              }}
            >
              {successMessage}
            </div>
          )}

          <form onSubmit={handleSubmit}>

            {/* Full name - registration only */}
            {isRegister && (
              <div className="input-group">
                <span className="input-icon">👤</span>

                <input
                  className="auth-input"
                  type="text"
                  placeholder="Full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>
            )}

            {/* Username */}
            <div className="input-group">
              <span className="input-icon">👤</span>

              <input
                className="auth-input"
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>

            {/* Password */}
            <div className="input-group">
              <span className="input-icon">🔒</span>

              <input
                className="auth-input"
                type={showPassword ? 'text' : 'password'}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />

              <button
                type="button"
                className="eye-btn"
                onClick={() => setShowPassword((previous) => !previous)}
                aria-label="Toggle password visibility"
              >
                {showPassword ? '🙈' : '👁'}
              </button>
            </div>

            {/* Wallet - registration only */}
            {isRegister && (
              <div className="input-group">
                <span className="input-icon">💳</span>

                <input
                  className="auth-input"
                  type="text"
                  placeholder="Wallet address (0x...)"
                  value={walletAddress}
                  onChange={(e) => setWalletAddress(e.target.value)}
                  required
                />
              </div>
            )}

            {/* Forgot password */}
            {!isRegister && (
              <button
                type="button"
                className="forgot-link"
                onClick={handleForgotPassword}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                  marginLeft: 'auto',
                }}
              >
                Forgot password?
              </button>
            )}

            {/* Submit */}
            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
            >
              {loading
                ? 'PLEASE WAIT...'
                : isRegister
                ? 'CREATE ACCOUNT'
                : 'LOGIN'}
            </button>

          </form>

          {/* Divider */}
          <div className="divider">
            <span>OR</span>
          </div>

          {/* MetaMask */}
          <button
            type="button"
            className="btn-metamask"
            onClick={handleMetaMask}
          >
            <span>🦊</span>
            <span>Continue with MetaMask</span>
          </button>

          {/* Login/Register switch */}
          <div className="switch-text">
            {isRegister
              ? 'Already have an account? '
              : "Don't have an account? "}

            <button
              type="button"
              onClick={() => {
                setIsRegister((previous) => !previous);
                setErrorMessage('');
                setSuccessMessage('');
              }}
            >
              {isRegister ? 'Login' : 'Register'}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="footer-section">
          <div className="footer-text">
            Turn your waste into rewards ♻
          </div>

          <div className="footer-art">
            <span className="footer-icon-svg">♻️</span>
            <span className="footer-arrow-svg">→</span>
            <span className="footer-wallet-img">🪙</span>
          </div>
        </div>

      </div>
    </div>
  );
}
