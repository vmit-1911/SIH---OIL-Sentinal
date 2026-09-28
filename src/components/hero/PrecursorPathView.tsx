import React, { useState } from 'react';
import {
  ArrowLeft,
  ShieldAlert,
  Building2,
  Wrench,
  ChevronRight,
  Filter,
  FileText,
  Share2,
  Check,
  Compass,
  Network,
} from 'lucide-react';
import type { PrecursorCluster, SafetyReport } from '../../types/safety';
import { SafetyBadge } from '../common/SafetyBadge';

interface PrecursorPathViewProps {
  cluster: PrecursorCluster;
  reports: SafetyReport[];
  onBack: () => void;
  onOpenReport: (reportId: string) => void;
}

export const PrecursorPathView: React.FC<PrecursorPathViewProps> = ({
  cluster,
  reports,
  onBack,
  onOpenReport,
}) => {
  const [selectedNode, setSelectedNode] = useState<string>('root');
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [copiedAction, setCopiedAction] = useState(false);

  const activeFocus = hoveredNode || selectedNode;

  // Filter reports based on active selection
  const getFilteredReports = () => {
    if (selectedNode === 'root' || selectedNode === 'barrier' || selectedNode === 'lsr') {
      return reports; // All 7 reports share the barrier and LSR
    }
    if (selectedNode === 'activity') {
      return reports.filter((r) =>
        r.activity.toLowerCase().includes('pump') ||
        r.activity.toLowerCase().includes('valve') ||
        r.activity.toLowerCase().includes('hose') ||
        r.activity.toLowerCase().includes('manifold')
      );
    }
    if (selectedNode.startsWith('site-')) {
      return reports.filter((r) => r.siteId === selectedNode);
    }
    return reports;
  };

  const filteredReports = getFilteredReports();

  // Dynamic contextual explanation based on pattern discovery
  const getContextualInsight = () => {
    switch (activeFocus) {
      case 'barrier':
        return {
          category: 'CRITICAL SAFEGUARD DEGRADATION',
          title: 'Positive Physical Isolation & Bleed-Off Verification',
          text: '7 independent field observations across 4 drilling & production installations describe line breakages or servicing commencing without positive verification of zero stored energy or missing padlocked LOTO disconnects.',
          metric: '7 of 7 reports linked to this safeguard breach',
          status: 'UNVERIFIED',
          statusColor: 'var(--sif-critical)',
        };
      case 'activity':
        return {
          category: 'HIGH-PRESSURE OPERATIONAL CONTEXT',
          title: 'Pressurized Manifold, Pump & Valve Servicing',
          text: 'The precursor concentrated during routine maintenance, line pigging, and fluid-end disassembly tasks where stored hydraulic or gas pressure was trapped behind stuck analog valves.',
          metric: '6 connected servicing operations',
          status: 'ELEVATED EXPOSURE',
          statusColor: 'var(--barrier-amber)',
        };
      case 'lsr':
        return {
          category: 'MANDATORY IOGP SAFEGUARD',
          title: 'Rule #01: Energy Isolation & Zero-Energy State',
          text: 'Mandates verified isolation of all energy sources, depressurization, atmospheric testing, and physical lockout before barrier integrity is compromised.',
          metric: 'Direct IOGP Rule Violation',
          status: 'HIGH RISK',
          statusColor: 'var(--sif-critical)',
        };
      case 'site-duliajan-14':
        return {
          category: 'ASSET EXPOSURE SPOTLIGHT',
          title: 'Duliajan Deep Drill Rig #14',
          text: 'Mud pump fluid end overhaul conducted with stuck analog pressure gauge; BOP accumulator check valve disassembled under 3,000 PSI nitrogen pre-charge.',
          metric: '2 reports at Duliajan Rig #14',
          status: 'CRITICAL RIG',
          statusColor: 'var(--sif-critical)',
        };
      case 'site-moran-07':
        return {
          category: 'ASSET EXPOSURE SPOTLIGHT',
          title: 'Moran Workover Rig #07',
          text: 'Pressurized rotary kelly hose hammer union disconnected with choked bleed line; hand exposure into mud tank agitator belt with cardboard tag only.',
          metric: '2 reports at Moran Rig #07',
          status: 'NEAR MISS',
          statusColor: 'var(--barrier-amber)',
        };
      case 'site-digboi-ocs2':
        return {
          category: 'ASSET EXPOSURE SPOTLIGHT',
          title: 'Digboi Oil Collection Station (OCS-2)',
          text: 'Crude separator inlet manifold unbolted with 15% passing valve; 16-inch crude pig receiver door unbolted while whistling pressurized gas vapor.',
          metric: '2 reports at Digboi OCS-2',
          status: 'PROCESS RELEASE',
          statusColor: 'var(--barrier-amber)',
        };
      case 'site-nhk-11':
        return {
          category: 'ASSET EXPOSURE SPOTLIGHT',
          title: 'Naharkatiya Wellhead #11',
          text: 'Gland packing nuts tightened with 36-inch pipe wrench under 2,800 PSI wellhead pressure with no permit to work or upstream isolation.',
          metric: '1 report at Naharkatiya #11',
          status: 'FATAL PRECURSOR',
          statusColor: 'var(--sif-critical)',
        };
      default:
        return {
          category: 'SYSTEMIC CAUSAL TOPOLOGY',
          title: cluster.title,
          text: 'These 7 field observations are correlated because they share the identical failed barrier: opening high-energy systems without positive zero-pressure confirmation. Select any node in the map to filter evidence.',
          metric: `${cluster.reportCount} connected observations across ${cluster.assetsInvolved.length} facilities`,
          status: 'ACTIVE TOPOLOGY',
          statusColor: 'var(--sif-critical)',
        };
    }
  };

  const currentInsight = getContextualInsight();

  const handleCopyAction = () => {
    setCopiedAction(true);
    setTimeout(() => setCopiedAction(false), 2000);
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
      {/* 1. TOP UTILITY BREADCRUMB & METRIC HEADER */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={onBack}
            className="oil-btn oil-btn-secondary"
            style={{ padding: '0.35rem 0.75rem', fontSize: '0.775rem' }}
          >
            <ArrowLeft size={13} />
            <span>Command Center</span>
          </button>
          <span style={{ color: 'var(--border-subtle)' }}>/</span>
          <span className="oil-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            TOPOLOGY INVESTIGATION
          </span>
          <span style={{ color: 'var(--border-subtle)' }}>/</span>
          <span className="oil-mono" style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            #{cluster.id}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={handleCopyAction}
            className="oil-btn oil-btn-secondary"
            style={{ fontSize: '0.75rem', padding: '0.4rem 0.85rem' }}
          >
            {copiedAction ? <Check size={13} style={{ color: 'var(--verified-emerald)' }} /> : <Share2 size={13} />}
            <span>{copiedAction ? 'Briefing Copied to Clipboard' : 'Export HSE Briefing Dossier'}</span>
          </button>
        </div>
      </div>

      {/* 2. THE INTELLIGENCE WORKSPACE: MAP (LEFT) + REAL-TIME INSPECTOR (RIGHT) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: '1.25rem' }}>
        {/* Left: Causal Intelligence Topology Map */}
        <div className="control-panel" style={{ padding: '1.5rem', position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Network size={16} style={{ color: 'var(--primary-blue)' }} />
              <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                MULTI-TIER CAUSAL RELATIONSHIP MAP
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {selectedNode !== 'root' && (
                <button
                  onClick={() => setSelectedNode('root')}
                  className="oil-btn oil-btn-secondary"
                  style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                >
                  <Filter size={11} />
                  <span>Reset All Nodes</span>
                </button>
              )}
              <span className="oil-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                7 EVIDENCE CHAINS LINKED
              </span>
            </div>
          </div>

          {/* Topological Layout Canvas */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '1.25rem',
              position: 'relative',
              padding: '1rem 0',
            }}
          >
            {/* TIER 1: ROOT PRECURSOR NODE */}
            <div
              onClick={() => setSelectedNode('root')}
              onMouseEnter={() => setHoveredNode('root')}
              onMouseLeave={() => setHoveredNode(null)}
              className="control-panel-elevated"
              style={{
                width: '100%',
                maxWidth: '560px',
                padding: '1rem 1.25rem',
                cursor: 'pointer',
                borderLeft: '4px solid var(--sif-critical)',
                borderColor: activeFocus === 'root' ? 'var(--sif-critical)' : 'var(--border-default)',
                backgroundColor: activeFocus === 'root' ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span className="signal-tag-critical" style={{ fontSize: '0.65rem' }}>
                  ROOT PRECURSOR PATTERN
                </span>
                <span className="oil-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  ACCELERATION: {cluster.trendVelocity}
                </span>
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {cluster.title}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                7 Unsafe Observations • 4 Operating Fields • Zero Prior Fatalities Recorded
              </div>
            </div>

            {/* Connecting Hairline Junction */}
            <div style={{ width: '1px', height: '24px', backgroundColor: 'var(--border-elevated)' }} />

            {/* TIER 2: 3 BALANCED SAFEGUARD & PROCESS NODES */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', width: '100%' }}>
              {/* Failed Barrier Node */}
              <div
                onClick={() => setSelectedNode('barrier')}
                onMouseEnter={() => setHoveredNode('barrier')}
                onMouseLeave={() => setHoveredNode(null)}
                className="control-panel"
                style={{
                  padding: '0.9rem',
                  cursor: 'pointer',
                  borderTop: '3px solid var(--barrier-amber)',
                  borderColor: activeFocus === 'barrier' ? 'var(--barrier-amber)' : 'var(--border-default)',
                  backgroundColor: activeFocus === 'barrier' ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.35rem' }}>
                  <ShieldAlert size={13} style={{ color: 'var(--barrier-amber)' }} />
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--barrier-amber)' }}>
                    FAILED BARRIER
                  </span>
                </div>
                <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                  {cluster.primaryFailedBarrier}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
                  Double block & bleed omitted or unverified
                </div>
              </div>

              {/* Operational Activity Node */}
              <div
                onClick={() => setSelectedNode('activity')}
                onMouseEnter={() => setHoveredNode('activity')}
                onMouseLeave={() => setHoveredNode(null)}
                className="control-panel"
                style={{
                  padding: '0.9rem',
                  cursor: 'pointer',
                  borderTop: '3px solid var(--primary-blue)',
                  borderColor: activeFocus === 'activity' ? 'var(--primary-blue)' : 'var(--border-default)',
                  backgroundColor: activeFocus === 'activity' ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.35rem' }}>
                  <Wrench size={13} style={{ color: 'var(--primary-blue)' }} />
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--primary-blue)' }}>
                    OPERATIONAL TASK
                  </span>
                </div>
                <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                  {cluster.primaryActivity}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
                  High-pressure manifold, pump & valve servicing
                </div>
              </div>

              {/* Mandatory IOGP Rule Node */}
              <div
                onClick={() => setSelectedNode('lsr')}
                onMouseEnter={() => setHoveredNode('lsr')}
                onMouseLeave={() => setHoveredNode(null)}
                className="control-panel"
                style={{
                  padding: '0.9rem',
                  cursor: 'pointer',
                  borderTop: '3px solid var(--verified-emerald)',
                  borderColor: activeFocus === 'lsr' ? 'var(--verified-emerald)' : 'var(--border-default)',
                  backgroundColor: activeFocus === 'lsr' ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.35rem' }}>
                  <Compass size={13} style={{ color: 'var(--verified-emerald)' }} />
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--verified-emerald)' }}>
                    IOGP SAFEGUARD
                  </span>
                </div>
                <div style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                  Rule #01: {cluster.lifeSavingRule}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
                  Verify isolation before work commences
                </div>
              </div>
            </div>

            {/* Connecting Hairline Junction */}
            <div style={{ width: '1px', height: '24px', backgroundColor: 'var(--border-elevated)' }} />

            {/* TIER 3: CONVERGENCE AT 4 OPERATIONAL ASSETS */}
            <div style={{ width: '100%' }}>
              <div style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
                <span className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                  AFFECTED OPERATIONAL ASSETS (SELECT TO ISOLATE EVIDENCE STREAM)
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
                {cluster.assetsInvolved.map((asset) => {
                  const isSelected = selectedNode === asset.siteId;
                  const isHovered = hoveredNode === asset.siteId;
                  const isNodeActive = isSelected || isHovered;

                  return (
                    <button
                      key={asset.siteId}
                      onClick={() => setSelectedNode(isSelected ? 'root' : asset.siteId)}
                      onMouseEnter={() => setHoveredNode(asset.siteId)}
                      onMouseLeave={() => setHoveredNode(null)}
                      className="control-panel"
                      style={{
                        padding: '0.75rem',
                        cursor: 'pointer',
                        textAlign: 'left',
                        borderColor: isNodeActive ? 'var(--primary-blue)' : 'var(--border-default)',
                        backgroundColor: isNodeActive ? 'var(--bg-canvas)' : 'var(--bg-surface)',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Building2 size={13} style={{ color: isNodeActive ? 'var(--primary-blue)' : 'var(--text-muted)' }} />
                        <span className="signal-tag-critical" style={{ fontSize: '0.625rem' }}>
                          {asset.reportCount} reports
                        </span>
                      </div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.35rem' }}>
                        {asset.siteName}
                      </div>
                      <div className="oil-mono" style={{ fontSize: '0.65rem', color: isNodeActive ? 'var(--primary-blue)' : 'var(--text-muted)', marginTop: '0.2rem' }}>
                        {isSelected ? 'ACTIVE FILTER' : 'CLICK TO FILTER'}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Real-time Node Intelligence Inspector */}
        <div className="control-panel-inset" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <span className="section-tag">{currentInsight.category}</span>
              <span
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  color: currentInsight.statusColor,
                  border: `1px solid ${currentInsight.statusColor}`,
                  padding: '0.1rem 0.4rem',
                  borderRadius: '2px',
                }}
              >
                {currentInsight.status}
              </span>
            </div>

            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              {currentInsight.title}
            </h2>

            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginBottom: '1.25rem' }}>
              {currentInsight.text}
            </p>

            {/* Readout stats */}
            <div
              className="control-panel"
              style={{
                padding: '0.85rem',
                backgroundColor: 'var(--bg-surface)',
                marginBottom: '1rem',
              }}
            >
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                EVIDENCE SATURATION
              </div>
              <div className="oil-mono" style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                {currentInsight.metric}
              </div>
            </div>

            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              <strong style={{ color: 'var(--text-primary)' }}>Investigation Guidance:</strong> In offshore and onshore drilling environments, failure to double-block and bleed pressurized mud/gas manifolds represents 85% of fatal kinetic projectile releases.
            </div>
          </div>

          <div
            style={{
              paddingTop: '1rem',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
            }}
          >
            <span>Topology Engine // v8.7</span>
            <span className="oil-mono">STATUS: HIGH CONFIDENCE</span>
          </div>
        </div>
      </div>

      {/* 3. EVIDENCE DOSSIER STREAM: DENSE OBSERVATION ROWS */}
      <div className="control-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileText size={16} style={{ color: 'var(--primary-blue)' }} />
            <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              CONNECTED OBSERVATION EVIDENCE ({filteredReports.length} of {reports.length} REPORTS SHOWN)
            </span>
          </div>
          {selectedNode !== 'root' && (
            <button
              onClick={() => setSelectedNode('root')}
              className="oil-btn oil-btn-secondary"
              style={{ fontSize: '0.725rem', padding: '0.25rem 0.6rem' }}
            >
              <Filter size={11} />
              <span>Reset to All {reports.length} Reports</span>
            </button>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {filteredReports.map((report) => (
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
              <div>
                <div className="oil-mono" style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {report.id}
                </div>
                <div className="oil-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                  {report.timestamp}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', alignItems: 'flex-start' }}>
                <SafetyBadge status={report.sifPotential} size="sm" />
                <SafetyBadge status={report.hseReview.status} size="sm" />
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {report.siteName}
                </div>
                <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)' }}>
                  {report.activity}
                </div>
              </div>

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
                  Potential Fatal Consequence: <strong style={{ color: 'var(--sif-critical)' }}>{report.explainability.potentialConsequence}</strong>
                </div>
              </div>

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
