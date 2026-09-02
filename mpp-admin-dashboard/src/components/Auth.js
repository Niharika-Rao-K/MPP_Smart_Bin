import React, { useState } from 'react';
import './Auth.css';

const USERS_KEY = 'r2e_users';
const ACTIVE_WALLET_KEY = 'r2e_active_wallet';

function getUsers() {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY)) || [];
  } catch {
    return [];
  }
}

function getWallet(user) {
  return user.wallet || user.walletAddress || '';
}

const Auth = ({ onLoginSuccess }) => {
  const [isRegister, setIsRegister] = useState(false);

  const [formData, setFormData] = useState({
    fullName: '',
    username: '',
    password: '',
    walletAddress: ''
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const startSession = (user) => {
    const wallet = getWallet(user);

    localStorage.setItem(ACTIVE_WALLET_KEY, wallet);

    onLoginSuccess({
      fullName: user.fullName || '',
      username: user.username,
      walletAddress: wallet
    });
  };

  const handleMetaMaskConnect = async () => {
    if (!window.ethereum) {
      alert('MetaMask is not installed!');
      return;
    }

    try {
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts'
      });

      const wallet = accounts[0];

      setFormData((previous) => ({
        ...previous,
        walletAddress: wallet
      }));

      // On the Login screen, allow MetaMask only for an existing registered user.
      if (!isRegister) {
        const user = getUsers().find(
          (item) => getWallet(item).toLowerCase() === wallet.toLowerCase()
        );

        if (!user) {
          alert('This wallet is not registered. Please create an account first.');
          setIsRegister(true);
          return;
        }

        startSession(user);
      }
    } catch (err) {
      alert(`MetaMask connection failed: ${err.message}`);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const fullName = formData.fullName.trim();
    const username = formData.username.trim();
    const password = formData.password;
    const wallet = formData.walletAddress.trim();

    if (isRegister) {
      if (!/^0x[a-fA-F0-9]{40}$/.test(wallet)) {
        alert('Please enter a valid MetaMask wallet address starting with 0x.');
        return;
      }

      const users = getUsers();

      const alreadyRegistered = users.some(
        (item) =>
          item.username.toLowerCase() === username.toLowerCase() ||
          getWallet(item).toLowerCase() === wallet.toLowerCase()
      );

      if (alreadyRegistered) {
        alert('That username or wallet address is already registered.');
        return;
      }

      const newUser = {
        fullName,
        username,
        password,
        wallet,
        walletAddress: wallet,
        totalWeight: 0,
        totalTokens: 0,
        streak: 1,
        deposits: []
      };

      users.push(newUser);
      localStorage.setItem(USERS_KEY, JSON.stringify(users));
      startSession(newUser);
      return;
    }

    const user = getUsers().find(
      (item) =>
        item.username.toLowerCase() === username.toLowerCase() &&
        item.password === password
    );

    if (!user) {
      alert('Invalid username or password.');
      return;
    }

    startSession(user);
  };

  return (
    <div className="auth-container">
      <div className="auth-header">
        <h1 className="brand-title">
          Recycle<span>2</span>Earn
        </h1>

        <p className="brand-subtitle">
          Recycle waste. Earn tokens.
          <br />
          Build a cleaner tomorrow.
        </p>

        <div className="eco-illustration">🌱 ♻️ 🪙</div>
      </div>

      <div className="auth-card">
        <h2>{isRegister ? 'Create Account' : 'Welcome Back!'}</h2>

        <p className="card-sub">
          {isRegister
            ? 'Join Recycle2Earn and start earning!'
            : 'Login to continue'}
        </p>

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
                required
                pattern="^0x[a-fA-F0-9]{40}$"
              />
            </div>
          )}

          {!isRegister && (
            <div className="forgot-pass">Forgot Password?</div>
          )}

          <button type="submit" className="btn-primary">
            {isRegister ? 'Register' : 'Login'}
          </button>
        </form>

        <div className="divider">
          <span>or</span>
        </div>

        <button className="btn-metamask" onClick={handleMetaMaskConnect}>
          <img
            src="https://upload.wikimedia.org/wikipedia/commons/3/36/MetaMask_Fox.svg"
            alt="MetaMask"
          />
          {isRegister ? 'Connect with MetaMask' : 'Login with MetaMask'}
        </button>

        <div className="toggle-auth">
          {isRegister ? (
            <p>
              Already have an account?{' '}
              <span onClick={() => setIsRegister(false)}>Login</span>
            </p>
          ) : (
            <p>
              Don&apos;t have an account?{' '}
              <span onClick={() => setIsRegister(true)}>Register</span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Auth;
