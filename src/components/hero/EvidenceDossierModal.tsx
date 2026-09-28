import React, { useState } from 'react';
import {
  X,
  UserCheck,
  Check,
} from 'lucide-react';
import type { SafetyReport } from '../../types/safety';
import { SafetyBadge } from '../common/SafetyBadge';

interface EvidenceDossierModalProps {
  report: SafetyReport | null;
  onClose: () => void;
  onUpdateReview?: (reportId: string, status: 'HSE_VERIFIED' | 'OVERRIDDEN', notes: string) => void;
}

export const EvidenceDossierModal: React.FC<EvidenceDossierModalProps> = ({
  report,
  onClose,
  onUpdateReview,
}) => {
  if (!report) return null;

  const [highlightTokens, setHighlightTokens] = useState(true);
  const [reviewNotes, setReviewNotes] = useState(report.hseReview.notes || '');
  const [reviewStatus, setReviewStatus] = useState(report.hseReview.status);
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSaveReview = (status: 'HSE_VERIFIED' | 'OVERRIDDEN') => {
    setReviewStatus(status);
    if (onUpdateReview) {
      onUpdateReview(report.id, status, reviewNotes);
    }
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2500);
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: '1.5rem',
      }}
      onClick={onClose}
    >
      <div
        className="control-panel-elevated"
        style={{
          width: '100%',
          maxWidth: '1040px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          backgroundColor: 'var(--bg-surface)',
          padding: 0,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Dossier Document Header */}
        <div
          style={{
            padding: '1rem 1.5rem',
            backgroundColor: 'var(--bg-canvas)',
            borderBottom: '1px solid var(--border-default)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className="section-tag">// INVESTIGATION DOSSIER</span>
            <span className="oil-mono" style={{ fontSize: '0.925rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {report.id}
            </span>
            <SafetyBadge status={report.sifPotential} size="sm" />
            <SafetyBadge status={reviewStatus} size="sm" />
          </div>

          <button
            onClick={onClose}
            className="oil-btn oil-btn-secondary"
            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
          >
            <X size={14} />
            <span>Close (Esc)</span>
          </button>
        </div>

        {/* Dossier Document Body */}
        <div
          style={{
            padding: '1.5rem',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.25rem',
          }}
        >
          {/* Metadata Row */}
          <div
            className="control-panel-inset"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '1rem',
              padding: '0.75rem 1rem',
            }}
          >
            <div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600 }}>FACILITY / SITE</div>
              <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.15rem' }}>{report.siteName}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600 }}>OPERATIONAL ACTIVITY</div>
              <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.15rem' }}>{report.activity}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600 }}>OBSERVATION TIMESTAMP</div>
              <div className="oil-mono" style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-secondary)', marginTop: '0.15rem' }}>{report.timestamp}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 600 }}>CONFIDENCE METRIC</div>
              <div className="oil-mono" style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--primary-blue)', marginTop: '0.15rem' }}>
                {(report.explainability.confidenceScore * 100).toFixed(0)}% CALIBRATED
              </div>
            </div>
          </div>

          {/* 1. ORIGINAL OBSERVATION */}
          <div className="control-panel" style={{ padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span className="section-tag">// 01. ORIGINAL FIELD OBSERVATION NARRATIVE</span>
              <button
                onClick={() => setHighlightTokens(!highlightTokens)}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '0.6875rem',
                  color: 'var(--primary-blue)',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                {highlightTokens ? 'Toggle Plain View' : 'Highlight Forensic Tokens'}
              </button>
            </div>
            <div
              className="control-panel-inset"
              style={{
                padding: '0.85rem',
                fontSize: '0.8125rem',
                lineHeight: 1.6,
                color: 'var(--text-primary)',
              }}
            >
              "{report.rawNarrative}"
            </div>
          </div>

          {/* 2. DIVERGENCE: REPORTED OUTCOME vs POTENTIAL CONSEQUENCE */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem' }}>
            <div className="control-panel-inset" style={{ padding: '0.85rem' }}>
              <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                // 02A. REPORTED ACTUAL OUTCOME
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                {report.actualOutcome}
              </div>
            </div>

            <div className="control-panel-inset" style={{ padding: '0.85rem', borderLeft: '3px solid var(--sif-critical)' }}>
              <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--sif-critical)', textTransform: 'uppercase' }}>
                // 02B. UNMITIGATED SIF CONSEQUENCE
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', fontWeight: 700, marginTop: '0.2rem' }}>
                {report.explainability.potentialConsequence}
              </div>
            </div>
          </div>

          {/* 3. SAFETY FORENSICS: ENERGY, BARRIER, RULE */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.85rem' }}>
            <div className="control-panel" style={{ padding: '0.85rem' }}>
              <span className="section-tag">// HAZARDOUS ENERGY</span>
              <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                {report.explainability.detectedEnergy}
              </div>
            </div>

            <div className="control-panel" style={{ padding: '0.85rem', borderLeft: '3px solid var(--barrier-amber)' }}>
              <span className="section-tag" style={{ color: 'var(--barrier-amber)' }}>// FAILED BARRIER</span>
              <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--barrier-amber)', marginTop: '0.25rem' }}>
                {report.explainability.failedBarrier}
              </div>
            </div>

            <div className="control-panel" style={{ padding: '0.85rem', borderLeft: '3px solid var(--primary-blue)' }}>
              <span className="section-tag" style={{ color: 'var(--primary-blue)' }}>// IOGP LIFE-SAVING RULE</span>
              <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--primary-blue)', marginTop: '0.25rem' }}>
                {report.lifeSavingRule}
              </div>
            </div>
          </div>

          {/* 4. REASONING EXPLANATION */}
          <div className="control-panel" style={{ padding: '1rem' }}>
            <span className="section-tag">// 04. WHY THIS WAS FLAGGED (FORENSIC REASONING)</span>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginTop: '0.4rem', marginBottom: 0 }}>
              {report.explainability.reasoningNarrative}
            </p>
          </div>

          {/* 5. HSE HUMAN VERIFICATION */}
          <div className="control-panel" style={{ padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <UserCheck size={14} style={{ color: 'var(--verified-emerald)' }} />
                <span style={{ fontSize: '0.775rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  // 05. HSE SUPERINTENDENT VERIFICATION CONSOLE
                </span>
              </div>
              {savedNotice && (
                <span style={{ fontSize: '0.7rem', color: 'var(--verified-emerald)', fontWeight: 600 }}>
                  ✓ Review Saved to SIF Register
                </span>
              )}
            </div>

            <textarea
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Enter validation notes, corrective engineering instructions, or stand-down directives..."
              style={{
                width: '100%',
                minHeight: '55px',
                padding: '0.5rem',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-xs)',
                fontSize: '0.775rem',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-sans)',
                resize: 'vertical',
                marginBottom: '0.5rem',
              }}
            />

            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={() => handleSaveReview('HSE_VERIFIED')}
                className="oil-btn oil-btn-success"
                style={{ fontSize: '0.725rem', padding: '0.3rem 0.75rem' }}
              >
                <Check size={12} />
                <span>Confirm SIF Status</span>
              </button>
              <button
                onClick={() => handleSaveReview('OVERRIDDEN')}
                className="oil-btn oil-btn-secondary"
                style={{ fontSize: '0.725rem', padding: '0.3rem 0.75rem' }}
              >
                <span>Downgrade</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
