import React, { useState, useEffect, useMemo } from 'react';
import {
  ShieldAlert,
  ArrowRight,
  Search,
  FileText,
  ChevronRight,
  X,
} from 'lucide-react';
import type {
  LsrIntelligenceSummary,
  LifeSavingRule,
  SafetyReport,
} from '../../types/safety';
import { safetyService } from '../../services/safetyService';
import type { LsrTrendPoint } from '../../services/mockLsrData';
import { SafetyBadge } from '../common/SafetyBadge';

interface LifeSavingRulesViewProps {
  onNavigateToPrecursor?: (precursorId: string) => void;
  onNavigateToSite?: (siteId: string) => void;
  onOpenReport?: (reportId: string) => void;
  onNavigateToAnalyzer?: () => void;
}

type SortCriterion = 'most_observed' | 'sif_count' | 'precursors';

export const LifeSavingRulesView: React.FC<LifeSavingRulesViewProps> = ({
  onNavigateToPrecursor,
  onNavigateToSite: _onNavigateToSite,
  onOpenReport,
  onNavigateToAnalyzer: _onNavigateToAnalyzer,
}) => {
  const [summaries, setSummaries] = useState<LsrIntelligenceSummary[]>([]);
  const [selectedRuleId, setSelectedRuleId] = useState<LifeSavingRule>('Energy Isolation');
  const [timeWindow, setTimeWindow] = useState<'7d' | '30d' | '90d'>('30d');
  const [sifOnly, setSifOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortCriterion, setSortCriterion] = useState<SortCriterion>('most_observed');

  // Interactive secondary filters
  const [selectedActivity, setSelectedActivity] = useState<string | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);

  // Evidence reports & trend data
  const [reports, setReports] = useState<SafetyReport[]>([]);
  const [, setTrendData] = useState<LsrTrendPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    safetyService.getLifeSavingRuleSummaries().then((data) => {
      setSummaries(data);
      if (data.length > 0 && !data.some((d) => d.ruleId === selectedRuleId)) {
        setSelectedRuleId(data[0].ruleId);
      }
      setLoading(false);
    });
  }, [selectedRuleId]);

  useEffect(() => {
    safetyService.getLifeSavingRuleTrend(selectedRuleId, timeWindow).then((trend) => {
      setTrendData(trend);
    });
  }, [selectedRuleId, timeWindow]);

  useEffect(() => {
    safetyService
      .getLifeSavingRuleReports(selectedRuleId, {
        activity: selectedActivity || undefined,
        siteId: selectedAssetId || undefined,
        sifOnly,
      })
      .then((reps) => {
        setReports(reps);
      });
  }, [selectedRuleId, selectedActivity, selectedAssetId, sifOnly]);

  const handleSelectRule = (ruleId: LifeSavingRule) => {
    setSelectedRuleId(ruleId);
    setSelectedActivity(null);
    setSelectedAssetId(null);
  };

  const selectedRule = useMemo(() => {
    return summaries.find((s) => s.ruleId === selectedRuleId) || summaries[0];
  }, [summaries, selectedRuleId]);

  const filteredRules = useMemo(() => {
    let list = [...summaries];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (r) =>
          r.ruleName.toLowerCase().includes(q) ||
          r.whyAppearingText.toLowerCase().includes(q) ||
          r.primaryFailedBarrier.toLowerCase().includes(q)
      );
    }

    list.sort((a, b) => {
      if (sortCriterion === 'most_observed') {
        return b.totalConnectedObservations - a.totalConnectedObservations;
      }
      if (sortCriterion === 'sif_count') {
        return b.sifPotentialObservations - a.sifPotentialObservations;
      }
      if (sortCriterion === 'precursors') {
        return b.recurringPrecursorsCount - a.recurringPrecursorsCount;
      }
      return 0;
    });

    return list;
  }, [summaries, searchQuery, sortCriterion]);

  if (loading || !selectedRule) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ width: '28px', height: '28px', borderRadius: '50%', border: '2px solid var(--border-default)', borderTopColor: 'var(--primary-blue)', animation: 'spin 1s linear infinite', margin: '0 auto 1rem auto' }} />
        <div>Loading Life-Saving Rules Intelligence...</div>
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
        maxWidth: '1560px',
        margin: '0 auto',
        width: '100%',
      }}
    >
      {/* 1. TOP UTILITY HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="oil-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            // 05 LIFE-SAVING RULES
          </span>
          <span style={{ color: 'var(--border-subtle)' }}>/</span>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            IOGP SAFEGUARD COMPLIANCE & DECAY
          </span>
        </div>

        {/* Time Window Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          {(['7d', '30d', '90d'] as const).map((tw) => (
            <button
              key={tw}
              onClick={() => setTimeWindow(tw)}
              className="oil-btn oil-btn-secondary"
              style={{
                padding: '0.25rem 0.65rem',
                fontSize: '0.725rem',
                backgroundColor: timeWindow === tw ? 'var(--primary-blue-subtle)' : 'var(--bg-surface)',
                borderColor: timeWindow === tw ? 'var(--primary-blue)' : 'var(--border-default)',
                color: timeWindow === tw ? 'var(--primary-blue)' : 'var(--text-secondary)',
                fontWeight: timeWindow === tw ? 700 : 500,
              }}
            >
              {tw === '7d' ? '7 Days' : tw === '30d' ? '30 Days' : '90 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* 2. MAIN SPLIT: LEFT (INDEX) vs RIGHT (SELECTED RULE WORKSPACE) */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '1.25rem', alignItems: 'start' }}>
        {/* ================= LEFT COLUMN: RULE INTELLIGENCE INDEX ================= */}
        <div className="control-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="section-tag">// IOGP RULES INDEX</span>
            <span className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
              {filteredRules.length} SAFEGUARDS
            </span>
          </div>

          {/* Quick Search */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: 'var(--bg-canvas)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-xs)',
              padding: '0.35rem 0.6rem',
              gap: '0.4rem',
            }}
          >
            <Search size={13} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search rule or barrier..."
              style={{
                border: 'none',
                background: 'transparent',
                outline: 'none',
                fontSize: '0.75rem',
                color: 'var(--text-primary)',
                width: '100%',
              }}
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: 0 }}>
                <X size={12} style={{ color: 'var(--text-muted)' }} />
              </button>
            )}
          </div>

          {/* Sort Buttons */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.3rem' }}>
            <button
              onClick={() => setSortCriterion('most_observed')}
              className="oil-btn oil-btn-secondary"
              style={{
                fontSize: '0.65rem',
                padding: '0.2rem',
                backgroundColor: sortCriterion === 'most_observed' ? 'var(--primary-blue-subtle)' : 'var(--bg-canvas)',
                borderColor: sortCriterion === 'most_observed' ? 'var(--primary-blue)' : 'var(--border-subtle)',
                color: sortCriterion === 'most_observed' ? 'var(--primary-blue)' : 'var(--text-secondary)',
                fontWeight: sortCriterion === 'most_observed' ? 700 : 500,
              }}
            >
              Observed
            </button>
            <button
              onClick={() => setSortCriterion('sif_count')}
              className="oil-btn oil-btn-secondary"
              style={{
                fontSize: '0.65rem',
                padding: '0.2rem',
                backgroundColor: sortCriterion === 'sif_count' ? 'var(--sif-critical-bg)' : 'var(--bg-canvas)',
                borderColor: sortCriterion === 'sif_count' ? 'var(--sif-critical)' : 'var(--border-subtle)',
                color: sortCriterion === 'sif_count' ? 'var(--sif-critical)' : 'var(--text-secondary)',
                fontWeight: sortCriterion === 'sif_count' ? 700 : 500,
              }}
            >
              SIF-Pot
            </button>
            <button
              onClick={() => setSortCriterion('precursors')}
              className="oil-btn oil-btn-secondary"
              style={{
                fontSize: '0.65rem',
                padding: '0.2rem',
                backgroundColor: sortCriterion === 'precursors' ? 'var(--barrier-amber-bg)' : 'var(--bg-canvas)',
                borderColor: sortCriterion === 'precursors' ? 'var(--barrier-amber)' : 'var(--border-subtle)',
                color: sortCriterion === 'precursors' ? 'var(--barrier-amber)' : 'var(--text-secondary)',
                fontWeight: sortCriterion === 'precursors' ? 700 : 500,
              }}
            >
              Precursor
            </button>
          </div>

          {/* Rules List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: '680px', overflowY: 'auto' }}>
            {filteredRules.map((rule, idx) => {
              const isSelected = rule.ruleId === selectedRuleId;

              return (
                <div
                  key={rule.ruleId}
                  onClick={() => handleSelectRule(rule.ruleId)}
                  className="control-panel"
                  style={{
                    padding: '0.65rem 0.85rem',
                    cursor: 'pointer',
                    borderColor: isSelected ? 'var(--primary-blue)' : 'var(--border-subtle)',
                    backgroundColor: isSelected ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                    borderLeft: isSelected ? '3px solid var(--primary-blue)' : undefined,
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                        0{idx + 1}
                      </span>
                      <span style={{ fontSize: '0.8125rem', fontWeight: isSelected ? 700 : 600, color: isSelected ? 'var(--primary-blue)' : 'var(--text-primary)' }}>
                        {rule.ruleName}
                      </span>
                    </div>
                    <ChevronRight size={13} style={{ color: isSelected ? 'var(--primary-blue)' : 'var(--text-muted)' }} />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.35rem', fontSize: '0.6875rem' }}>
                    <span className="oil-mono" style={{ color: 'var(--text-secondary)' }}>
                      {rule.totalConnectedObservations} reports
                    </span>
                    {rule.sifPotentialObservations > 0 && (
                      <span className="signal-tag-critical" style={{ fontSize: '0.6rem' }}>
                        {rule.sifPotentialObservations} SIF
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ================= RIGHT COLUMN: SELECTED RULE INVESTIGATION WORKSPACE ================= */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Dominant Selected Rule Briefing Banner */}
          <div
            className="control-panel-elevated"
            style={{
              padding: '1.25rem 1.5rem',
              borderLeft: selectedRule.sifPotentialObservations > 0 ? '4px solid var(--sif-critical)' : '4px solid var(--primary-blue)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                  <ShieldAlert size={16} style={{ color: 'var(--primary-blue)' }} />
                  <span className="section-tag">IOGP SAFEGUARD INVESTIGATION</span>
                  <span className="oil-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    TREND: {selectedRule.trendVelocity}
                  </span>
                </div>

                <h1 style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 0.4rem 0' }}>
                  {selectedRule.ruleName}
                </h1>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: 0, maxWidth: '820px', lineHeight: 1.5 }}>
                  {selectedRule.whyAppearingText}
                </p>
              </div>
            </div>

            {/* Readout Numbers Strip */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: '1rem',
                marginTop: '1.25rem',
                paddingTop: '1rem',
                borderTop: '1px solid var(--border-subtle)',
              }}
            >
              <div>
                <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Connected Observations
                </div>
                <div className="display-anchor" style={{ fontSize: '1.5rem', marginTop: '0.15rem' }}>
                  {selectedRule.totalConnectedObservations}
                </div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>All incoming reports</div>
              </div>

              <div>
                <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--sif-critical)', textTransform: 'uppercase' }}>
                  SIF Precursors Flagged
                </div>
                <div className="display-anchor display-anchor-sif" style={{ fontSize: '1.5rem', marginTop: '0.15rem' }}>
                  {selectedRule.sifPotentialObservations}
                </div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--sif-critical)' }}>
                  {selectedRule.totalConnectedObservations > 0
                    ? `${Math.round((selectedRule.sifPotentialObservations / selectedRule.totalConnectedObservations) * 100)}% density`
                    : '0%'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--barrier-amber)', textTransform: 'uppercase' }}>
                  Recurring Precursors
                </div>
                <div className="display-anchor" style={{ fontSize: '1.5rem', color: 'var(--barrier-amber)', marginTop: '0.15rem' }}>
                  {selectedRule.recurringPrecursorsCount}
                </div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Multi-site clusters</div>
              </div>

              <div>
                <div style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Affected Asset Hubs
                </div>
                <div className="display-anchor" style={{ fontSize: '1.5rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                  {selectedRule.affectedAssetsCount}
                </div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Operating facilities</div>
              </div>
            </div>
          </div>

          {/* Cognitive Contrast: Outcome vs Potential */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div className="control-panel-inset" style={{ padding: '0.85rem' }}>
              <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                RECORDED ACTUAL OUTCOME (WHAT HAPPENED)
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontStyle: 'italic', marginTop: '0.2rem' }}>
                "{selectedRule.reportedOutcomeSummary}"
              </div>
            </div>

            <div className="control-panel-inset" style={{ padding: '0.85rem', borderLeft: '2px solid var(--sif-critical)' }}>
              <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--sif-critical)', textTransform: 'uppercase' }}>
                POTENTIAL FATAL TRAJECTORY (WHAT COULD HAVE HAPPENED)
              </div>
              <div style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', fontWeight: 600, marginTop: '0.2rem' }}>
                {selectedRule.potentialConsequenceSummary}
              </div>
            </div>
          </div>

          {/* Middle Split: Connected Precursors & Barrier Spotlight */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.25rem' }}>
            {/* Connected Precursor Clusters */}
            <div className="control-panel" style={{ padding: '1.25rem' }}>
              <div className="section-tag" style={{ marginBottom: '0.5rem' }}>
                // CONNECTED PRECURSORS
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                {selectedRule.precursors[0]?.title || selectedRule.ruleName}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.45, marginBottom: '0.85rem' }}>
                {selectedRule.totalConnectedObservations} field observations demonstrate recurring breakdown of this specific safeguard across {selectedRule.affectedAssetsCount} operational installations.
              </div>

              {onNavigateToPrecursor && (
                <button
                  onClick={() => onNavigateToPrecursor('PREC-04-ENERGY-ISO')}
                  className="oil-btn oil-btn-primary"
                  style={{ fontSize: '0.75rem', padding: '0.45rem 0.85rem', gap: '0.4rem' }}
                >
                  <span>Investigate Precursor Topology</span>
                  <ArrowRight size={13} />
                </button>
              )}
            </div>

            {/* Primary Failed Barrier */}
            <div className="control-panel" style={{ padding: '1.25rem' }}>
              <div className="section-tag" style={{ marginBottom: '0.5rem' }}>
                // PRIMARY FAILED BARRIER
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--barrier-amber)', marginBottom: '0.35rem' }}>
                {selectedRule.primaryFailedBarrier}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                {selectedRule.failedBarrierDescription}
              </div>
            </div>
          </div>

          {/* Evidence Stream for This Rule */}
          <div className="control-panel" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={15} style={{ color: 'var(--primary-blue)' }} />
                <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  CONNECTED EVIDENCE LOG ({reports.length} REPORTS)
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <button
                  onClick={() => setSifOnly(!sifOnly)}
                  className="oil-btn oil-btn-secondary"
                  style={{
                    fontSize: '0.6875rem',
                    padding: '0.2rem 0.5rem',
                    backgroundColor: sifOnly ? 'var(--sif-critical-bg)' : 'var(--bg-canvas)',
                    borderColor: sifOnly ? 'var(--sif-critical)' : 'var(--border-subtle)',
                    color: sifOnly ? 'var(--sif-critical)' : 'var(--text-secondary)',
                  }}
                >
                  {sifOnly ? 'SIF Only (Active)' : 'Filter SIF Only'}
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              {reports.slice(0, 4).map((rep) => (
                <div
                  key={rep.id}
                  onClick={() => onOpenReport && onOpenReport(rep.id)}
                  className="control-panel"
                  style={{
                    padding: '0.65rem 0.85rem',
                    cursor: 'pointer',
                    display: 'grid',
                    gridTemplateColumns: '120px 100px 140px 1fr 110px',
                    alignItems: 'center',
                    gap: '0.75rem',
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
                    <div className="oil-mono" style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {rep.id}
                    </div>
                    <div className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {rep.timestamp}
                    </div>
                  </div>

                  <SafetyBadge status={rep.sifPotential} size="sm" />

                  <div style={{ fontSize: '0.725rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {rep.siteName}
                  </div>

                  <div style={{ overflow: 'hidden' }}>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                      "{rep.rawNarrative}"
                    </div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {rep.activity}
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '0.2rem', color: 'var(--primary-blue)', fontSize: '0.725rem', fontWeight: 600 }}>
                    <span>Inspect</span>
                    <ChevronRight size={13} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
