import React from 'react';
import {
  ArrowRight,
  ShieldAlert,
  ChevronRight,
  Clock,
  Compass,
  FileText,
  TrendingUp,
} from 'lucide-react';
import type { PrecursorCluster, SafetyReport, CommandCenterMetrics } from '../../types/safety';
import { SafetyBadge } from '../common/SafetyBadge';

interface CommandCenterViewProps {
  metrics: CommandCenterMetrics;
  precursorCluster: PrecursorCluster;
  recentReports: SafetyReport[];
  onInspectPrecursor: (clusterId: string) => void;
  onOpenReport: (reportId: string) => void;
}

export const CommandCenterView: React.FC<CommandCenterViewProps> = ({
  metrics,
  precursorCluster,
  recentReports,
  onInspectPrecursor,
  onOpenReport,
}) => {
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
      {/* 1. TOP OPERATIONAL BRIEFING BANNER (ASYMMETRIC SPLIT) */}
      <div
        className="control-panel-elevated"
        style={{
          borderLeft: '4px solid var(--sif-critical)',
          display: 'grid',
          gridTemplateColumns: '1.6fr 1fr',
          gap: '2rem',
          padding: '1.5rem 1.75rem',
          position: 'relative',
        }}
      >
        {/* Left Column: The Dominant Signal */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            {/* Status & Signal Metadata Hairline */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
              <span className="signal-tag-critical" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <span className="pulse-sif" style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: 'var(--sif-critical)' }} />
                CRITICAL SIGNAL // ACTIVE SIF EMERGENCE
              </span>
              <span className="oil-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                PATTERN ID: #{precursorCluster.id}
              </span>
              <span style={{ color: 'var(--border-subtle)' }}>|</span>
              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--barrier-amber)' }}>
                IOGP SAFEGUARD: {precursorCluster.lifeSavingRule}
              </span>
              <span style={{ color: 'var(--border-subtle)' }}>|</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                VELOCITY: <strong style={{ color: 'var(--sif-critical)' }}>{precursorCluster.trendVelocity}</strong>
              </span>
            </div>

            {/* Dominant Intelligence Headline */}
            <h1
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                letterSpacing: '-0.025em',
                lineHeight: 1.25,
                marginBottom: '0.75rem',
              }}
            >
              Repeated isolation verification failures detected across multiple pressurized asset operations
            </h1>

            {/* Narrative Explanation */}
            <p
              style={{
                fontSize: '0.875rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.55,
                marginBottom: '1rem',
                maxWidth: '860px',
              }}
            >
              Observed field reports repeatedly describe work on pressurized manifolds, mud pumps, and wellhead valves without positive double block & bleed or padlocked LOTO disconnects. While all recent field incidents recorded zero lost-time injuries, opening live fluid/gas lines under pressure is a verified primary precursor to fatal injection and catastrophic projectile blowout.
            </p>
          </div>

          {/* Action Row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
            <button
              onClick={() => onInspectPrecursor(precursorCluster.id)}
              className="oil-btn oil-btn-primary"
              style={{
                padding: '0.65rem 1.25rem',
                fontSize: '0.8125rem',
                gap: '0.5rem',
              }}
            >
              <Compass size={15} />
              <span>Investigate Precursor Topology Map</span>
              <ArrowRight size={14} />
            </button>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Cross-asset correlation verified by NLP evidence chain
            </span>
          </div>
        </div>

        {/* Right Column: Industrial Readout Panel */}
        <div
          className="control-panel-inset"
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '1.25rem',
          }}
        >
          <div>
            <div className="section-tag" style={{ marginBottom: '0.75rem' }}>
              // TELEMETRY SNAPSHOT
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              {/* Metric 1 */}
              <div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  SIF Precursor Density
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem', marginTop: '0.2rem' }}>
                  <span className="display-anchor display-anchor-sif" style={{ fontSize: '1.75rem' }}>
                    {metrics.sifDensityPercent}%
                  </span>
                  <span className="oil-mono" style={{ fontSize: '0.75rem', color: 'var(--sif-critical)' }}>
                    ({metrics.sifFlaggedCount} / {metrics.totalAnalyzed})
                  </span>
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Incoming observations harboring fatal potential
                </div>
              </div>

              {/* Metric 2 */}
              <div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  Systemic Clusters
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem', marginTop: '0.2rem' }}>
                  <span className="display-anchor" style={{ fontSize: '1.75rem', color: 'var(--barrier-amber)' }}>
                    {metrics.activePrecursorClusters}
                  </span>
                  <span className="signal-tag-warning" style={{ fontSize: '0.65rem' }}>ACTIVE</span>
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Multi-site recurring failure patterns
                </div>
              </div>

              {/* Metric 3 */}
              <div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  HSE Verification Rate
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem', marginTop: '0.2rem' }}>
                  <span className="display-anchor" style={{ fontSize: '1.75rem', color: 'var(--verified-emerald)' }}>
                    {metrics.verifiedByHsePercent}%
                  </span>
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Superintendent confirmed reviews
                </div>
              </div>

              {/* Metric 4 */}
              <div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  Affected Asset Hubs
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem', marginTop: '0.2rem' }}>
                  <span className="display-anchor" style={{ fontSize: '1.75rem', color: 'var(--text-primary)' }}>
                    {precursorCluster.assetsInvolved.length}
                  </span>
                  <span className="oil-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    FACILITIES
                  </span>
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                  Duliajan, Moran, Digboi, Naharkatiya
                </div>
              </div>
            </div>
          </div>

          <div
            style={{
              marginTop: '1rem',
              paddingTop: '0.75rem',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
            }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Clock size={12} /> Observation Range: {precursorCluster.earliestReport} — {precursorCluster.latestReport}
            </span>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
              Assam Basin Division
            </span>
          </div>
        </div>
      </div>

      {/* 2. MIDDLE SPLIT: SIGNAL DEVELOPMENT & WHY IT MATTERS */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '1.25rem' }}>
        {/* Left: Signal Timeline & Emergence Footprint */}
        <div className="control-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <TrendingUp size={16} style={{ color: 'var(--primary-blue)' }} />
              <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                SIGNAL DEVELOPMENT TIMELINE & FIELD FOOTPRINT
              </span>
            </div>
            <span className="oil-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              // CHRONOLOGICAL EMERGENCE
            </span>
          </div>

          {/* Horizontal Progression Strip */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '0.5rem',
              padding: '0.75rem',
              backgroundColor: 'var(--bg-inset)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ borderLeft: '2px solid var(--border-default)', paddingLeft: '0.5rem' }}>
              <div className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>OCT 14 // 14:15</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.15rem' }}>Moran #07</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)' }}>Manifold valve cracked without bleed verification</div>
            </div>

            <div style={{ borderLeft: '2px solid var(--barrier-amber)', paddingLeft: '0.5rem' }}>
              <div className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>OCT 19 // 09:30</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.15rem' }}>Duliajan Rig #14</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)' }}>Mud pump fluid end opened; LOTO lock missing</div>
            </div>

            <div style={{ borderLeft: '2px solid var(--barrier-amber)', paddingLeft: '0.5rem' }}>
              <div className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>OCT 22 // 16:45</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.15rem' }}>Digboi OCS-2</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)' }}>Separator inlet valve isolated without bleeder open</div>
            </div>

            <div style={{ borderLeft: '2px solid var(--sif-critical)', paddingLeft: '0.5rem' }}>
              <div className="oil-mono" style={{ fontSize: '0.65rem', color: 'var(--sif-critical)' }}>OCT 24 // 11:20</div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.15rem' }}>NHK #11</div>
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)' }}>HP pipeline union unbolted under trapped pressure</div>
            </div>
          </div>

          {/* Footprint Matrix */}
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
            OPERATIONAL SITE & ACTIVITY DISTRIBUTION
          </div>
          <table className="dense-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>ASSET / SITE</th>
                <th>OPERATIONAL ACTIVITY</th>
                <th>FAILED SAFEGUARD</th>
                <th>CONSEQUENCE PROFILE</th>
                <th>REPORTS</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Duliajan Rig #14</td>
                <td>Mud Pump Fluid End Overhaul</td>
                <td><span className="signal-tag-warning" style={{ fontSize: '0.65rem' }}>Double Block & Bleed</span></td>
                <td>Hydrocarbon / Mud Injection</td>
                <td className="oil-mono" style={{ fontWeight: 600 }}>3</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Moran Drilling #07</td>
                <td>High-Pressure Manifold Rig-Up</td>
                <td><span className="signal-tag-warning" style={{ fontSize: '0.65rem' }}>Padlocked LOTO Lockout</span></td>
                <td>Projectile Blowout</td>
                <td className="oil-mono" style={{ fontWeight: 600 }}>2</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Digboi OCS-2</td>
                <td>Separator Depressurization</td>
                <td><span className="signal-tag-warning" style={{ fontSize: '0.65rem' }}>Positive Zero-Energy Check</span></td>
                <td>Toxic H2S Release</td>
                <td className="oil-mono" style={{ fontWeight: 600 }}>2</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Naharkatiya Wellhead #11</td>
                <td>Xmas Tree Valve Replacement</td>
                <td><span className="signal-tag-warning" style={{ fontSize: '0.65rem' }}>Mechanical Line Blanking</span></td>
                <td>Uncontrolled Well Blowout</td>
                <td className="oil-mono" style={{ fontWeight: 600 }}>1</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Right: Why It Matters & Safeguard Integrity */}
        <div className="control-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldAlert size={16} style={{ color: 'var(--barrier-amber)' }} />
                <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  IOGP BARRIER DEGRADATION
                </span>
              </div>
              <span className="oil-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                // LAST 30 DAYS
              </span>
            </div>

            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', lineHeight: 1.45 }}>
              Proportion of precursor observations where secondary or primary barriers failed to arrest hazardous energy:
            </p>

            {/* Barrier Breakdown Bars */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Energy Isolation & LOTO Verification</span>
                  <span className="oil-mono" style={{ color: 'var(--sif-critical)', fontWeight: 700 }}>42% (HIGH SEVERITY)</span>
                </div>
                <div style={{ height: '5px', backgroundColor: 'var(--bg-inset)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: '42%', height: '100%', backgroundColor: 'var(--sif-critical)' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Line of Fire Exclusion Barricading</span>
                  <span className="oil-mono" style={{ color: 'var(--barrier-amber)', fontWeight: 700 }}>28%</span>
                </div>
                <div style={{ height: '5px', backgroundColor: 'var(--bg-inset)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: '28%', height: '100%', backgroundColor: 'var(--barrier-amber)' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Confined Space Gas Testing</span>
                  <span className="oil-mono" style={{ color: 'var(--barrier-amber)', fontWeight: 700 }}>18%</span>
                </div>
                <div style={{ height: '5px', backgroundColor: 'var(--bg-inset)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: '18%', height: '100%', backgroundColor: 'var(--barrier-amber)' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Working at Height 100% Tie-Off</span>
                  <span className="oil-mono" style={{ color: 'var(--text-secondary)', fontWeight: 700 }}>12%</span>
                </div>
                <div style={{ height: '5px', backgroundColor: 'var(--bg-inset)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ width: '12%', height: '100%', backgroundColor: 'var(--primary-blue)' }} />
                </div>
              </div>
            </div>
          </div>

          <div
            className="control-panel-inset"
            style={{
              marginTop: '1.25rem',
              padding: '0.85rem',
              fontSize: '0.75rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.45,
            }}
          >
            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
              OPERATIONAL RISK CORRELATION
            </div>
            73% of Energy Isolation observations correlate directly with mud pump fluid end overhauls and wellhead valve maintenance in the Moran & Duliajan drilling sectors.
          </div>
        </div>
      </div>

      {/* 3. EVIDENCE STREAM: HIGH-DENSITY INVESTIGATIVE ROWS */}
      <div className="control-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileText size={16} style={{ color: 'var(--primary-blue)' }} />
            <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              UNDERLYING SAFETY EVIDENCE STREAM
            </span>
            <span className="signal-tag-info" style={{ fontSize: '0.65rem' }}>
              {recentReports.length} OBSERVATIONS HARBORING PRECURSORS
            </span>
          </div>
          <span className="oil-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            CLICK ANY OBSERVATION TO LAUNCH EXPLAINABLE EVIDENCE DOSSIER
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {recentReports.slice(0, 4).map((report) => (
            <div
              key={report.id}
              onClick={() => onOpenReport(report.id)}
              className="control-panel"
              style={{
                padding: '0.75rem 1rem',
                cursor: 'pointer',
                transition: 'border-color 0.15s ease, background-color 0.15s ease',
                display: 'grid',
                gridTemplateColumns: '130px 140px 180px 1fr 140px',
                alignItems: 'center',
                gap: '1rem',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--primary-blue)';
                e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-subtle)';
                e.currentTarget.style.backgroundColor = 'var(--bg-surface)';
              }}
            >
              {/* ID & Date */}
              <div>
                <div className="oil-mono" style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {report.id}
                </div>
                <div className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                  {report.timestamp}
                </div>
              </div>

              {/* Status Badges */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', alignItems: 'flex-start' }}>
                <SafetyBadge status={report.sifPotential} size="sm" />
                <SafetyBadge status={report.hseReview.status} size="sm" />
              </div>

              {/* Site & Activity */}
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {report.siteName}
                </div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)' }}>
                  {report.activity}
                </div>
              </div>

              {/* Verbatim Narrative Snippet */}
              <div style={{ overflow: 'hidden' }}>
                <div
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.4,
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                    overflow: 'hidden',
                  }}
                >
                  "{report.rawNarrative}"
                </div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                  Recorded Outcome: <strong style={{ color: 'var(--text-primary)' }}>{report.actualOutcome}</strong>
                </div>
              </div>

              {/* Action Trigger */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '0.25rem', color: 'var(--primary-blue)', fontSize: '0.75rem', fontWeight: 600 }}>
                <span>Inspect Dossier</span>
                <ChevronRight size={14} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
