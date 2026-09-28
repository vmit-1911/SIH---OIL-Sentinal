import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  X,
  ChevronRight,
  ExternalLink,
  UserCheck,
  RotateCcw,
  Check,
} from 'lucide-react';
import type {
  SafetyReport,
  LifeSavingRule,
  SifPotentialStatus,
} from '../../types/safety';
import { safetyService } from '../../services/safetyService';
import { SafetyBadge } from '../common/SafetyBadge';

interface ReportExplorerViewProps {
  onNavigateToPrecursor?: (precursorId: string) => void;
  onNavigateToSite?: (siteId: string) => void;
  onNavigateToLsr?: (ruleId: LifeSavingRule) => void;
  onNavigateToAnalyzer?: (report?: SafetyReport) => void;
  initialReportId?: string;
}

type SortOption = 'newest' | 'oldest' | 'sif_first' | 'verified_first';
type SemanticHighlightFilter = 'all' | 'energy' | 'barrier' | 'action' | 'hazard' | 'consequence';

export const ReportExplorerView: React.FC<ReportExplorerViewProps> = ({
  onNavigateToPrecursor,
  onNavigateToSite: _onNavigateToSite,
  onNavigateToLsr: _onNavigateToLsr,
  onNavigateToAnalyzer,
  initialReportId,
}) => {
  const [reports, setReports] = useState<SafetyReport[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(initialReportId || null);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedReportType, setSelectedReportType] = useState<string>('ALL');
  const [selectedSifStatus, setSelectedSifStatus] = useState<string>('ALL');
  const [selectedLsr, setSelectedLsr] = useState<string>('ALL');
  const [selectedPrecursor, setSelectedPrecursor] = useState<string>('ALL');
  const [selectedSite, setSelectedSite] = useState<string>('ALL');
  const [selectedHseStatus, setSelectedHseStatus] = useState<string>('ALL');
  const [sortOption, setSortOption] = useState<SortOption>('newest');

  // Dossier state
  const [activeHighlightCategory, setActiveHighlightCategory] = useState<SemanticHighlightFilter>('all');
  const [selectedTokenIndex, setSelectedTokenIndex] = useState<number | null>(null);
  const [relatedReports, setRelatedReports] = useState<{ report: SafetyReport; connectionReason: string }[]>([]);
  const [reviewNoteInput, setReviewNoteInput] = useState<string>('');
  const [reviewSavedAlert, setReviewSavedAlert] = useState<boolean>(false);

  useEffect(() => {
    safetyService.getAllReports().then((data) => {
      setReports(data);
      if (data.length > 0) {
        if (initialReportId && data.some((r) => r.id === initialReportId)) {
          setSelectedReportId(initialReportId);
        } else {
          setSelectedReportId(data[0].id);
        }
      }
      setLoading(false);
    });
  }, [initialReportId]);

  useEffect(() => {
    if (!selectedReportId) {
      setRelatedReports([]);
      return;
    }
    safetyService.getRelatedReports(selectedReportId).then((rel) => {
      setRelatedReports(rel);
    });
    setSelectedTokenIndex(null);
    setActiveHighlightCategory('all');
    setReviewSavedAlert(false);
    setReviewNoteInput('');
  }, [selectedReportId]);

  const selectedReport = useMemo(() => {
    if (!selectedReportId) return reports[0] || null;
    return reports.find((r) => r.id === selectedReportId) || reports[0] || null;
  }, [reports, selectedReportId]);

  const filterOptions = useMemo(() => {
    const reportTypes = Array.from(new Set(reports.map((r) => r.reportType))).filter(Boolean);
    const rules = Array.from(new Set(reports.map((r) => r.lifeSavingRule))).filter(Boolean);
    const precursors = Array.from(new Set(reports.map((r) => r.precursorClusterId))).filter(Boolean);
    const sites = Array.from(new Set(reports.map((r) => r.siteName))).filter(Boolean);
    return { reportTypes, rules, precursors, sites };
  }, [reports]);

  const filteredReports = useMemo(() => {
    let result = [...reports];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (r) =>
          r.id.toLowerCase().includes(q) ||
          r.rawNarrative.toLowerCase().includes(q) ||
          r.siteName.toLowerCase().includes(q) ||
          r.activity.toLowerCase().includes(q) ||
          r.lifeSavingRule.toLowerCase().includes(q) ||
          r.failedBarrier.toLowerCase().includes(q) ||
          (r.precursorClusterId && r.precursorClusterId.toLowerCase().includes(q)) ||
          r.actualOutcome.toLowerCase().includes(q) ||
          r.potentialConsequence.toLowerCase().includes(q)
      );
    }

    if (selectedReportType !== 'ALL') {
      result = result.filter((r) => r.reportType === selectedReportType);
    }

    if (selectedSifStatus !== 'ALL') {
      result = result.filter((r) => r.sifPotential === selectedSifStatus);
    }

    if (selectedLsr !== 'ALL') {
      result = result.filter((r) => r.lifeSavingRule === selectedLsr);
    }

    if (selectedPrecursor !== 'ALL') {
      result = result.filter((r) => r.precursorClusterId === selectedPrecursor);
    }

    if (selectedSite !== 'ALL') {
      result = result.filter((r) => r.siteName === selectedSite);
    }

    if (selectedHseStatus !== 'ALL') {
      result = result.filter((r) => r.hseReview?.status === selectedHseStatus);
    }

    result.sort((a, b) => {
      if (sortOption === 'newest') return b.timestamp.localeCompare(a.timestamp);
      if (sortOption === 'oldest') return a.timestamp.localeCompare(b.timestamp);
      if (sortOption === 'sif_first') {
        const score = (s: SifPotentialStatus) => (s === 'SIF_POTENTIAL' ? 2 : 1);
        return score(b.sifPotential) - score(a.sifPotential);
      }
      if (sortOption === 'verified_first') {
        const aVerified = a.hseReview?.status === 'HSE_VERIFIED' ? 2 : 1;
        const bVerified = b.hseReview?.status === 'HSE_VERIFIED' ? 2 : 1;
        return bVerified - aVerified;
      }
      return 0;
    });

    return result;
  }, [
    reports,
    searchQuery,
    selectedReportType,
    selectedSifStatus,
    selectedLsr,
    selectedPrecursor,
    selectedSite,
    selectedHseStatus,
    sortOption,
  ]);

  const handleUpdateReview = async (status: 'HSE_VERIFIED' | 'OVERRIDDEN' | 'PENDING_REVIEW') => {
    if (!selectedReport) return;
    try {
      const updated = await safetyService.updateHseReview(
        selectedReport.id,
        status,
        reviewNoteInput || selectedReport.hseReview?.notes || 'Status updated via Report Explorer.',
        'D. Borah, HSE Lead Superintendent'
      );
      setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setReviewSavedAlert(true);
      setTimeout(() => setReviewSavedAlert(false), 2500);
    } catch (err) {
      console.error('Failed to update HSE review:', err);
    }
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setSelectedReportType('ALL');
    setSelectedSifStatus('ALL');
    setSelectedLsr('ALL');
    setSelectedPrecursor('ALL');
    setSelectedSite('ALL');
    setSelectedHseStatus('ALL');
  };

  const renderInteractiveNarrativeTokens = (report: SafetyReport) => {
    const narrative = report.rawNarrative;
    const tokens = report.explainability?.tokens || [];

    if (!tokens.length) {
      return <span style={{ color: 'var(--text-primary)', lineHeight: 1.65 }}>{narrative}</span>;
    }

    const relevantTokens = tokens.filter((t) => {
      if (activeHighlightCategory === 'all') return true;
      if (activeHighlightCategory === 'energy') return t.category === 'energy';
      if (activeHighlightCategory === 'barrier') return t.category === 'barrier';
      if (activeHighlightCategory === 'action') return t.category === 'action';
      if (activeHighlightCategory === 'hazard') return t.category === 'hazard';
      if (activeHighlightCategory === 'consequence') return t.category === 'consequence';
      return true;
    });

    if (!relevantTokens.length) {
      return <span style={{ color: 'var(--text-primary)', lineHeight: 1.65 }}>{narrative}</span>;
    }

    let renderedElements: React.ReactNode[] = [];
    let currentIdx = 0;
    const sortedTokens = [...relevantTokens].sort(
      (a, b) => narrative.indexOf(a.text) - narrative.indexOf(b.text)
    );

    sortedTokens.forEach((tok, i) => {
      const matchPos = narrative.indexOf(tok.text, currentIdx);
      if (matchPos !== -1) {
        if (matchPos > currentIdx) {
          renderedElements.push(narrative.substring(currentIdx, matchPos));
        }

        const isSelected = selectedTokenIndex === i;
        let tokenColor = 'var(--primary-blue)';
        let tokenBg = 'var(--primary-blue-subtle)';

        if (tok.category === 'barrier') {
          tokenColor = 'var(--barrier-amber)';
          tokenBg = 'var(--barrier-amber-bg)';
        } else if (tok.category === 'hazard' || tok.category === 'consequence') {
          tokenColor = 'var(--sif-critical)';
          tokenBg = 'var(--sif-critical-bg)';
        }

        renderedElements.push(
          <mark
            key={`tok-${i}`}
            onClick={() => setSelectedTokenIndex(isSelected ? null : i)}
            style={{
              backgroundColor: isSelected ? 'rgba(217, 119, 6, 0.25)' : tokenBg,
              color: tokenColor,
              borderBottom: `2px solid ${tokenColor}`,
              padding: '0.1rem 0.35rem',
              borderRadius: '2px',
              cursor: 'pointer',
              fontWeight: 600,
              margin: '0 2px',
            }}
          >
            {tok.text}
          </mark>
        );
        currentIdx = matchPos + tok.text.length;
      }
    });

    if (currentIdx < narrative.length) {
      renderedElements.push(narrative.substring(currentIdx));
    }

    return <div style={{ lineHeight: 1.65, fontSize: '0.8125rem' }}>{renderedElements}</div>;
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ width: '28px', height: '28px', borderRadius: '50%', border: '2px solid var(--border-default)', borderTopColor: 'var(--primary-blue)', animation: 'spin 1s linear infinite', margin: '0 auto 1rem auto' }} />
        <div>Loading Safety Evidence Library...</div>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: '1.25rem 1.75rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
        maxWidth: '1600px',
        margin: '0 auto',
        width: '100%',
      }}
    >
      {/* 1. TOP HEADER & SEARCH BAR */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="oil-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            // 06 REPORT EXPLORER
          </span>
          <span style={{ color: 'var(--border-subtle)' }}>/</span>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            SAFETY EVIDENCE LIBRARY
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className="oil-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            {filteredReports.length} OF {reports.length} OBSERVATIONS MATCHED
          </span>
          <button
            onClick={handleResetFilters}
            className="oil-btn oil-btn-secondary"
            style={{ fontSize: '0.725rem', padding: '0.25rem 0.65rem' }}
          >
            <RotateCcw size={12} />
            <span>Reset Filters</span>
          </button>
        </div>
      </div>

      {/* 2. SEARCH & COMPOSE FILTER STRIP */}
      <div className="control-panel" style={{ padding: '0.85rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {/* Search Row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: 'var(--bg-canvas)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-xs)',
            padding: '0.4rem 0.75rem',
            gap: '0.5rem',
          }}
        >
          <Search size={15} style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search observation text, report ID (#UA-2024-...), failed barrier, activity or equipment..."
            style={{
              border: 'none',
              background: 'transparent',
              outline: 'none',
              fontSize: '0.8125rem',
              color: 'var(--text-primary)',
              width: '100%',
              fontFamily: 'var(--font-sans)',
            }}
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}>
              <X size={14} style={{ color: 'var(--text-muted)' }} />
            </button>
          )}
        </div>

        {/* Filter Dropdowns */}
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
          {/* Classification */}
          <select
            value={selectedReportType}
            onChange={(e) => setSelectedReportType(e.target.value)}
            style={{
              padding: '0.35rem 0.6rem',
              backgroundColor: 'var(--bg-canvas)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '0.725rem',
              color: 'var(--text-primary)',
            }}
          >
            <option value="ALL">All Classifications</option>
            {filterOptions.reportTypes.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          {/* SIF Status */}
          <select
            value={selectedSifStatus}
            onChange={(e) => setSelectedSifStatus(e.target.value)}
            style={{
              padding: '0.35rem 0.6rem',
              backgroundColor: 'var(--bg-canvas)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '0.725rem',
              color: 'var(--text-primary)',
            }}
          >
            <option value="ALL">All SIF Statuses</option>
            <option value="SIF_POTENTIAL">SIF Potential Only</option>
            <option value="NON_SIF">Non-SIF Routine Only</option>
          </select>

          {/* Life-Saving Rule */}
          <select
            value={selectedLsr}
            onChange={(e) => setSelectedLsr(e.target.value)}
            style={{
              padding: '0.35rem 0.6rem',
              backgroundColor: 'var(--bg-canvas)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '0.725rem',
              color: 'var(--text-primary)',
            }}
          >
            <option value="ALL">All Life-Saving Rules</option>
            {filterOptions.rules.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>

          {/* Asset / Site */}
          <select
            value={selectedSite}
            onChange={(e) => setSelectedSite(e.target.value)}
            style={{
              padding: '0.35rem 0.6rem',
              backgroundColor: 'var(--bg-canvas)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '0.725rem',
              color: 'var(--text-primary)',
            }}
          >
            <option value="ALL">All Asset Facilities</option>
            {filterOptions.sites.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {/* Sort */}
          <select
            value={sortOption}
            onChange={(e) => setSortOption(e.target.value as any)}
            style={{
              padding: '0.35rem 0.6rem',
              backgroundColor: 'var(--bg-canvas)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xs)',
              fontSize: '0.725rem',
              color: 'var(--text-primary)',
              marginLeft: 'auto',
            }}
          >
            <option value="newest">Sort: Newest First</option>
            <option value="oldest">Sort: Oldest First</option>
            <option value="sif_first">Sort: SIF Potential First</option>
            <option value="verified_first">Sort: HSE Verified First</option>
          </select>
        </div>
      </div>

      {/* 3. ASYMMETRIC SPLIT: LEFT EVIDENCE STREAM vs RIGHT INVESTIGATIVE DOSSIER */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.35fr', gap: '1.25rem', alignItems: 'start' }}>
        {/* ================= LEFT: EVIDENCE RESULTS FEED ================= */}
        <div className="control-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '820px', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
            <span className="section-tag">// OBSERVATION RESULTS</span>
            <span className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
              {filteredReports.length} MATCHES
            </span>
          </div>

          {filteredReports.length === 0 ? (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              No safety observations match the current search or filters.
            </div>
          ) : (
            filteredReports.map((rep) => {
              const isSelected = selectedReport?.id === rep.id;

              return (
                <div
                  key={rep.id}
                  onClick={() => setSelectedReportId(rep.id)}
                  className="control-panel"
                  style={{
                    padding: '0.75rem 0.85rem',
                    cursor: 'pointer',
                    borderColor: isSelected ? 'var(--primary-blue)' : 'var(--border-subtle)',
                    backgroundColor: isSelected ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                    borderLeft: isSelected ? '3px solid var(--primary-blue)' : undefined,
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span className="oil-mono" style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {rep.id}
                      </span>
                      <SafetyBadge status={rep.sifPotential} size="sm" />
                    </div>
                    <span className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {rep.timestamp}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.725rem', fontWeight: 600, color: 'var(--primary-blue)', marginBottom: '0.2rem' }}>
                    {rep.siteName} • {rep.activity}
                  </div>

                  <div
                    style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-secondary)',
                      lineHeight: 1.4,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    "{rep.rawNarrative}"
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.35rem', fontSize: '0.675rem' }}>
                    <span style={{ color: 'var(--barrier-amber)', fontWeight: 600 }}>
                      Barrier: {rep.failedBarrier}
                    </span>
                    <span style={{ color: isSelected ? 'var(--primary-blue)' : 'var(--text-muted)', fontWeight: 600 }}>
                      {isSelected ? 'ACTIVE DOSSIER' : 'INSPECT →'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* ================= RIGHT: THE INVESTIGATIVE EVIDENCE DOSSIER ================= */}
        {selectedReport ? (
          <div className="control-panel-elevated" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Dossier Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.35rem' }}>
                  <span className="oil-mono" style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {selectedReport.id}
                  </span>
                  <SafetyBadge status={selectedReport.sifPotential} size="md" />
                  <SafetyBadge status={selectedReport.hseReview?.status || 'PENDING_REVIEW'} size="md" />
                </div>
                <div style={{ fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
                  {selectedReport.siteName} • {selectedReport.timestamp} • Operational Scope: {selectedReport.operationalArea}
                </div>
              </div>

              {onNavigateToAnalyzer && (
                <button
                  onClick={() => onNavigateToAnalyzer(selectedReport)}
                  className="oil-btn oil-btn-secondary"
                  style={{ fontSize: '0.725rem', padding: '0.35rem 0.75rem', gap: '0.35rem' }}
                >
                  <span>Open in NLP Analyzer</span>
                  <ExternalLink size={12} />
                </button>
              )}
            </div>

            {/* Section 1: Original Observation & Semantic Tokens */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span className="section-tag">// ORIGINAL FIELD OBSERVATION</span>
                {/* Highlight Filters */}
                <div style={{ display: 'flex', gap: '0.25rem' }}>
                  {(['all', 'energy', 'barrier', 'hazard'] as const).map((cat) => (
                    <button
                      key={cat}
                      onClick={() => setActiveHighlightCategory(cat)}
                      style={{
                        padding: '0.15rem 0.45rem',
                        fontSize: '0.65rem',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '2px',
                        backgroundColor: activeHighlightCategory === cat ? 'var(--primary-blue-subtle)' : 'var(--bg-canvas)',
                        color: activeHighlightCategory === cat ? 'var(--primary-blue)' : 'var(--text-muted)',
                        cursor: 'pointer',
                        textTransform: 'uppercase',
                        fontWeight: activeHighlightCategory === cat ? 700 : 500,
                      }}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              <div className="control-panel-inset" style={{ padding: '0.85rem' }}>
                {renderInteractiveNarrativeTokens(selectedReport)}
              </div>
            </div>

            {/* Section 2: Cognitive Contrast: Outcome vs Potential */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="control-panel-inset" style={{ padding: '0.85rem' }}>
                <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  REPORTED ACTUAL OUTCOME
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                  {selectedReport.actualOutcome}
                </div>
              </div>

              <div className="control-panel-inset" style={{ padding: '0.85rem', borderLeft: '2px solid var(--sif-critical)' }}>
                <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--sif-critical)', textTransform: 'uppercase' }}>
                  POTENTIAL FATAL CONSEQUENCE
                </div>
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', fontWeight: 600, marginTop: '0.2rem' }}>
                  {selectedReport.potentialConsequence}
                </div>
              </div>
            </div>

            {/* Section 3: Safety Forensics (Energy, Barrier, Rule) */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.775rem' }}>
              <div className="control-panel" style={{ padding: '0.85rem' }}>
                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--barrier-amber)', textTransform: 'uppercase' }}>
                  FAILED BARRIER
                </span>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.15rem' }}>
                  {selectedReport.failedBarrier}
                </div>
              </div>

              <div className="control-panel" style={{ padding: '0.85rem' }}>
                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--primary-blue)', textTransform: 'uppercase' }}>
                  LIFE-SAVING RULE
                </span>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.15rem' }}>
                  {selectedReport.lifeSavingRule}
                </div>
              </div>
            </div>

            {/* Section 4: Connected Precursor Jump */}
            {selectedReport.precursorClusterId && (
              <div
                style={{
                  padding: '0.75rem 1rem',
                  backgroundColor: 'var(--bg-canvas)',
                  border: '1px solid var(--border-default)',
                  borderLeft: '4px solid var(--sif-critical)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--sif-critical)', textTransform: 'uppercase' }}>
                    LINKED RECURRING PRECURSOR
                  </div>
                  <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    #{selectedReport.precursorClusterId}
                  </div>
                </div>
                {onNavigateToPrecursor && (
                  <button
                    onClick={() => onNavigateToPrecursor(selectedReport.precursorClusterId!)}
                    className="oil-btn oil-btn-primary"
                    style={{ fontSize: '0.725rem', padding: '0.35rem 0.75rem', gap: '0.35rem' }}
                  >
                    <span>View Pattern</span>
                    <ChevronRight size={13} />
                  </button>
                )}
              </div>
            )}

            {/* Correlated Observations */}
            {relatedReports.length > 0 && (
              <div className="control-panel" style={{ padding: '0.85rem' }}>
                <span className="section-tag" style={{ marginBottom: '0.5rem' }}>
                  // CORRELATED SAFETY OBSERVATIONS ({relatedReports.length})
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  {relatedReports.slice(0, 2).map((rel) => (
                    <div
                      key={rel.report.id}
                      onClick={() => setSelectedReportId(rel.report.id)}
                      className="control-panel-inset"
                      style={{ padding: '0.5rem 0.75rem', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span className="oil-mono" style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                            {rel.report.id}
                          </span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            {rel.connectionReason}
                          </span>
                        </div>
                      </div>
                      <span className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--primary-blue)' }}>
                        INSPECT →
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Section 5: HSE Superintendent Verification Console */}
            <div className="control-panel" style={{ padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <UserCheck size={14} style={{ color: 'var(--verified-emerald)' }} />
                  <span style={{ fontSize: '0.775rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    HSE SUPERINTENDENT REVIEW
                  </span>
                </div>
                {reviewSavedAlert && (
                  <span style={{ fontSize: '0.6875rem', color: 'var(--verified-emerald)', fontWeight: 600 }}>
                    ✓ Review saved to register
                  </span>
                )}
              </div>

              <textarea
                value={reviewNoteInput}
                onChange={(e) => setReviewNoteInput(e.target.value)}
                placeholder="Enter validation notes or corrective action directives..."
                style={{
                  width: '100%',
                  minHeight: '50px',
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
                  <span>Mark Overridden</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="control-panel-inset" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            Select an observation from the library to inspect its forensic dossier.
          </div>
        )}
      </div>
    </div>
  );
};
