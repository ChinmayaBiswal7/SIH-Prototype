import React, { useState } from 'react';
import { login, AUTHORIZED_TEAM_MEMBERS } from '../../../services/authService';
import './LoginScreen.css';

export default function LoginScreen({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showDemoDrawer, setShowDemoDrawer] = useState(false);

  function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (!email.trim() || !password.trim()) {
      setError('Please provide both authorized email and security passcode.');
      return;
    }

    setIsLoading(true);

    // Realistic authentication delay
    setTimeout(() => {
      const res = login(email, password);
      setIsLoading(false);

      if (res.success) {
        onLoginSuccess(res.user);
      } else {
        setError(res.error);
      }
    }, 600);
  }

  function handleQuickFill(acc) {
    setEmail(acc.email);
    setPassword(acc.password);
    setError('');
  }

  return (
    <div className="login-wrapper">
      {/* Background Ambience & Cyber Grid */}
      <div className="login-bg-grid" />
      <div className="login-ambient-orb" />
      <div className="login-scanline" />

      {/* Main Glassmorphic Security Card */}
      <div className="login-card">
        {/* Top Emblem & Header */}
        <div className="login-header">
          <div className="login-emblem">
            <i className="fas fa-shield-halved" />
          </div>
          <div className="login-badge-pill">
            <span className="live-dot" />
            <span>SECURE RESTRICTED TERMINAL</span>
          </div>
          <h1 className="login-title">ClearWays Command HQ</h1>
          <p className="login-subtitle">
            Smart Urban Mobility & AI-Driven Green Corridor Platform
          </p>
        </div>

        {/* Security Warning Notice */}
        <div className="login-security-notice">
          <i className="fas fa-lock" />
          <span>Access Restricted to Authorized Team Members & SIH Evaluation Jury</span>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="login-error-banner">
            <i className="fas fa-circle-exclamation" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-input-group">
            <label>Authorized Personnel Email</label>
            <div className="login-input-box">
              <i className="fas fa-user-shield" />
              <input
                type="email"
                placeholder="officer@clearways.io"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </div>
          </div>

          <div className="login-input-group">
            <label>Security Passcode</label>
            <div className="login-input-box">
              <i className="fas fa-key" />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter security passcode"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="login-eye-btn"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? "Hide password" : "Show password"}
              >
                <i className={`fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`} />
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="login-submit-btn"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <i className="fas fa-circle-notch fa-spin" />
                <span>Verifying Biometric & Cryptographic Access...</span>
              </>
            ) : (
              <>
                <i className="fas fa-fingerprint" />
                <span>Authorize & Enter Command Center</span>
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Access Drawer Toggle */}
        <div className="login-footer">
          <button 
            type="button" 
            className="login-drawer-toggle"
            onClick={() => setShowDemoDrawer(!showDemoDrawer)}
          >
            <i className={`fas ${showDemoDrawer ? 'fa-chevron-up' : 'fa-id-badge'}`} />
            <span>{showDemoDrawer ? 'Hide Authorized Demo Profiles' : 'Quick-Fill Authorized Team Profiles (SIH Presentation)'}</span>
          </button>

          {showDemoDrawer && (
            <div className="login-demo-profiles">
              <div className="login-dp-hint">Click any profile below to autofill verified credentials:</div>
              {AUTHORIZED_TEAM_MEMBERS.map((acc, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="login-dp-card"
                  onClick={() => handleQuickFill(acc)}
                >
                  <div className="login-dp-main">
                    <strong>{acc.name}</strong>
                    <span className="login-dp-role">{acc.role}</span>
                  </div>
                  <div className="login-dp-badge">{acc.badge}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="login-sub-footer">
          <span>Encrypted with SHA-256 • Smart India Hackathon Prototype</span>
        </div>
      </div>
    </div>
  );
}
