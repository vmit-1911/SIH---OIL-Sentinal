import React from 'react';
import {
  Activity,
  Network,
  Cpu,
  Building2,
  ShieldAlert,
  FileSearch,
} from 'lucide-react';

export type ActiveNavTab =
  | 'command-center'
  | 'precursors'
  | 'analyzer'
  | 'sites'
  | 'lsr'
  | 'explorer';

interface NavigationRailProps {
  activeTab: ActiveNavTab;
  onSelectTab: (tab: ActiveNavTab) => void;
}

export const NavigationRail: React.FC<NavigationRailProps> = ({
  activeTab,
  onSelectTab,
}) => {
  const navItems = [
    {
      id: 'command-center' as ActiveNavTab,
      indexCode: '01',
      label: 'Command Briefing',
      sublabel: 'Operational Landscape',
      icon: Activity,
      badge: undefined,
    },
    {
      id: 'precursors' as ActiveNavTab,
      indexCode: '02',
      label: 'Precursor Topology',
      sublabel: 'Pattern Connections',
      icon: Network,
      badge: '1 Critical',
    },
    {
      id: 'analyzer' as ActiveNavTab,
      indexCode: '03',
      label: 'AI Report Analyzer',
      sublabel: 'Explainable NLP',
      icon: Cpu,
      badge: undefined,
    },
    {
      id: 'sites' as ActiveNavTab,
      indexCode: '04',
      label: 'Spatial Exposure',
      sublabel: 'Asset Concentration',
      icon: Building2,
      badge: undefined,
    },
    {
      id: 'lsr' as ActiveNavTab,
      indexCode: '05',
      label: 'Life-Saving Rules',
      sublabel: 'IOGP Safeguards',
      icon: ShieldAlert,
      badge: undefined,
    },
    {
      id: 'explorer' as ActiveNavTab,
      indexCode: '06',
      label: 'Report Explorer',
      sublabel: 'Evidence Library',
      icon: FileSearch,
      badge: undefined,
    },
  ];

  return (
    <nav
      style={{
        height: '50px',
        backgroundColor: '#ffffff',
        borderBottom: '1px solid var(--border-default)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.5rem',
        boxShadow: 'var(--shadow-subtle)',
        zIndex: 25,
        overflowX: 'auto',
      }}
    >
      {/* Horizontal Nav Modules */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.55rem',
                padding: '0.4rem 0.85rem',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: isActive ? 'var(--bg-canvas)' : 'transparent',
                border: '1px solid',
                borderColor: isActive ? 'var(--border-default)' : 'transparent',
                borderBottom: isActive ? '2px solid var(--primary-blue)' : '2px solid transparent',
                color: isActive ? 'var(--primary-blue)' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.12s ease',
                position: 'relative',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'var(--bg-subtle)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }
              }}
            >
              <span
                className="oil-mono"
                style={{
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  color: isActive ? 'var(--primary-blue)' : 'var(--text-muted)',
                }}
              >
                //{item.indexCode}
              </span>

              <Icon
                size={14}
                style={{
                  color: isActive ? 'var(--primary-blue)' : 'var(--text-muted)',
                  flexShrink: 0,
                }}
              />

              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: '0.775rem', fontWeight: isActive ? 700 : 600, letterSpacing: '0.01em', lineHeight: 1.15 }}>
                  {item.label}
                </div>
              </div>

              {item.badge && (
                <span
                  style={{
                    backgroundColor: 'var(--sif-critical-bg)',
                    border: '1px solid var(--sif-critical-border)',
                    color: 'var(--sif-critical-text)',
                    fontSize: '0.6rem',
                    fontWeight: 700,
                    padding: '0.05rem 0.35rem',
                    borderRadius: 'var(--radius-xs)',
                    letterSpacing: '0.03em',
                  }}
                  className="oil-mono"
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Persistent Technical Footprint Counters */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', paddingLeft: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.725rem' }}>
          <span style={{ color: 'var(--text-muted)' }}>ANALYZED:</span>
          <span className="oil-mono" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>1,482</span>
        </div>

        <div style={{ width: '1px', height: '12px', backgroundColor: 'var(--border-subtle)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.725rem' }}>
          <span style={{ color: 'var(--sif-critical-text)' }}>SIF POTENTIAL:</span>
          <span className="oil-mono" style={{ fontWeight: 700, color: 'var(--sif-critical-text)' }}>164</span>
        </div>

        <div style={{ width: '1px', height: '12px', backgroundColor: 'var(--border-subtle)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.725rem' }}>
          <span style={{ color: 'var(--barrier-amber-text)' }}>RECURRING PATTERNS:</span>
          <span className="oil-mono" style={{ fontWeight: 700, color: 'var(--barrier-amber-text)' }}>7</span>
        </div>
      </div>
    </nav>
  );
};
