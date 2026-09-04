import React, { useState } from "react";
import "./Auth.css";

const API_BASE =
  process.env.REACT_APP_API_URL ||
  "https://solid-succotash-97w5vgqj54vr277wv-8000.app.github.dev";

const ACTIVE_WALLET_KEY = "r2e_active_wallet";

const customWalletSrc =
  "https://upload.wikimedia.org/wikipedia/commons/3/36/MetaMask_Fox.svg";

const heroImageSrc =
  "https://plus.unsplash.com/premium_photo-1742937587723-35e893fc4f9f?q=80&w=1067&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1...";

function Auth({ onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false);

  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [walletAddress, setWalletAddress] = useState("");

  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showRegisterPassword, setShowRegisterPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const showRegister = () => {
    setIsRegister(true);
    setError("");
  };

  const showLogin = () => {
    setIsRegister(false);
    setError("");
  };

  const handleLogin = async (event) => {
    event.preventDefault();

    setError("");

    if (!username.trim() || !password) {
      setError("Please enter your username and password.");
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username.trim(),
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed.");
      }

      const user = data.user;

      localStorage.setItem(
        "r2e_user",
        JSON.stringify({
          fullName: user.full_name,
          username: user.username,
          walletAddress: user.wallet_address,
        })
      );

      localStorage.setItem(
        ACTIVE_WALLET_KEY,
        user.wallet_address
      );

      if (onLoginSuccess) {
        onLoginSuccess({
          fullName: user.full_name,
          username: user.username,
          walletAddress: user.wallet_address,
        });
      }

      // Your existing dashboard is still dashboard.html.
      window.location.replace("/dashboard.html");
    } catch (err) {
      setError(err.message || "Unable to login.");
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (event) => {
    event.preventDefault();

    setError("");

    if (!fullName.trim()) {
      setError("Please enter your full name.");
      return;
    }

    if (!username.trim()) {
      setError("Please enter a username.");
      return;
    }

    if (!password) {
      setError("Please enter a password.");
      return;
    }

    if (password.length < 4) {
      setError("Password must be at least 4 characters.");
      return;
    }

    if (!walletAddress.trim()) {
      setError("Please enter your wallet address.");
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          full_name: fullName.trim(),
          username: username.trim(),
          password,
          wallet_address: walletAddress.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Registration failed.");
      }

      const user = data.user;

      localStorage.setItem(
        "r2e_user",
        JSON.stringify({
          fullName: user.full_name,
          username: user.username,
          walletAddress: user.wallet_address,
        })
      );

      localStorage.setItem(
        ACTIVE_WALLET_KEY,
        user.wallet_address
      );

      alert("Account created successfully!");

      if (onLoginSuccess) {
        onLoginSuccess({
          fullName: user.full_name,
          username: user.username,
          walletAddress: user.wallet_address,
        });
      }

      window.location.replace("/dashboard.html");
    } catch (err) {
      setError(err.message || "Unable to create account.");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = (event) => {
    event.preventDefault();

    alert(
      "Forgot password functionality will be added next. Your account passwords are now stored securely in the backend database."
    );
  };

  const handleMetaMaskLogin = async () => {
    setError("");

    if (!window.ethereum) {
      alert(
        "MetaMask is not installed. Please install MetaMask and try again."
      );
      return;
    }

    alert(
      "MetaMask login will be connected to the backend in the next step."
    );
  };

  const handleMetaMaskRegister = async () => {
    setError("");

    if (!window.ethereum) {
      alert(
        "MetaMask is not installed. Please install MetaMask and try again."
      );
      return;
    }

    alert(
      "MetaMask registration will be connected to the backend in the next step."
    );
  };

  const togglePassword = (type) => {
    if (type === "login") {
      setShowLoginPassword((previous) => !previous);
    } else {
      setShowRegisterPassword((previous) => !previous);
    }
  };

  return (
    <div className="auth-wrapper-body">
      <div className="mobile-frame">

        {/* Background leaf - top left */}
        <svg
          className="leaf-bg-tl"
          viewBox="0 0 110 130"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M0 0C35 10 65 25 80 55C92 78 91 103 72 130"
            stroke="#B8D2B5"
            strokeWidth="3"
            strokeLinecap="round"
            opacity="0.55"
          />
          <path
            d="M8 8C28 18 47 33 58 52"
            stroke="#C8DEC5"
            strokeWidth="2"
            strokeLinecap="round"
            opacity="0.7"
          />
          <path
            d="M22 21C10 38 7 53 12 67C29 60 39 48 39 35C36 29 30 24 22 21Z"
            fill="#D1E2CE"
            opacity="0.65"
          />
          <path
            d="M52 44C39 58 37 73 43 87C59 79 67 66 66 54C63 49 58 46 52 44Z"
            fill="#C3D9BF"
            opacity="0.65"
          />
        </svg>

        {/* Background leaf - top right */}
        <svg
          className="leaf-bg-tr"
          viewBox="0 0 110 130"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M110 0C75 10 45 25 30 55C18 78 19 103 38 130"
            stroke="#B8D2B5"
            strokeWidth="3"
            strokeLinecap="round"
            opacity="0.55"
          />
          <path
            d="M102 8C82 18 63 33 52 52"
            stroke="#C8DEC5"
            strokeWidth="2"
            strokeLinecap="round"
            opacity="0.7"
          />
          <path
            d="M88 21C100 38 103 53 98 67C81 60 71 48 71 35C74 29 80 24 88 21Z"
            fill="#D1E2CE"
            opacity="0.65"
          />
          <path
            d="M58 44C71 58 73 73 67 87C51 79 43 66 44 54C47 49 52 46 58 44Z"
            fill="#C3D9BF"
            opacity="0.65"
          />
        </svg>

        {/* Back button */}
        {isRegister && (
          <button
            className="back-btn"
            type="button"
            onClick={showLogin}
            aria-label="Back to login"
          >
            <i className="fa-solid fa-arrow-left"></i>
          </button>
        )}

        {/* Brand */}
        <div className="brand-header">
          <div className="brand-title">
            <i className="fa-solid fa-leaf sprout-icon"></i>
            Recycle2Earn
          </div>

          <div className="brand-subtitle">
            Recycle waste. Earn tokens.
            <br />
            Build a cleaner tomorrow.
          </div>
        </div>

        {/* Hero artwork */}
        <div className="hero-art">
          <img
            src={heroImageSrc}
            alt="Recycle Token Icon"
          />
        </div>

        {/* Auth card */}
        <div className="auth-card">

          {/* LOGIN */}
          {!isRegister && (
            <>
              <div className="card-title">
                Welcome Back!
              </div>

              <div className="card-subtitle">
                Login to continue
              </div>

              <form onSubmit={handleLogin}>

                <div className="input-group">
                  <i className="fa-solid fa-user input-icon"></i>

                  <input
                    className="auth-input"
                    type="text"
                    placeholder="Username"
                    value={username}
                    onChange={(event) =>
                      setUsername(event.target.value)
                    }
                    autoComplete="username"
                  />
                </div>

                <div className="input-group">
                  <i className="fa-solid fa-lock input-icon"></i>

                  <input
                    className="auth-input"
                    type={
                      showLoginPassword
                        ? "text"
                        : "password"
                    }
                    placeholder="Password"
                    value={password}
                    onChange={(event) =>
                      setPassword(event.target.value)
                    }
                    autoComplete="current-password"
                  />

                  <button
                    className="eye-btn"
                    type="button"
                    onClick={() =>
                      togglePassword("login")
                    }
                    aria-label="Toggle password visibility"
                  >
                    <i
                      className={
                        showLoginPassword
                          ? "fa-solid fa-eye-slash"
                          : "fa-solid fa-eye"
                      }
                    ></i>
                  </button>
                </div>

                <button
                  className="forgot-link"
                  type="button"
                  onClick={handleForgotPassword}
                >
                  Forgot Password?
                </button>

                {error && (
                  <div className="auth-error">
                    {error}
                  </div>
                )}

                <button
                  className="btn-primary"
                  type="submit"
                  disabled={loading}
                >
                  {loading ? "Logging in..." : "Login"}
                </button>

              </form>

              <div className="divider">
                <span>or</span>
              </div>

              <button
                className="btn-metamask"
                type="button"
                onClick={handleMetaMaskLogin}
              >
                <img
                  className="wallet-icon-img"
                  src={customWalletSrc}
                  alt="MetaMask Wallet"
                />
                Login with MetaMask
              </button>

              <div className="switch-text">
                Don't have an account?{" "}
                <button
                  type="button"
                  onClick={showRegister}
                >
                  Register
                </button>
              </div>
            </>
          )}

          {/* REGISTER */}
          {isRegister && (
            <>
              <div className="card-title">
                Create Account
              </div>

              <div className="card-subtitle">
                Join Recycle2Earn and start earning!
              </div>

              <form onSubmit={handleRegister}>

                <div className="input-group">
                  <i className="fa-solid fa-id-card input-icon"></i>

                  <input
                    className="auth-input"
                    type="text"
                    placeholder="Full Name"
                    value={fullName}
                    onChange={(event) =>
                      setFullName(event.target.value)
                    }
                    autoComplete="name"
                  />
                </div>

                <div className="input-group">
                  <i className="fa-solid fa-user input-icon"></i>

                  <input
                    className="auth-input"
                    type="text"
                    placeholder="Username"
                    value={username}
                    onChange={(event) =>
                      setUsername(event.target.value)
                    }
                    autoComplete="username"
                  />
                </div>

                <div className="input-group">
                  <i className="fa-solid fa-lock input-icon"></i>

                  <input
                    className="auth-input"
                    type={
                      showRegisterPassword
                        ? "text"
                        : "password"
                    }
                    placeholder="Password"
                    value={password}
                    onChange={(event) =>
                      setPassword(event.target.value)
                    }
                    autoComplete="new-password"
                  />

                  <button
                    className="eye-btn"
                    type="button"
                    onClick={() =>
                      togglePassword("register")
                    }
                    aria-label="Toggle password visibility"
                  >
                    <i
                      className={
                        showRegisterPassword
                          ? "fa-solid fa-eye-slash"
                          : "fa-solid fa-eye"
                      }
                    ></i>
                  </button>
                </div>

                <div className="input-group">
                  <i className="fa-solid fa-wallet input-icon"></i>

                  <input
                    className="auth-input"
                    type="text"
                    placeholder="Wallet Address"
                    value={walletAddress}
                    onChange={(event) =>
                      setWalletAddress(event.target.value)
                    }
                    autoComplete="off"
                  />

                  <button
                    className="eye-btn wallet-info-btn"
                    type="button"
                    onClick={() =>
                      alert(
                        "Enter your Ethereum wallet address. MetaMask registration will be available soon."
                      )
                    }
                    aria-label="Wallet information"
                  >
                    <i className="fa-solid fa-circle-info"></i>
                  </button>
                </div>

                {error && (
                  <div className="auth-error">
                    {error}
                  </div>
                )}

                <button
                  className="btn-primary"
                  type="submit"
                  disabled={loading}
                >
                  {loading
                    ? "Creating Account..."
                    : "Register"}
                </button>

              </form>

              <div className="divider">
                <span>or</span>
              </div>

              <button
                className="btn-metamask"
                type="button"
                onClick={handleMetaMaskRegister}
              >
                <img
                  className="wallet-icon-img"
                  src={customWalletSrc}
                  alt="MetaMask Wallet"
                />
                Connect MetaMask
              </button>

              <div className="switch-text">
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={showLogin}
                >
                  Login
                </button>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="footer-section">

          <div className="footer-text">
            Recycle today, earn tokens tomorrow.
          </div>

          <div className="footer-art">

            {/* Recycling bin */}
            <svg
              className="footer-icon-svg"
              viewBox="0 0 50 52"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12 15H38L35 48H15L12 15Z"
                fill="#B9D3B6"
              />
              <path
                d="M9 13H41"
                stroke="#5B8660"
                strokeWidth="3"
                strokeLinecap="round"
              />
              <path
                d="M19 13V8H31V13"
                stroke="#5B8660"
                strokeWidth="3"
                strokeLinecap="round"
              />
              <path
                d="M20 22V40"
                stroke="#7CA47D"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <path
                d="M30 22V40"
                stroke="#7CA47D"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>

            {/* Arrow */}
            <svg
              className="footer-arrow-svg"
              viewBox="0 0 50 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M2 12C15 4 28 4 42 12"
                stroke="#78A27A"
                strokeWidth="2"
                strokeDasharray="4 4"
                strokeLinecap="round"
              />
              <path
                d="M39 7L45 12L39 17"
                stroke="#78A27A"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>

            {/* Coin */}
            <svg
              className="footer-icon-svg"
              viewBox="0 0 50 52"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle
                cx="25"
                cy="26"
                r="19"
                fill="#D6E6B9"
              />
              <circle
                cx="25"
                cy="26"
                r="14"
                stroke="#8EAA68"
                strokeWidth="2"
              />
              <text
                x="25"
                y="32"
                textAnchor="middle"
                fontFamily="Plus Jakarta Sans, sans-serif"
                fontSize="18"
                fontWeight="800"
                fill="#65804D"
              >
                $
              </text>
            </svg>

            {/* Arrow */}
            <svg
              className="footer-arrow-svg"
              viewBox="0 0 50 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M2 12C15 4 28 4 42 12"
                stroke="#78A27A"
                strokeWidth="2"
                strokeDasharray="4 4"
                strokeLinecap="round"
              />
              <path
                d="M39 7L45 12L39 17"
                stroke="#78A27A"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>

            {/* MetaMask */}
            <img
              className="footer-wallet-img"
              src={customWalletSrc}
              alt="MetaMask Wallet"
            />

          </div>
        </div>

        {/* Bottom foliage */}
        <svg
          className="leaf-bg-bottom"
          viewBox="0 0 410 90"
          preserveAspectRatio="none"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M0 70C55 35 95 40 140 65C180 87 215 86 250 67C290 45 335 38 410 64V90H0V70Z"
            fill="#C8DCC5"
            opacity="0.7"
          />

          <path
            d="M0 82C65 52 110 57 155 76C195 93 230 91 270 74C315 54 355 53 410 72V90H0V82Z"
            fill="#B8D2B5"
            opacity="0.65"
          />
        </svg>

      </div>
    </div>
  );
}

export default Auth;

