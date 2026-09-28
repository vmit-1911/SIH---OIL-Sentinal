import React from 'react';
import { AlertOctagon, CheckCircle2, ShieldAlert, AlertTriangle, XCircle } from 'lucide-react';
import type { SifPotentialStatus, SignalSeverity } from '../../types/safety';

export type BadgeStatus =
  | SifPotentialStatus
  | SignalSeverity
  | 'HSE_VERIFIED'
  | 'PENDING_REVIEW'
  | 'OVERRIDDEN'
  | 'NEEDS_REVIEW'
  | 'BARRIER_FAILED';

interface SafetyBadgeProps {
  status: BadgeStatus;
  customLabel?: string;
  size?: 'sm' | 'md';
}

export const SafetyBadge: React.FC<SafetyBadgeProps> = ({
  status,
  customLabel,
  size = 'md',
}) => {
  const isSm = size === 'sm';

  switch (status) {
    case 'SIF_POTENTIAL':
    case 'CRITICAL_SIGNAL':
      return (
        <span
          className="badge-sif"
          style={{
            fontSize: isSm ? '0.675rem' : '0.725rem',
            padding: isSm ? '0.15rem 0.45rem' : '0.2rem 0.55rem',
          }}
          title="Flagged as having Serious Injury & Fatality Potential"
        >
          <AlertOctagon size={isSm ? 12 : 13} style={{ color: 'var(--sif-critical)' }} />
          <span>{customLabel || 'SIF Potential'}</span>
        </span>
      );

    case 'NON_SIF_POTENTIAL':
    case 'NORMAL':
      return (
        <span
          className="badge-non-sif"
          style={{
            fontSize: isSm ? '0.675rem' : '0.725rem',
            padding: isSm ? '0.15rem 0.45rem' : '0.2rem 0.55rem',
          }}
        >
          <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: 'var(--text-muted)' }} />
          <span>{customLabel || 'Non-SIF'}</span>
        </span>
      );

    case 'ELEVATED':
    case 'ATTENTION':
    case 'BARRIER_FAILED':
      return (
        <span
          className="badge-barrier"
          style={{
            fontSize: isSm ? '0.675rem' : '0.725rem',
            padding: isSm ? '0.15rem 0.45rem' : '0.2rem 0.55rem',
          }}
        >
          <AlertTriangle size={isSm ? 12 : 13} style={{ color: 'var(--barrier-amber)' }} />
          <span>{customLabel || 'Barrier Degradation'}</span>
        </span>
      );

    case 'HSE_VERIFIED':
      return (
        <span
          className="badge-verified"
          style={{
            fontSize: isSm ? '0.675rem' : '0.725rem',
            padding: isSm ? '0.15rem 0.45rem' : '0.2rem 0.55rem',
          }}
        >
          <CheckCircle2 size={isSm ? 12 : 13} style={{ color: 'var(--verified-emerald)' }} />
          <span>{customLabel || 'HSE Verified'}</span>
        </span>
      );

    case 'OVERRIDDEN':
      return (
        <span
          className="badge-non-sif"
          style={{
            fontSize: isSm ? '0.675rem' : '0.725rem',
            padding: isSm ? '0.15rem 0.45rem' : '0.2rem 0.55rem',
          }}
        >
          <XCircle size={isSm ? 12 : 13} style={{ color: 'var(--sif-critical)' }} />
          <span>{customLabel || 'Overridden'}</span>
        </span>
      );

    case 'PENDING_REVIEW':
    case 'NEEDS_REVIEW':
      return (
        <span
          className="badge-blue"
          style={{
            fontSize: isSm ? '0.675rem' : '0.725rem',
            padding: isSm ? '0.15rem 0.45rem' : '0.2rem 0.55rem',
          }}
        >
          <ShieldAlert size={isSm ? 12 : 13} style={{ color: 'var(--primary-blue)' }} />
          <span>{customLabel || (status === 'NEEDS_REVIEW' ? 'Needs HSE Audit' : 'AI Assessed (Pending Review)')}</span>
        </span>
      );

    default:
      return null;
  }
};
