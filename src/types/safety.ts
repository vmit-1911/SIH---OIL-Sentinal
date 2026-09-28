// Domain types for OIL-SIF Precursor Intelligence Platform

export type SifPotentialStatus = 'SIF_POTENTIAL' | 'NON_SIF_POTENTIAL' | 'UNDER_REVIEW';

export type SignalSeverity = 'CRITICAL_SIGNAL' | 'ELEVATED' | 'ATTENTION' | 'NORMAL';

export type LifeSavingRule =
  | 'Energy Isolation'
  | 'Line of Fire'
  | 'Confined Space'
  | 'Working at Height'
  | 'Hot Work'
  | 'Lifting Operations'
  | 'Bypassing Safety Controls'
  | 'Driving Safety'
  | 'Toxic Gas / Chemical Exposure';

export type BarrierType = 'Preventive' | 'Mitigative';

export interface SemanticToken {
  text: string;
  category: 'hazard' | 'energy' | 'barrier' | 'action' | 'consequence';
  explanation: string;
}

export interface ExplainabilityDossier {
  detectedEnergy: string;
  workerExposure: string;
  failedBarrier: string;
  barrierType: BarrierType;
  potentialConsequence: string;
  reasoningNarrative: string;
  tokens: SemanticToken[];
  confidenceScore: number; // 0.0 - 1.0
  confidenceBand: 'HIGH_CONFIDENCE' | 'MODERATE' | 'LOW';
}

export interface HseReviewRecord {
  status: 'HSE_VERIFIED' | 'PENDING_REVIEW' | 'OVERRIDDEN';
  verifiedBy?: string;
  verifiedRole?: string;
  verifiedAt?: string;
  notes?: string;
}

export interface SafetyReport {
  id: string; // e.g. "OIL-UA-2026-0842"
  timestamp: string;
  siteId: string;
  siteName: string;
  operationalArea: 'Assam Asset' | 'Rajasthan Project' | 'KG Offshore Basin' | 'Pipeline Division';
  assetType: 'Drilling Rig' | 'Workover Rig' | 'Gas Gathering Station' | 'Oil Processing Plant';
  reportType: 'Unsafe Act' | 'Unsafe Condition' | 'Near Miss' | 'Minor Event';
  activity: string;
  rawNarrative: string;
  actualOutcome: string;
  potentialConsequence: string;
  sifPotential: SifPotentialStatus;
  lifeSavingRule: LifeSavingRule;
  failedBarrier: string;
  precursorClusterId: string;
  explainability: ExplainabilityDossier;
  hseReview: HseReviewRecord;
}

export interface PrecursorCluster {
  id: string; // e.g. "PREC-04-ENERGY-ISO"
  title: string;
  lifeSavingRule: LifeSavingRule;
  severity: SignalSeverity;
  headlineSummary: string;
  rootCausalMechanisms: string;
  primaryFailedBarrier: string;
  primaryActivity: string;
  reportCount: number;
  assetsInvolved: {
    siteId: string;
    siteName: string;
    reportCount: number;
  }[];
  trendVelocity: string; // e.g. "+40% in 14 days"
  earliestReport: string;
  latestReport: string;
  reportIds: string[];
}

export interface CommandCenterMetrics {
  totalAnalyzed: number;
  sifFlaggedCount: number;
  sifDensityPercent: number;
  activePrecursorClusters: number;
  verifiedByHsePercent: number;
  highRiskAssetsCount: number;
}

// AI Report Analyzer Types
export interface EvidenceItem {
  id: string;
  originalPhrase: string;
  deduction: string;
  category: 'energy' | 'barrier' | 'action' | 'instrumentation' | 'exposure';
}

export interface AnalysisResult {
  reportId: string;
  sifPotential: SifPotentialStatus;
  classificationConfidence: number; // 0.00 - 1.00
  confidenceBand: 'HIGH_CONFIDENCE' | 'MODERATE' | 'LOW';
  lifeSavingRule: LifeSavingRule;
  lsrReasoning: string;
  failedBarrier: string;
  barrierType: BarrierType;
  actualOutcome: string;
  potentialConsequence: string;
  extractedEnergy: string;
  extractedActivity: string;
  extractedExposure: string;
  evidenceItems: EvidenceItem[];
  synthesisEquation: {
    factors: string[];
    result: string;
  };
  relatedPrecursor: {
    id: string;
    title: string;
    observationCount: number;
    assetCount: number;
    failedBarrier: string;
  };
  reviewStatus: 'PENDING_REVIEW' | 'HSE_VERIFIED' | 'OVERRIDDEN' | 'NEEDS_REVIEW';
  reviewNotes?: string;
}

export interface DemoObservationFixture {
  id: string;
  title: string;
  reportType: 'Unsafe Act' | 'Unsafe Condition' | 'Near Miss';
  siteName: string;
  activity: string;
  narrative: string;
  analysisResult: AnalysisResult;
}

// Site & Asset Exposure Types (Phase 5)
export interface SiteAssetExposure {
  siteId: string;
  siteName: string;
  clusterArea: 'Duliajan Operational Hub' | 'Moran Field Operations' | 'Digboi Production Sector' | 'Naharkatiya & Surrounding Wells';
  assetClass: 'Drilling Rig' | 'Workover Rig' | 'Oil Processing Plant' | 'Wellhead Installation' | 'Gas Compression';
  totalObservations: number;
  sifPotentialCount: number;
  nonSifCount: number;
  precursorDensityPercent: number; // e.g. 28.6%
  dominantPrecursorId: string;
  dominantPrecursorTitle: string;
  lifeSavingRule: LifeSavingRule;
  failedBarrier: string;
  trend: 'INCREASING' | 'STABLE' | 'DECREASING';
  connectedReportIds: string[];
  activities: {
    activityName: string;
    count: number;
  }[];
  spatialPosition: {
    gridX: number; // 0-100% relative layout within regional map container
    gridY: number;
  };
}

export interface PrecursorFilterOption {
  id: string;
  title: string;
  rule: LifeSavingRule;
  connectedReportsCount: number;
  affectedAssetsCount: number;
}

export interface ExposureTrendPoint {
  timeLabel: string;
  sifCount: number;
  routineCount: number;
}

// Life-Saving Rule Intelligence Types (Phase 6)
export interface LsrPrecursorConnection {
  id: string;
  title: string;
  severity: SignalSeverity;
  connectedObservations: number;
  failedBarrier: string;
  affectedAssets: string[];
  activities: string[];
}

export interface LsrIntelligenceSummary {
  ruleId: LifeSavingRule;
  ruleName: string;
  statusClassification: 'MOST_OBSERVED' | 'MULTIPLE_PRECURSORS' | 'EMERGING_SIGNAL' | 'LIMITED_EVIDENCE';
  totalConnectedObservations: number;
  sifPotentialObservations: number;
  recurringPrecursorsCount: number;
  affectedAssetsCount: number;
  whyAppearingText: string;
  reportedOutcomeSummary: string;
  potentialConsequenceSummary: string;
  ruleAssociationEvidence: {
    energySource: string;
    activityContext: string;
    barrierEvidence: string;
    exposurePathway: string;
  };
  primaryFailedBarrier: string;
  failedBarrierReportCount: number;
  failedBarrierDescription: string;
  precursors: LsrPrecursorConnection[];
  activities: { activityName: string; count: number }[];
  affectedAssets: { siteId: string; siteName: string; count: number }[];
  trendVelocity: string;
}
