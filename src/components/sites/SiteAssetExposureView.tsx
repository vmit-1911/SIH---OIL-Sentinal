import React, { useState, useEffect } from 'react';
import {
  ArrowRight,
  Calendar,
  ChevronRight,
  BarChart3,
  Compass,
} from 'lucide-react';
import type {
  SiteAssetExposure,
  PrecursorFilterOption,
  ExposureTrendPoint,
  SafetyReport,
} from '../../types/safety';
import { SafetyBadge } from '../common/SafetyBadge';
import { safetyService } from '../../services/safetyService';

interface SiteAssetExposureViewProps {
  onNavigateToPrecursor: (clusterId: string) => void;
  onOpenReport: (reportId: string) => void;
}

export const SiteAssetExposureView: React.FC<SiteAssetExposureViewProps> = ({
  onNavigateToPrecursor,
  onOpenReport,
}) => {
  const [precursorFilters, setPrecursorFilters] = useState<PrecursorFilterOption[]>([]);
  const [selectedPrecursorId, setSelectedPrecursorId] = useState<string>('ALL');
  const [siteExposures, setSiteExposures] = useState<SiteAssetExposure[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string>('site-moran-07');
  const [timeWindow, setTimeWindow] = useState<'7d' | '30d' | '90d'>('30d');
  const [trendPoints, setTrendPoints] = useState<ExposureTrendPoint[]>([]);
  const [selectedActivityFilter, setSelectedActivityFilter] = useState<string | null>(null);
  const [connectedReports, setConnectedReports] = useState<SafetyReport[]>([]);

  useEffect(() => {
    Promise.all([
      safetyService.getPrecursorFilterOptions(),
      safetyService.getSiteExposures(selectedPrecursorId),
      safetyService.getExposureTrends(timeWindow),
      safetyService.getReports(),
    ]).then(([filters, sites, trends, allReports]) => {
      setPrecursorFilters(filters);
      setSiteExposures(sites);
      setTrendPoints(trends);
      setConnectedReports(allReports);

      if (sites.length > 0 && !sites.some((s) => s.siteId === selectedSiteId)) {
        setSelectedSiteId(sites[0].siteId);
      }
    });
  }, [selectedPrecursorId, timeWindow]);

  const selectedSite = siteExposures.find((s) => s.siteId === selectedSiteId) || siteExposures[0] || null;

  const siteReports = selectedSite
    ? connectedReports.filter((r) => {
        const matchesSite = r.siteId === selectedSite.siteId;
        if (!selectedActivityFilter) return matchesSite;
        return matchesSite && r.activity.toLowerCase().includes(selectedActivityFilter.toLowerCase());
      })
    : [];

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
      {/* 1. TOP HEADER & TELEMETRY CONTROLS */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="oil-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            // 04 SPATIAL EXPOSURE
          </span>
          <span style={{ color: 'var(--border-subtle)' }}>/</span>
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            ASSAM BASIN ASSET CONCENTRATION
          </span>
        </div>

        {/* Time Window Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Calendar size={13} style={{ color: 'var(--text-muted)' }} />
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

      {/* 2. PRECURSOR FILTER STRIP */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          overflowX: 'auto',
          paddingBottom: '0.25rem',
        }}
      >
        <span className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
          PRECURSOR FILTER:
        </span>
        {precursorFilters.map((p) => {
          const isSelected = selectedPrecursorId === p.id;

          return (
            <button
              key={p.id}
              onClick={() => {
                setSelectedPrecursorId(p.id);
                setSelectedActivityFilter(null);
              }}
              className="control-panel"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.3rem 0.65rem',
                backgroundColor: isSelected ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                borderColor: isSelected ? 'var(--primary-blue)' : 'var(--border-subtle)',
                color: isSelected ? 'var(--primary-blue)' : 'var(--text-secondary)',
                fontWeight: isSelected ? 700 : 500,
                fontSize: '0.75rem',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              <span>{p.title}</span>
              <span className="oil-mono" style={{ fontSize: '0.65rem', opacity: 0.8 }}>
                ({p.connectedReportsCount})
              </span>
            </button>
          );
        })}
      </div>

      {/* 3. THREE-COLUMN SPATIAL EXPOSURE INTELLIGENCE WORKSPACE */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.35fr 1.15fr', gap: '1.25rem', alignItems: 'start' }}>
        {/* ================= LEFT COLUMN: MONITORED ASSET SECTORS ================= */}
        <div className="control-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
            <span className="section-tag">// OPERATIONAL ASSETS</span>
            <span className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
              {siteExposures.length} SITES
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {siteExposures.map((site) => {
              const isSelected = selectedSiteId === site.siteId;
              const isHighDensity = site.precursorDensityPercent >= 25.0;

              return (
                <div
                  key={site.siteId}
                  onClick={() => {
                    setSelectedSiteId(site.siteId);
                    setSelectedActivityFilter(null);
                  }}
                  className="control-panel"
                  style={{
                    padding: '0.75rem 0.85rem',
                    cursor: 'pointer',
                    borderColor: isSelected ? 'var(--primary-blue)' : 'var(--border-subtle)',
                    backgroundColor: isSelected ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                    <span className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                      {site.clusterArea}
                    </span>
                    <span className="oil-mono" style={{ fontSize: '0.65rem', color: site.trend === 'INCREASING' ? 'var(--sif-critical)' : 'var(--text-muted)', fontWeight: 600 }}>
                      {site.trend === 'INCREASING' ? '▲ ACCELERATING' : '— STABLE'}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {site.siteName}
                  </div>

                  {/* Precursor Density Meter */}
                  <div style={{ marginTop: '0.45rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '0.2rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Precursor Density</span>
                      <span className="oil-mono" style={{ fontWeight: 700, color: isHighDensity ? 'var(--sif-critical)' : 'var(--text-primary)' }}>
                        {site.precursorDensityPercent}% ({site.sifPotentialCount}/{site.totalObservations})
                      </span>
                    </div>
                    <div style={{ height: '4px', backgroundColor: 'var(--bg-inset)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${site.precursorDensityPercent}%`,
                          height: '100%',
                          backgroundColor: isHighDensity ? 'var(--sif-critical)' : 'var(--primary-blue)',
                        }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ================= CENTER COLUMN: SPATIAL SCHEMATIC ================= */}
        <div className="control-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Compass size={15} style={{ color: 'var(--primary-blue)' }} />
              <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                SPATIAL EXPOSURE TOPOLOGY
              </span>
            </div>
            <span className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
              SYNTHETIC BASIN MAP
            </span>
          </div>

          {/* Spatial Grid Schematic Container */}
          <div
            className="control-panel-inset"
            style={{
              padding: '1.5rem',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '1.25rem',
              position: 'relative',
              minHeight: '260px',
            }}
          >
            {siteExposures.map((site) => {
              const isSelected = selectedSiteId === site.siteId;
              const isHigh = site.precursorDensityPercent >= 25.0;

              return (
                <div
                  key={site.siteId}
                  onClick={() => setSelectedSiteId(site.siteId)}
                  className="control-panel"
                  style={{
                    padding: '0.85rem',
                    cursor: 'pointer',
                    borderColor: isSelected ? 'var(--primary-blue)' : 'var(--border-default)',
                    backgroundColor: isSelected ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                    borderLeft: isHigh ? '3px solid var(--sif-critical)' : '3px solid var(--border-elevated)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="oil-mono" style={{ fontSize: '0.625rem', color: 'var(--text-muted)' }}>
                      SECTOR // {site.clusterArea.toUpperCase()}
                    </span>
                    <span className={isHigh ? 'signal-tag-critical' : 'signal-tag-info'} style={{ fontSize: '0.6rem' }}>
                      {site.precursorDensityPercent}% DENSITY
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.35rem' }}>
                    {site.siteName}
                  </div>
                  <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    Rule: {site.lifeSavingRule}
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
            * <strong>Spatial Exposure Note:</strong> This topology illustrates cross-site hazard concentration and barrier decay across monitored operational facilities in Upper Assam. Precursor density isolates where fatal energy is accumulating regardless of overall reporting volume.
          </div>
        </div>

        {/* ================= RIGHT COLUMN: SELECTED ASSET PROFILE ================= */}
        {selectedSite && (
          <div className="control-panel-inset" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <span className="section-tag">// ASSET INTELLIGENCE</span>
                <span className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                  ID: {selectedSite.siteId}
                </span>
              </div>

              <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {selectedSite.siteName}
              </h2>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {selectedSite.clusterArea} • {selectedSite.assetClass}
              </div>
            </div>

            {/* SIF Density Anchor */}
            <div className="control-panel" style={{ padding: '0.85rem', backgroundColor: 'var(--bg-surface)' }}>
              <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                PRECURSOR CONCENTRATION DENSITY
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginTop: '0.2rem' }}>
                <span className="display-anchor display-anchor-sif" style={{ fontSize: '1.5rem' }}>
                  {selectedSite.precursorDensityPercent}%
                </span>
                <span className="oil-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  ({selectedSite.sifPotentialCount} SIF / {selectedSite.totalObservations} Total)
                </span>
              </div>
            </div>

            {/* Dominant Precursor & Failed Barrier */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.75rem' }}>
              <div>
                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Dominant Precursor Pattern:
                </span>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.1rem' }}>
                  {selectedSite.dominantPrecursorTitle}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Failed Barrier:
                </span>
                <div style={{ fontWeight: 600, color: 'var(--barrier-amber)', marginTop: '0.1rem' }}>
                  {selectedSite.failedBarrier}
                </div>
              </div>
            </div>

            {/* Activity Filters */}
            <div>
              <div style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                Observed Operational Activities:
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                {selectedSite.activities.map((act) => {
                  const isFiltered = selectedActivityFilter === act.activityName;

                  return (
                    <button
                      key={act.activityName}
                      onClick={() => setSelectedActivityFilter(isFiltered ? null : act.activityName)}
                      className="oil-btn oil-btn-secondary"
                      style={{
                        padding: '0.2rem 0.5rem',
                        fontSize: '0.6875rem',
                        backgroundColor: isFiltered ? 'var(--primary-blue-subtle)' : 'var(--bg-surface)',
                        borderColor: isFiltered ? 'var(--primary-blue)' : 'var(--border-subtle)',
                        color: isFiltered ? 'var(--primary-blue)' : 'var(--text-secondary)',
                      }}
                    >
                      <span>{act.activityName}</span>
                      <span className="oil-mono" style={{ opacity: 0.8 }}>({act.count})</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Action Jump to Precursor */}
            <button
              onClick={() => onNavigateToPrecursor(selectedSite.dominantPrecursorId)}
              className="oil-btn oil-btn-primary"
              style={{ fontSize: '0.775rem', padding: '0.5rem 0.85rem', width: '100%', gap: '0.4rem', marginTop: '0.25rem' }}
            >
              <span>Inspect Precursor Topology</span>
              <ArrowRight size={13} />
            </button>
          </div>
        )}
      </div>

      {/* 4. LOWER WORKSPACE: VELOCITY TREND & EVIDENCE DOSSIER STREAM */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: '1.25rem', alignItems: 'start' }}>
        {/* Left: Trend Sparkline */}
        <div className="control-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BarChart3 size={15} style={{ color: 'var(--primary-blue)' }} />
              <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                EXPOSURE VELOCITY ({timeWindow.toUpperCase()})
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.65rem' }}>
              <span style={{ color: 'var(--sif-critical)', fontWeight: 600 }}>■ SIF Precursors</span>
              <span style={{ color: 'var(--text-muted)' }}>■ Routine Reports</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem', height: '90px', borderBottom: '1px solid var(--border-subtle)' }}>
            {trendPoints.map((pt) => {
              const sifHeight = Math.max(6, (pt.sifCount / 30) * 70);
              const routineHeight = Math.max(10, (pt.routineCount / 100) * 60);

              return (
                <div key={pt.timeLabel} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.2rem', height: '100%', justifyContent: 'flex-end' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px' }}>
                    <div style={{ width: '8px', height: `${sifHeight}px`, backgroundColor: 'var(--sif-critical)', borderRadius: '1px 1px 0 0' }} />
                    <div style={{ width: '8px', height: `${routineHeight}px`, backgroundColor: 'var(--border-default)', borderRadius: '1px 1px 0 0' }} />
                  </div>
                  <span className="oil-mono" style={{ fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {pt.timeLabel}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Site Evidence Rows */}
        <div className="control-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              SITE EVIDENCE STREAM ({siteReports.length} OBSERVATIONS)
            </span>
            <span className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
              CLICK ROW FOR DOSSIER
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
            {siteReports.slice(0, 3).map((rep) => (
              <div
                key={rep.id}
                onClick={() => onOpenReport(rep.id)}
                className="control-panel"
                style={{
                  padding: '0.6rem 0.85rem',
                  cursor: 'pointer',
                  display: 'grid',
                  gridTemplateColumns: '110px 100px 1fr 110px',
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
  );
};
