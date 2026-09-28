import React, { useState, useEffect } from 'react';
import {
  Building2,
  Clock,
  Radio,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { safetyService } from '../../services/safetyService';

interface TopUtilityBarProps {
  onPrecursorClick?: () => void;
  activePrecursorTitle?: string;
}

export const TopUtilityBar: React.FC<TopUtilityBarProps> = ({
  onPrecursorClick,
  activePrecursorTitle = 'High-Pressure Energy Isolation & Zero-Verification Bypass',
}) => {
  const [isBackendLive, setIsBackendLive] = useState<boolean>(true);

  const handleRefreshHealth = async () => {
    try {
      const health = await safetyService.checkBackendHealth();
      setIsBackendLive(health.isOnline);
    } catch {
      setIsBackendLive(false);
    }
  };

  useEffect(() => {
    handleRefreshHealth();
    const interval = setInterval(handleRefreshHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header
      style={{
        height: '42px',
        backgroundColor: '#090d16',
        color: '#ffffff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.5rem',
        borderBottom: '1px solid #1e293b',
        zIndex: 30,
        fontSize: '0.725rem',
      }}
    >
      {/* Left: Organization Identifier & Operational Telemetry */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div
            style={{
              backgroundColor: 'var(--primary-blue)',
              color: '#ffffff',
              fontWeight: 800,
              fontSize: '0.7rem',
              padding: '0.15rem 0.45rem',
              borderRadius: 'var(--radius-xs)',
              letterSpacing: '0.06em',
            }}
          >
            OIL
          </div>
          <span style={{ fontWeight: 700, letterSpacing: '0.04em', color: '#f8fafc' }}>
            OIL INDIA LIMITED
          </span>
          <span style={{ color: '#475569' }}>//</span>
          <span style={{ color: '#94a3b8', fontWeight: 500, letterSpacing: '0.03em' }}>
            SIF PRECURSOR INTELLIGENCE CONTROL ROOM
          </span>
        </div>

        <div style={{ width: '1px', height: '14px', backgroundColor: '#334155' }} />

        {/* Operational Basin Scope */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#cbd5e1' }}>
          <Building2 size={12} color="#38bdf8" />
          <span style={{ fontWeight: 600 }}>ASSAM OPERATIONAL BASIN</span>
          <span style={{ color: '#64748b', fontSize: '0.675rem' }}>(Duliajan • Moran • Digboi • Naharkatiya)</span>
        </div>
      </div>

      {/* Center: Live Signal Alert Broadcast Pill */}
      {onPrecursorClick && (
        <button
          onClick={onPrecursorClick}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            backgroundColor: 'rgba(220, 38, 38, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#fca5a5',
            padding: '0.2rem 0.65rem',
            borderRadius: 'var(--radius-xs)',
            cursor: 'pointer',
            fontSize: '0.7rem',
            transition: 'all 0.15s ease',
          }}
          title="Click to inspect active critical precursor in Precursor Intelligence"
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(220, 38, 38, 0.25)';
            e.currentTarget.style.borderColor = '#ef4444';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(220, 38, 38, 0.15)';
            e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.4)';
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#ef4444', display: 'inline-block', boxShadow: '0 0 6px #ef4444' }} />
          <span style={{ fontWeight: 700, color: '#fee2e2' }}>ACTIVE SIF SIGNAL:</span>
          <span style={{ maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {activePrecursorTitle}
          </span>
          <ArrowRight size={11} color="#fca5a5" />
        </button>
      )}

      {/* Right: Technical Metadata & Mode */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#94a3b8' }}>
          <Clock size={11} />
          <span className="oil-mono" style={{ fontSize: '0.675rem' }}>24 SEP 2026 // 12:00 IST</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#4ade80' }}>
          <Radio size={11} />
          <span style={{ fontWeight: 700, fontSize: '0.675rem', letterSpacing: '0.03em' }}>MONITORING ACTIVE</span>
        </div>

        {/* Live Backend Link Telemetry */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            backgroundColor: isBackendLive ? 'rgba(34, 197, 94, 0.12)' : 'rgba(234, 179, 8, 0.12)',
            border: `1px solid ${isBackendLive ? 'rgba(34, 197, 94, 0.35)' : 'rgba(234, 179, 8, 0.35)'}`,
            padding: '0.15rem 0.5rem',
            borderRadius: 'var(--radius-xs)',
            color: isBackendLive ? '#86efac' : '#fde047',
            fontSize: '0.65rem',
            fontWeight: 700,
            cursor: 'pointer',
          }}
          onClick={handleRefreshHealth}
          title={isBackendLive ? 'FastAPI Backend Online at localhost:8000 (Click to re-probe)' : 'FastAPI Backend unreachable, operating in resilient local mode (Click to re-probe)'}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: isBackendLive ? '#22c55e' : '#eab308',
              boxShadow: isBackendLive ? '0 0 6px #22c55e' : '0 0 6px #eab308',
            }}
          />
          <span>{isBackendLive ? 'BACKEND: FASTAPI LIVE (PORT 8000)' : 'BACKEND: OFFLINE MODE'}</span>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
            backgroundColor: '#1e293b',
            padding: '0.15rem 0.45rem',
            borderRadius: 'var(--radius-xs)',
            color: '#cbd5e1',
            fontSize: '0.65rem',
            fontWeight: 600,
          }}
        >
          <ShieldCheck size={11} color="#38bdf8" />
          <span>OIL SIF SENTINEL</span>
        </div>
      </div>
    </header>
  );
};
