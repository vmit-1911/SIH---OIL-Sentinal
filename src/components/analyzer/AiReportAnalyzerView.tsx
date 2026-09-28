import React, { useState, useEffect } from 'react';
import {
  RotateCcw,
  FileText,
  UserCheck,
  Check,
  Cpu,
  CornerDownRight,
  ArrowRight,
} from 'lucide-react';
import type { AnalysisResult, DemoObservationFixture } from '../../types/safety';
import { SafetyBadge } from '../common/SafetyBadge';
import { safetyService } from '../../services/safetyService';

interface AiReportAnalyzerViewProps {
  onNavigateToPrecursor: (clusterId: string) => void;
}

export const AiReportAnalyzerView: React.FC<AiReportAnalyzerViewProps> = ({
  onNavigateToPrecursor,
}) => {
  // Input state
  const [narrative, setNarrative] = useState('');
  const [reportType, setReportType] = useState<'Unsafe Act' | 'Unsafe Condition' | 'Near Miss' | 'Incident'>('Unsafe Act');
  const [siteName, setSiteName] = useState('Duliajan Deep Drill Rig #14');
  const [activity, setActivity] = useState('');

  // Analysis workflow states
  const [analysisState, setAnalysisState] = useState<'EMPTY' | 'ANALYZING' | 'RESULT'>('EMPTY');
  const [analysisStepIndex, setAnalysisStepIndex] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [highlightedEvidenceId, setHighlightedEvidenceId] = useState<string | null>(null);

  // HSE human-in-the-loop review state
  const [reviewStatus, setReviewStatus] = useState<'PENDING_REVIEW' | 'HSE_VERIFIED' | 'OVERRIDDEN' | 'NEEDS_REVIEW'>('PENDING_REVIEW');
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewSavedMessage, setReviewSavedMessage] = useState(false);

  // Demo fixtures loaded from service
  const [demoFixtures, setDemoFixtures] = useState<DemoObservationFixture[]>([]);

  useEffect(() => {
    safetyService.getDemoFixtures().then(setDemoFixtures);
  }, []);

  const processingSteps = [
    'Parsing Unstructured Field Narrative',
    'Identifying Stored Energy & Chemical Vectors',
    'Evaluating Physical Safeguard Integrity',
    'Correlating with IOGP Life-Saving Rules',
    'Formulating Explainable Evidence Chain',
  ];

  const handleSelectDemo = (demo: DemoObservationFixture) => {
    setNarrative(demo.narrative);
    setReportType(demo.reportType);
    setSiteName(demo.siteName);
    setActivity(demo.activity);
    setAnalysisState('EMPTY');
    setResult(null);
    setHighlightedEvidenceId(null);
    setReviewStatus('PENDING_REVIEW');
    setReviewNotes('');
  };

  const handleAnalyze = async () => {
    if (!narrative.trim()) return;

    setAnalysisState('ANALYZING');
    setAnalysisStepIndex(0);

    const interval = setInterval(() => {
      setAnalysisStepIndex((prev) => {
        if (prev < processingSteps.length - 1) {
          return prev + 1;
        }
        clearInterval(interval);
        return prev;
      });
    }, 220);

    try {
      const res = await safetyService.analyzeReport(narrative, reportType, siteName, activity);
      setTimeout(() => {
        clearInterval(interval);
        setResult(res);
        setReviewStatus(res.reviewStatus);
        setAnalysisState('RESULT');
      }, 1100);
    } catch (err) {
      clearInterval(interval);
      console.error('Failed to analyze report:', err);
      setAnalysisState('EMPTY');
    }
  };

  const handleReset = () => {
    setNarrative('');
    setActivity('');
    setAnalysisState('EMPTY');
    setResult(null);
    setHighlightedEvidenceId(null);
    setReviewStatus('PENDING_REVIEW');
    setReviewNotes('');
  };

  const handleUpdateReview = (newStatus: 'HSE_VERIFIED' | 'OVERRIDDEN' | 'NEEDS_REVIEW') => {
    setReviewStatus(newStatus);
    setReviewSavedMessage(true);
    setTimeout(() => setReviewSavedMessage(false), 2500);
  };

  const renderHighlightedNarrative = () => {
    if (!result || !result.evidenceItems.length) {
      return narrative;
    }

    const activeEvidence = result.evidenceItems.find((ev) => ev.id === highlightedEvidenceId);

    if (!activeEvidence) {
      return (
        <span style={{ color: 'var(--text-secondary)', lineHeight: 1.65 }}>
          {narrative}
        </span>
      );
    }

    const phrase = activeEvidence.originalPhrase;
    const parts = narrative.split(phrase);

    if (parts.length < 2) {
      return (
        <span style={{ color: 'var(--text-secondary)', lineHeight: 1.65 }}>
          {narrative}
        </span>
      );
    }

    return (
      <span style={{ color: 'var(--text-secondary)', lineHeight: 1.65 }}>
        {parts[0]}
        <mark
          style={{
            backgroundColor: 'rgba(217, 119, 6, 0.18)',
            color: '#b45309',
            padding: '0.15rem 0.35rem',
            borderRadius: '2px',
            fontWeight: 700,
            borderBottom: '2px solid var(--barrier-amber)',
          }}
        >
          {phrase}
        </mark>
        {parts.slice(1).join(phrase)}
      </span>
    );
  };

  return (
    <div
      style={{
        padding: '1.25rem 1.75rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
        maxWidth: '1560px',
        margin: '0 auto',
        width: '100%',
      }}
    >
      {/* 1. TOP HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="oil-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            // 03 AI REPORT ANALYZER
          </span>
          <span style={{ color: 'var(--border-subtle)' }}>/</span>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            EVIDENCE INVESTIGATION WORKSPACE
          </span>
        </div>

        <button
          onClick={handleReset}
          className="oil-btn oil-btn-secondary"
          style={{ fontSize: '0.75rem', padding: '0.4rem 0.85rem' }}
        >
          <RotateCcw size={13} />
          <span>Reset Investigation</span>
        </button>
      </div>

      {/* 2. SPLIT INVESTIGATION PANELS: LEFT (ORIGINAL) vs RIGHT (AI INTERPRETATION) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1.35fr', gap: '1.25rem', alignItems: 'start' }}>
        {/* ================= LEFT PANEL: ORIGINAL SAFETY REPORT SOURCE ================= */}
        <div className="control-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={15} style={{ color: 'var(--primary-blue)' }} />
              <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                ORIGINAL FIELD OBSERVATION (PRIMARY SOURCE)
              </span>
            </div>
            <span className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
              {narrative.length} CHARACTERS
            </span>
          </div>

          {/* Form Context Strip */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                Classification
              </label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value as any)}
                style={{
                  width: '100%',
                  padding: '0.4rem 0.6rem',
                  backgroundColor: 'var(--bg-canvas)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-xs)',
                  fontSize: '0.775rem',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-sans)',
                }}
              >
                <option value="Unsafe Act">Unsafe Act (UA)</option>
                <option value="Unsafe Condition">Unsafe Condition (UC)</option>
                <option value="Near Miss">Near Miss</option>
                <option value="Incident">Minor Incident</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                Operating Facility
              </label>
              <select
                value={siteName}
                onChange={(e) => setSiteName(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.4rem 0.6rem',
                  backgroundColor: 'var(--bg-canvas)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-xs)',
                  fontSize: '0.775rem',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-sans)',
                }}
              >
                <option value="Duliajan Deep Drill Rig #14">Duliajan Deep Drill Rig #14</option>
                <option value="Moran Workover Rig #07">Moran Workover Rig #07</option>
                <option value="Digboi Oil Collection Station (OCS-2)">Digboi Oil Collection Station (OCS-2)</option>
                <option value="Naharkatiya Wellhead #11">Naharkatiya Wellhead #11</option>
                <option value="Gas Compression Station #03">Gas Compression Station #03</option>
              </select>
            </div>
          </div>

          {/* Narrative Editor / Highlight Viewer */}
          <div>
            <label style={{ display: 'block', fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              Free-Text Narrative
            </label>

            {analysisState === 'RESULT' ? (
              <div
                className="control-panel-inset"
                style={{
                  minHeight: '140px',
                  padding: '0.85rem',
                  fontSize: '0.8125rem',
                  lineHeight: 1.65,
                }}
              >
                {renderHighlightedNarrative()}
                <div
                  style={{
                    marginTop: '0.75rem',
                    paddingTop: '0.5rem',
                    borderTop: '1px solid var(--border-subtle)',
                    fontSize: '0.7rem',
                    color: 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  <CornerDownRight size={13} style={{ color: 'var(--primary-blue)' }} />
                  <span>Interactive highlight active: click any factor on the right to pinpoint source text.</span>
                </div>
              </div>
            ) : (
              <textarea
                value={narrative}
                onChange={(e) => setNarrative(e.target.value)}
                placeholder="Paste or type raw safety observation narrative (e.g. while floorhand was loosening high-pressure manifold flange, no bleed off check performed...)"
                style={{
                  width: '100%',
                  minHeight: '140px',
                  padding: '0.85rem',
                  backgroundColor: 'var(--bg-canvas)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-xs)',
                  fontSize: '0.8125rem',
                  lineHeight: 1.55,
                  color: 'var(--text-primary)',
                  resize: 'vertical',
                  fontFamily: 'var(--font-sans)',
                }}
              />
            )}
          </div>

          {/* Action Row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <button
              onClick={handleReset}
              className="oil-btn oil-btn-secondary"
              style={{ fontSize: '0.75rem' }}
              disabled={analysisState === 'ANALYZING' || (!narrative && analysisState === 'EMPTY')}
            >
              Clear Text
            </button>

            <button
              onClick={handleAnalyze}
              className="oil-btn oil-btn-primary"
              style={{
                padding: '0.55rem 1.25rem',
                fontSize: '0.8125rem',
                fontWeight: 600,
                gap: '0.5rem',
              }}
              disabled={!narrative.trim() || analysisState === 'ANALYZING'}
            >
              <Cpu size={14} />
              <span>{analysisState === 'ANALYZING' ? 'Executing NLP Extraction...' : 'Execute AI Analysis'}</span>
            </button>
          </div>

          {/* Synthetic Demo Fixture Bar */}
          <div style={{ paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
              OR SELECT DEMO OBSERVATION FIXTURE:
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
              {demoFixtures.map((demo) => {
                const isEnergy = demo.id.includes('ENERGY');
                const isConfined = demo.id.includes('CONFINED');

                return (
                  <button
                    key={demo.id}
                    onClick={() => handleSelectDemo(demo)}
                    className="control-panel"
                    style={{
                      padding: '0.5rem 0.75rem',
                      cursor: 'pointer',
                      textAlign: 'left',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      transition: 'border-color 0.15s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--primary-blue)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border-subtle)';
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {demo.title}
                      </div>
                      <div className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                        {demo.siteName} • {demo.activity}
                      </div>
                    </div>
                    <span
                      className={isEnergy || isConfined ? 'signal-tag-critical' : 'signal-tag-info'}
                      style={{ fontSize: '0.625rem' }}
                    >
                      {isEnergy || isConfined ? 'SIF POTENTIAL' : 'ROUTINE'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* ================= RIGHT PANEL: AI INTERPRETATION & EXPLAINABILITY ================= */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {analysisState === 'EMPTY' && (
            <div
              className="control-panel-inset"
              style={{
                padding: '3rem 2rem',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.75rem',
              }}
            >
              <Cpu size={28} style={{ color: 'var(--text-muted)' }} />
              <div style={{ fontSize: '0.925rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Awaiting Safety Observation Input
              </div>
              <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)', maxWidth: '420px', lineHeight: 1.5 }}>
                Enter a raw observation narrative on the left or select a synthetic OIL fixture, then execute AI analysis to extract hazardous energy, failed safeguards, and IOGP Life-Saving Rule correlations.
              </div>
            </div>
          )}

          {analysisState === 'ANALYZING' && (
            <div className="control-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: 14, height: 14, border: '2px solid var(--border-default)', borderTopColor: 'var(--primary-blue)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Extracting Safety Forensics & Causal Evidence...
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {processingSteps.map((step, idx) => {
                  const isDone = idx < analysisStepIndex;
                  const isCurrent = idx === analysisStepIndex;

                  return (
                    <div
                      key={step}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.65rem',
                        fontSize: '0.775rem',
                        color: isDone ? 'var(--verified-emerald)' : isCurrent ? 'var(--primary-blue)' : 'var(--text-muted)',
                        fontWeight: isCurrent || isDone ? 600 : 400,
                      }}
                    >
                      <span
                        className="oil-mono"
                        style={{
                          width: '18px',
                          height: '18px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          borderRadius: '2px',
                          backgroundColor: isDone ? 'var(--verified-emerald-bg)' : isCurrent ? 'var(--primary-blue-subtle)' : 'var(--bg-canvas)',
                          fontSize: '0.65rem',
                        }}
                      >
                        {isDone ? '✓' : idx + 1}
                      </span>
                      <span>{step}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {analysisState === 'RESULT' && result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* SIF Assessment Anchor */}
              <div
                className="control-panel-elevated"
                style={{
                  borderLeft: result.sifPotential === 'SIF_POTENTIAL' ? '4px solid var(--sif-critical)' : '4px solid var(--border-default)',
                  padding: '1.25rem 1.5rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '1rem',
                }}
              >
                <div>
                  <div className="section-tag" style={{ marginBottom: '0.25rem' }}>
                    AI SAFETY ASSESSMENT
                  </div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.65rem' }}>
                    <span
                      className={`display-anchor ${result.sifPotential === 'SIF_POTENTIAL' ? 'display-anchor-sif' : ''}`}
                      style={{ fontSize: '1.5rem' }}
                    >
                      {result.sifPotential === 'SIF_POTENTIAL' ? 'CRITICAL SIF POTENTIAL' : 'ROUTINE OBSERVATION'}
                    </span>
                    <SafetyBadge status={result.sifPotential} size="sm" />
                  </div>
                  <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    {result.sifPotential === 'SIF_POTENTIAL'
                      ? 'High-energy vector observed with compromised or missing barrier.'
                      : 'Operational deviation with zero fatal trajectory.'}
                  </div>
                </div>

                <div className="control-panel-inset" style={{ padding: '0.5rem 0.85rem', textAlign: 'right' }}>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                    Calibrated Confidence
                  </div>
                  <div className="oil-mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {(result.classificationConfidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Cognitive Contrast: Outcome vs Potential */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '0.75rem',
                }}
              >
                <div className="control-panel-inset" style={{ padding: '0.85rem' }}>
                  <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    REPORTED ACTUAL OUTCOME
                  </div>
                  <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                    {result.actualOutcome}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                    Actual recorded field consequence
                  </div>
                </div>

                <div className="control-panel-inset" style={{ padding: '0.85rem', borderLeft: '2px solid var(--sif-critical)' }}>
                  <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--sif-critical)', textTransform: 'uppercase' }}>
                    POTENTIAL FATAL TRAJECTORY
                  </div>
                  <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                    {result.potentialConsequence}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--sif-critical)', marginTop: '0.15rem' }}>
                    Unmitigated energy release risk
                  </div>
                </div>
              </div>

              {/* HERO EXPLAINABILITY: WHY WAS THIS FLAGGED? */}
              <div className="control-panel" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <div>
                    <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      WHY WAS THIS FLAGGED? // EXTRACTED FORENSIC FACTORS
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      Click any evidence factor to highlight its exact source phrase in the narrative:
                    </div>
                  </div>
                  {highlightedEvidenceId && (
                    <button
                      onClick={() => setHighlightedEvidenceId(null)}
                      className="oil-btn oil-btn-secondary"
                      style={{ fontSize: '0.6875rem', padding: '0.15rem 0.45rem' }}
                    >
                      Clear Pin
                    </button>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {result.evidenceItems.map((item, idx) => {
                    const isSelected = highlightedEvidenceId === item.id;

                    return (
                      <div
                        key={item.id}
                        onClick={() => setHighlightedEvidenceId(isSelected ? null : item.id)}
                        className="control-panel"
                        style={{
                          padding: '0.6rem 0.85rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '0.65rem',
                          borderColor: isSelected ? 'var(--primary-blue)' : 'var(--border-subtle)',
                          backgroundColor: isSelected ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        <span className="oil-mono" style={{ fontSize: '0.6875rem', fontWeight: 700, color: isSelected ? 'var(--primary-blue)' : 'var(--text-muted)', marginTop: '2px' }}>
                          0{idx + 1}
                        </span>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '0.775rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                            "{item.originalPhrase}"
                          </div>
                          <div style={{ fontSize: '0.725rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                            → {item.deduction}
                          </div>
                        </div>
                        <span className="oil-mono" style={{ fontSize: '0.625rem', color: isSelected ? 'var(--primary-blue)' : 'var(--text-muted)', fontWeight: 600 }}>
                          {isSelected ? 'PINNED' : 'PIN PHRASE'}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Synthesis Logic Readout */}
                <div
                  className="control-panel-inset"
                  style={{
                    marginTop: '0.75rem',
                    padding: '0.65rem 0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '0.35rem',
                    fontSize: '0.75rem',
                  }}
                >
                  <span style={{ fontSize: '0.6875rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    SYNTHESIS:
                  </span>
                  {result.synthesisEquation.factors.map((factor, i) => (
                    <React.Fragment key={factor}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)', backgroundColor: 'var(--bg-surface)', padding: '0.1rem 0.4rem', border: '1px solid var(--border-subtle)' }}>
                        {factor}
                      </span>
                      {i < result.synthesisEquation.factors.length - 1 && (
                        <span style={{ color: 'var(--text-muted)', fontWeight: 700 }}>+</span>
                      )}
                    </React.Fragment>
                  ))}
                  <span style={{ color: 'var(--text-muted)', fontWeight: 700 }}>=</span>
                  <span style={{ fontWeight: 800, color: result.sifPotential === 'SIF_POTENTIAL' ? 'var(--sif-critical)' : 'var(--text-primary)' }}>
                    {result.synthesisEquation.result}
                  </span>
                </div>
              </div>

              {/* HSE HUMAN-IN-THE-LOOP REVIEW */}
              <div className="control-panel" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <UserCheck size={15} style={{ color: 'var(--verified-emerald)' }} />
                    <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      HSE SUPERINTENDENT VERIFICATION CONSOLE
                    </span>
                  </div>
                  <SafetyBadge status={reviewStatus} size="sm" />
                </div>

                <textarea
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Enter superintendent validation notes or corrective action directives..."
                  style={{
                    width: '100%',
                    minHeight: '55px',
                    padding: '0.5rem',
                    backgroundColor: 'var(--bg-canvas)',
                    border: '1px solid var(--border-default)',
                    borderRadius: 'var(--radius-xs)',
                    fontSize: '0.75rem',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-sans)',
                    resize: 'vertical',
                    marginBottom: '0.5rem',
                  }}
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', gap: '0.4rem' }}>
                    <button
                      onClick={() => handleUpdateReview('HSE_VERIFIED')}
                      className="oil-btn oil-btn-success"
                      style={{ fontSize: '0.725rem', padding: '0.3rem 0.75rem' }}
                    >
                      <Check size={12} />
                      <span>Verify SIF Precursor</span>
                    </button>
                    <button
                      onClick={() => handleUpdateReview('OVERRIDDEN')}
                      className="oil-btn oil-btn-secondary"
                      style={{ fontSize: '0.725rem', padding: '0.3rem 0.75rem' }}
                    >
                      <span>Mark False Positive</span>
                    </button>
                  </div>

                  {reviewSavedMessage && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--verified-emerald)', fontWeight: 600 }}>
                      ✓ Review recorded in OIL SIF register
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 3. FULL-WIDTH LOWER SECTION: VISUAL EVIDENCE CHAIN & PRECURSOR LINK */}
      {analysisState === 'RESULT' && result && (
        <div className="control-panel" style={{ padding: '1.25rem' }}>
          <div className="section-tag" style={{ marginBottom: '0.75rem' }}>
            // FULL CAUSAL EVIDENCE CHAIN
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(6, 1fr)',
              gap: '0.75rem',
              marginBottom: '1rem',
            }}
          >
            <div className="control-panel-inset" style={{ padding: '0.75rem' }}>
              <div style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 600 }}>01. REPORT</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>{reportType}</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>{siteName}</div>
            </div>

            <div className="control-panel-inset" style={{ padding: '0.75rem' }}>
              <div style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 600 }}>02. HAZARD VECTOR</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>{result.extractedEnergy}</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Energy Vector</div>
            </div>

            <div className="control-panel-inset" style={{ padding: '0.75rem', borderLeft: '2px solid var(--barrier-amber)' }}>
              <div style={{ fontSize: '0.625rem', color: 'var(--barrier-amber)', fontWeight: 600 }}>03. FAILED BARRIER</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--barrier-amber)', marginTop: '0.2rem' }}>{result.failedBarrier}</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Safeguard Failure</div>
            </div>

            <div className="control-panel-inset" style={{ padding: '0.75rem', borderLeft: '2px solid var(--sif-critical)' }}>
              <div style={{ fontSize: '0.625rem', color: 'var(--sif-critical)', fontWeight: 600 }}>04. SIF POTENTIAL</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--sif-critical)', marginTop: '0.2rem' }}>{result.sifPotential}</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Fatal Potential</div>
            </div>

            <div className="control-panel-inset" style={{ padding: '0.75rem' }}>
              <div style={{ fontSize: '0.625rem', color: 'var(--primary-blue)', fontWeight: 600 }}>05. IOGP RULE</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary-blue)', marginTop: '0.2rem' }}>{result.lifeSavingRule}</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Standard Rule</div>
            </div>

            <div className="control-panel-inset" style={{ padding: '0.75rem' }}>
              <div style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 600 }}>06. CONSEQUENCE</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>{result.potentialConsequence}</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>High Severity</div>
            </div>
          </div>

          {/* Jump to Connected Precursor */}
          <div
            style={{
              padding: '0.85rem 1rem',
              backgroundColor: 'var(--bg-canvas)',
              border: '1px solid var(--border-default)',
              borderLeft: '4px solid var(--sif-critical)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.75rem',
            }}
          >
            <div>
              <div style={{ fontSize: '0.6875rem', fontWeight: 700, color: 'var(--sif-critical)', textTransform: 'uppercase' }}>
                CORRELATED PRECURSOR PATTERN IDENTIFIED
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {result.relatedPrecursor.title}
              </div>
              <div style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>
                {result.relatedPrecursor.observationCount} related reports across {result.relatedPrecursor.assetCount} assets share this failure pattern.
              </div>
            </div>

            <button
              onClick={() => onNavigateToPrecursor(result.relatedPrecursor.id)}
              className="oil-btn oil-btn-primary"
              style={{ fontSize: '0.775rem', padding: '0.5rem 1rem', gap: '0.4rem' }}
            >
              <span>Inspect Precursor Topology</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
