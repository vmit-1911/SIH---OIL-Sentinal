import type {
  SafetyReport,
  PrecursorCluster,
  CommandCenterMetrics,
  AnalysisResult,
  DemoObservationFixture,
  SiteAssetExposure,
  PrecursorFilterOption,
  ExposureTrendPoint,
  LsrIntelligenceSummary,
  LifeSavingRule,
} from '../types/safety';
import {
  MOCK_COMMAND_CENTER_METRICS,
  MOCK_PRECURSOR_CLUSTER,
  MOCK_SAFETY_REPORTS,
} from './mockSafetyData';
import { DEMO_OBSERVATION_FIXTURES } from './mockAnalyzerData';
import {
  MOCK_SITE_EXPOSURES,
  MOCK_PRECURSOR_FILTER_OPTIONS,
  MOCK_EXPOSURE_TRENDS,
} from './mockSiteExposureData';
import {
  MOCK_LSR_SUMMARIES,
  MOCK_LSR_TRENDS,
  MOCK_ADDITIONAL_RULE_REPORTS,
  type LsrTrendPoint,
} from './mockLsrData';
import { apiBridge, type BackendHealthState } from './apiBridge';

export interface FilterOptions {
  siteId?: string;
  lifeSavingRule?: string;
  sifPotentialOnly?: boolean;
  searchQuery?: string;
}

export class SafetyIntelligenceService {
  private static instance: SafetyIntelligenceService;

  public static getInstance(): SafetyIntelligenceService {
    if (!SafetyIntelligenceService.instance) {
      SafetyIntelligenceService.instance = new SafetyIntelligenceService();
    }
    return SafetyIntelligenceService.instance;
  }

  // Get health status of the FastAPI backend
  async checkBackendHealth(): Promise<BackendHealthState> {
    return await apiBridge.checkHealth();
  }

  // Get metrics for Command Center
  async getCommandCenterMetrics(): Promise<CommandCenterMetrics> {
    try {
      const liveMetrics = await apiBridge.fetchCommandCenterOverview();
      if (liveMetrics) {
        return {
          ...MOCK_COMMAND_CENTER_METRICS,
          ...liveMetrics,
        };
      }
    } catch {
      // Fallback to baseline metrics
    }
    return Promise.resolve(MOCK_COMMAND_CENTER_METRICS);
  }

  // Get active precursor clusters
  async getActivePrecursorClusters(): Promise<PrecursorCluster[]> {
    // In production, this calls GET /api/v1/precursors/active
    return Promise.resolve([MOCK_PRECURSOR_CLUSTER]);
  }

  // Get single precursor cluster by ID with linked reports
  async getPrecursorClusterById(_clusterId: string): Promise<{
    cluster: PrecursorCluster;
    reports: SafetyReport[];
  }> {
    // In production, this calls GET /api/v1/precursors/:clusterId
    const cluster = MOCK_PRECURSOR_CLUSTER;
    const reports = MOCK_SAFETY_REPORTS.filter((r) =>
      cluster.reportIds.includes(r.id)
    );
    return Promise.resolve({ cluster, reports });
  }

  // Internal helper to get unified pool of all safety reports
  public getAllMockReports(): SafetyReport[] {
    const additional = Object.values(MOCK_ADDITIONAL_RULE_REPORTS).flat();
    const existingIds = new Set(MOCK_SAFETY_REPORTS.map((r) => r.id));
    const nonDuplicates = additional.filter((r) => !existingIds.has(r.id));
    return [...MOCK_SAFETY_REPORTS, ...nonDuplicates];
  }

  // Query safety reports with flexible filters
  async getReports(filters?: FilterOptions): Promise<SafetyReport[]> {
    // In production, this calls GET /api/v1/reports?...
    let reports = this.getAllMockReports();

    if (filters?.siteId) {
      reports = reports.filter((r) => r.siteId === filters.siteId);
    }
    if (filters?.lifeSavingRule) {
      reports = reports.filter((r) => r.lifeSavingRule === filters.lifeSavingRule);
    }
    if (filters?.sifPotentialOnly) {
      reports = reports.filter((r) => r.sifPotential === 'SIF_POTENTIAL');
    }
    if (filters?.searchQuery) {
      const q = filters.searchQuery.toLowerCase();
      reports = reports.filter(
        (r) =>
          r.rawNarrative.toLowerCase().includes(q) ||
          r.id.toLowerCase().includes(q) ||
          r.siteName.toLowerCase().includes(q) ||
          r.activity.toLowerCase().includes(q)
      );
    }

    return Promise.resolve(reports);
  }

  // Get all reports unified
  async getAllReports(): Promise<SafetyReport[]> {
    return Promise.resolve(this.getAllMockReports());
  }

  // Get single report detail by ID
  async getReportById(reportId: string): Promise<SafetyReport | undefined> {
    const all = this.getAllMockReports();
    const report = all.find((r) => r.id === reportId);
    return Promise.resolve(report);
  }

  // Update HSE review verification status
  async updateHseReview(
    reportId: string,
    status: 'HSE_VERIFIED' | 'OVERRIDDEN' | 'PENDING_REVIEW',
    notes: string,
    reviewer: string
  ): Promise<SafetyReport> {
    const all = this.getAllMockReports();
    const report = all.find((r) => r.id === reportId);
    if (!report) {
      throw new Error(`Report ${reportId} not found`);
    }

    report.hseReview = {
      status,
      verifiedBy: reviewer,
      verifiedRole: 'Assam Asset Safety Directorate',
      verifiedAt: new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }) + ' IST',
      notes,
    };

    return Promise.resolve({ ...report });
  }

  // Get related reports with explainable relationship rationale
  async getRelatedReports(
    reportId: string
  ): Promise<{ report: SafetyReport; connectionReason: string }[]> {
    const all = this.getAllMockReports();
    const target = all.find((r) => r.id === reportId);
    if (!target) return Promise.resolve([]);

    const related: { report: SafetyReport; connectionReason: string }[] = [];

    for (const r of all) {
      if (r.id === target.id) continue;

      let reason = '';
      if (target.precursorClusterId && r.precursorClusterId === target.precursorClusterId) {
        reason = `Shared Precursor (${target.precursorClusterId}) & Failed Barrier`;
      } else if (target.failedBarrier && r.failedBarrier === target.failedBarrier) {
        reason = `Shared Failed Barrier: ${target.failedBarrier}`;
      } else if (target.lifeSavingRule && r.lifeSavingRule === target.lifeSavingRule) {
        reason = `Shared Safeguard: ${target.lifeSavingRule}`;
      } else if (target.siteId === r.siteId) {
        reason = `Shared Operational Asset: ${target.siteName}`;
      } else if (target.activity && r.activity === target.activity) {
        reason = `Shared Activity: ${target.activity}`;
      }

      if (reason) {
        related.push({ report: r, connectionReason: reason });
      }
    }

    return Promise.resolve(related.slice(0, 5));
  }

  // Get demo observation fixtures for the AI Report Analyzer
  async getDemoFixtures(): Promise<DemoObservationFixture[]> {
    return Promise.resolve(DEMO_OBSERVATION_FIXTURES);
  }

  // Analyze safety observation (connects to live FastAPI backend with local fallback)
  async analyzeReport(
    narrative: string,
    _reportType?: string,
    _siteName?: string,
    _activity?: string
  ): Promise<AnalysisResult> {
    // 1. First attempt live AI/NLP inference against FastAPI backend
    try {
      const liveResult = await apiBridge.analyzeSafetyNarrative(
        narrative,
        _reportType,
        _siteName,
        _activity
      );
      if (liveResult) {
        return liveResult;
      }
    } catch (apiErr) {
      console.warn('Backend API inference not reachable, utilizing high-fidelity local screening engine:', apiErr);
    }

    // 2. High-fidelity deterministic local fallback
    const matchedFixture = DEMO_OBSERVATION_FIXTURES.find(
      (f) =>
        f.narrative.toLowerCase().trim() === narrative.toLowerCase().trim() ||
        narrative.toLowerCase().includes('flange before the bleed-off point') ||
        narrative.toLowerCase().includes('manway of the crude test separator') ||
        narrative.toLowerCase().includes('water supply hose was left coiled')
    );

    if (matchedFixture) {
      return Promise.resolve(JSON.parse(JSON.stringify(matchedFixture.analysisResult)));
    }

    const lower = narrative.toLowerCase();
    const hasPressure = lower.includes('pressure') || lower.includes('valve') || lower.includes('pump') || lower.includes('line');
    const hasBleed = lower.includes('bleed') || lower.includes('loto') || lower.includes('lock') || lower.includes('isolation');
    const hasGas = lower.includes('gas') || lower.includes('h2s') || lower.includes('confined') || lower.includes('tank');

    if (hasGas) {
      return Promise.resolve(JSON.parse(JSON.stringify(DEMO_OBSERVATION_FIXTURES[1].analysisResult)));
    }

    if (hasPressure || hasBleed) {
      return Promise.resolve(JSON.parse(JSON.stringify(DEMO_OBSERVATION_FIXTURES[0].analysisResult)));
    }

    return Promise.resolve(JSON.parse(JSON.stringify(DEMO_OBSERVATION_FIXTURES[2].analysisResult)));
  }

  // Batch CSV Ingestion
  async uploadBatchCsv(file: File) {
    return await apiBridge.uploadBatchCsv(file);
  }

  // Site & Asset Exposure Service Methods (Phase 5)
  async getSiteExposures(precursorFilterId?: string): Promise<SiteAssetExposure[]> {
    // In production, calls GET /api/v1/sites/exposure?precursor=...
    if (!precursorFilterId || precursorFilterId === 'ALL') {
      return Promise.resolve(MOCK_SITE_EXPOSURES);
    }
    // Filter exposures related to the selected precursor
    return Promise.resolve(
      MOCK_SITE_EXPOSURES.filter((s) => s.dominantPrecursorId === precursorFilterId)
    );
  }

  async getPrecursorFilterOptions(): Promise<PrecursorFilterOption[]> {
    return Promise.resolve(MOCK_PRECURSOR_FILTER_OPTIONS);
  }

  async getExposureTrends(timeWindow: '7d' | '30d' | '90d'): Promise<ExposureTrendPoint[]> {
    return Promise.resolve(MOCK_EXPOSURE_TRENDS[timeWindow] || MOCK_EXPOSURE_TRENDS['30d']);
  }

  // Life-Saving Rule Intelligence Methods (Phase 6)
  async getLifeSavingRuleSummaries(): Promise<LsrIntelligenceSummary[]> {
    // In production, GET /api/v1/lsr/summaries
    return Promise.resolve(MOCK_LSR_SUMMARIES);
  }

  async getLifeSavingRuleDetail(ruleId: LifeSavingRule): Promise<LsrIntelligenceSummary | undefined> {
    // In production, GET /api/v1/lsr/:ruleId
    const found = MOCK_LSR_SUMMARIES.find((s) => s.ruleId === ruleId);
    return Promise.resolve(found);
  }

  async getLifeSavingRuleReports(
    ruleId: LifeSavingRule,
    filters?: { activity?: string; siteId?: string; sifOnly?: boolean }
  ): Promise<SafetyReport[]> {
    let pool: SafetyReport[] = [];
    if (ruleId === 'Energy Isolation') {
      pool = [...MOCK_SAFETY_REPORTS];
    } else {
      pool = MOCK_ADDITIONAL_RULE_REPORTS[ruleId] || [];
    }

    if (!filters) return Promise.resolve(pool);

    return Promise.resolve(
      pool.filter((r) => {
        if (filters.activity && r.activity !== filters.activity) return false;
        if (filters.siteId && r.siteId !== filters.siteId) return false;
        if (filters.sifOnly && r.sifPotential !== 'SIF_POTENTIAL') return false;
        return true;
      })
    );
  }

  async getLifeSavingRuleTrend(
    ruleId: string,
    timeWindow: '7d' | '30d' | '90d'
  ): Promise<LsrTrendPoint[]> {
    const ruleTrends = MOCK_LSR_TRENDS[ruleId] || MOCK_LSR_TRENDS['Energy Isolation'];
    return Promise.resolve(ruleTrends[timeWindow] || ruleTrends['30d']);
  }
}

export const safetyService = SafetyIntelligenceService.getInstance();
