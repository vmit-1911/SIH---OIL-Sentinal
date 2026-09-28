import React, { useState, useEffect } from 'react';
import { TopUtilityBar } from './components/layout/TopUtilityBar';
import { NavigationRail } from './components/layout/NavigationRail';
import type { ActiveNavTab } from './components/layout/NavigationRail';
import { CommandCenterView } from './components/hero/CommandCenterView';
import { PrecursorPathView } from './components/hero/PrecursorPathView';
import { AiReportAnalyzerView } from './components/analyzer/AiReportAnalyzerView';
import { SiteAssetExposureView } from './components/sites/SiteAssetExposureView';
import { LifeSavingRulesView } from './components/lsr/LifeSavingRulesView';
import { ReportExplorerView } from './components/explorer/ReportExplorerView';
import { EvidenceDossierModal } from './components/hero/EvidenceDossierModal';
import { safetyService } from './services/safetyService';
import { MOCK_ADDITIONAL_RULE_REPORTS } from './services/mockLsrData';
import type {
  SafetyReport,
  PrecursorCluster,
  CommandCenterMetrics,
} from './types/safety';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveNavTab>('command-center');
  const [metrics, setMetrics] = useState<CommandCenterMetrics | null>(null);
  const [activeCluster, setActiveCluster] = useState<PrecursorCluster | null>(null);
  const [reports, setReports] = useState<SafetyReport[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Load initial safety intelligence data
  useEffect(() => {
    const loadData = async () => {
      try {
        const [metricsData, clusterData, reportsData] = await Promise.all([
          safetyService.getCommandCenterMetrics(),
          safetyService.getPrecursorClusterById('PREC-04-ENERGY-ISO'),
          safetyService.getReports(),
        ]);

        setMetrics(metricsData);
        setActiveCluster(clusterData.cluster);
        setReports(reportsData);
      } catch (err) {
        console.error('Failed to load safety telemetry:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleInspectPrecursor = (_clusterId: string) => {
    setActiveTab('precursors');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleOpenReport = (reportId: string) => {
    setSelectedReportId(reportId);
  };

  const handleCloseReport = () => {
    setSelectedReportId(null);
  };

  const handleUpdateReview = async (
    reportId: string,
    status: 'HSE_VERIFIED' | 'OVERRIDDEN',
    notes: string
  ) => {
    try {
      const updatedReport = await safetyService.updateHseReview(
        reportId,
        status,
        notes,
        'D. Borah, HSE Lead Superintendent'
      );
      setReports((prev) =>
        prev.map((r) => (r.id === reportId ? updatedReport : r))
      );
    } catch (err) {
      console.error('Failed to update HSE review:', err);
    }
  };

  const activeReport = selectedReportId
    ? reports.find((r) => r.id === selectedReportId) ||
      Object.values(MOCK_ADDITIONAL_RULE_REPORTS)
        .flat()
        .find((r) => r.id === selectedReportId) ||
      null
    : null;

  if (loading || !metrics || !activeCluster) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--bg-canvas)',
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-mono)',
          gap: '1rem',
        }}
      >
        <div style={{ width: '32px', height: '32px', borderRadius: '50%', border: '3px solid var(--border-default)', borderTopColor: 'var(--tech-cyan-bright)', animation: 'spin 1s linear infinite' }} />
        <div>INITIALIZING OIL-SIF SAFETY INTELLIGENCE ENGINE...</div>
      </div>
    );
  }

  return (
    <div className="oil-app-container" style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', width: '100%' }}>
      {/* Industrial Mission Control Header Stack */}
      <TopUtilityBar
        onPrecursorClick={() => handleInspectPrecursor(activeCluster.id)}
        activePrecursorTitle={activeCluster.title}
      />
      <NavigationRail activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* Main Operational Intelligence Workspace */}
      <main style={{ flex: 1, overflowY: 'auto', backgroundColor: 'var(--bg-canvas)' }}>
          {activeTab === 'command-center' ? (
            <CommandCenterView
              metrics={metrics}
              precursorCluster={activeCluster}
              recentReports={reports}
              onInspectPrecursor={handleInspectPrecursor}
              onOpenReport={handleOpenReport}
            />
          ) : activeTab === 'precursors' ? (
            <PrecursorPathView
              cluster={activeCluster}
              reports={reports}
              onBack={() => setActiveTab('command-center')}
              onOpenReport={handleOpenReport}
            />
          ) : activeTab === 'analyzer' ? (
            <AiReportAnalyzerView
              onNavigateToPrecursor={handleInspectPrecursor}
            />
          ) : activeTab === 'sites' ? (
            <SiteAssetExposureView
              onNavigateToPrecursor={handleInspectPrecursor}
              onOpenReport={handleOpenReport}
            />
          ) : activeTab === 'lsr' ? (
            <LifeSavingRulesView
              onNavigateToPrecursor={handleInspectPrecursor}
              onNavigateToSite={(_siteId) => {
                setActiveTab('sites');
              }}
              onOpenReport={handleOpenReport}
              onNavigateToAnalyzer={() => {
                setActiveTab('analyzer');
              }}
            />
          ) : activeTab === 'explorer' ? (
            <ReportExplorerView
              onNavigateToPrecursor={handleInspectPrecursor}
              onNavigateToSite={(_siteId) => {
                setActiveTab('sites');
              }}
              onNavigateToLsr={(_ruleId) => {
                setActiveTab('lsr');
              }}
              onNavigateToAnalyzer={(_report) => {
                setActiveTab('analyzer');
              }}
            />
          ) : (
            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '0.5rem', fontWeight: 600 }}>
                Module Navigation
              </div>
              <button
                onClick={() => setActiveTab('command-center')}
                className="oil-btn oil-btn-primary"
              >
                Return to SIF Command Center
              </button>
            </div>
          )}
        </main>

      {/* Explainable AI Evidence Dossier Modal */}
      {selectedReportId && (
        <EvidenceDossierModal
          report={activeReport}
          onClose={handleCloseReport}
          onUpdateReview={handleUpdateReview}
        />
      )}
    </div>
  );
};

export default App;
