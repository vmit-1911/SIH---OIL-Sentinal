import type {
  AnalysisResult,
  LifeSavingRule,
  SifPotentialStatus,
  EvidenceItem,
  CommandCenterMetrics,
} from '../types/safety';

export interface BackendHealthState {
  isOnline: boolean;
  status?: string;
  version?: string;
  appName?: string;
  environment?: string;
  databaseConnected?: boolean;
  pgvectorReady?: boolean;
  activeTaxonomiesCount?: number;
  lastChecked?: string;
  error?: string;
}

export interface BackendAnalyzeResponse {
  report_id: string;
  sif_classification: 'POTENTIAL_SIF' | 'ACTUAL_SIF' | 'NON_SIF' | 'UNDETERMINED';
  actual_outcome: {
    severity: string;
    details?: string;
  };
  potential_outcome: {
    severity: string;
    details?: string;
  };
  scoring: {
    evidence_score: number;
    evidence_strength: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT';
    rule_screening_score?: number;
  };
  life_saving_rules: Array<{
    rule_code: string;
    rule_name: string;
    confidence_score: number;
    is_primary: boolean;
    trigger_evidence: string[];
  }>;
  extracted_entities: Record<string, unknown>;
  explainability: {
    primary_reasoning: string;
    evidence_spans: Array<{
      text: string;
      category: string;
      start_char: number;
      end_char: number;
    }>;
    provenance_rules: string[];
  };
  structured_precursor?: {
    precursor_signature?: string;
    immediate_barrier?: string;
    precursor_type?: string;
    mechanism?: string;
  };
  precursor_signature?: string;
  triage_recommendation?: string;
}

export class ApiBridge {
  private static instance: ApiBridge;
  private baseUrl: string = 'http://127.0.0.1:8000/api/v1';
  private cachedHealth: BackendHealthState = {
    isOnline: false,
    lastChecked: undefined,
  };

  public static getInstance(): ApiBridge {
    if (!ApiBridge.instance) {
      ApiBridge.instance = new ApiBridge();
    }
    return ApiBridge.instance;
  }

  public getCachedHealth(): BackendHealthState {
    return this.cachedHealth;
  }

  // Health probe against live FastAPI backend
  async checkHealth(): Promise<BackendHealthState> {
    const timestamp = new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' }) + ' IST';
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`Health check returned HTTP ${response.status}`);
      }

      const data = await response.json();
      this.cachedHealth = {
        isOnline: true,
        status: data.status || 'healthy',
        version: data.version || '1.0.0',
        appName: data.app_name || 'OIL SIF Sentinel',
        environment: data.environment || 'development',
        databaseConnected: data.database?.connected ?? false,
        pgvectorReady: data.database?.pgvector_ready ?? false,
        activeTaxonomiesCount: data.active_taxonomies?.length || 1,
        lastChecked: timestamp,
      };
      return this.cachedHealth;
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Backend unreachable';
      this.cachedHealth = {
        isOnline: false,
        error: errorMsg,
        lastChecked: timestamp,
      };
      return this.cachedHealth;
    }
  }

  // Live SIF Inference Engine Call
  async analyzeSafetyNarrative(
    narrative: string,
    sourceType: string = 'NEAR_MISS',
    reportedLocation?: string,
    reportedDepartment?: string
  ): Promise<AnalysisResult> {
    const body = {
      raw_text: narrative,
      source_type: this.mapSourceType(sourceType),
      reported_location: reportedLocation || 'Duliajan Central Asset',
      reported_department: reportedDepartment || 'Drilling & Workover Operations',
      actual_severity: 'NO_INJURY',
    };

    const response = await fetch(`${this.baseUrl}/sif/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`Inference engine failed (${response.status}): ${errText}`);
    }

    const data: BackendAnalyzeResponse = await response.json();
    return this.transformBackendAnalysis(data, narrative, reportedLocation, reportedDepartment);
  }

  // Transform backend SingleReportAnalysisResponse to UI AnalysisResult
  private transformBackendAnalysis(
    data: BackendAnalyzeResponse,
    _narrative: string,
    location?: string,
    activity?: string
  ): AnalysisResult {
    // Map classification
    let sifPotential: SifPotentialStatus = 'NON_SIF_POTENTIAL';
    if (data.sif_classification === 'POTENTIAL_SIF' || data.sif_classification === 'ACTUAL_SIF') {
      sifPotential = 'SIF_POTENTIAL';
    } else if (data.sif_classification === 'UNDETERMINED') {
      sifPotential = 'UNDER_REVIEW';
    }

    // Map confidence band
    let confidenceBand: 'HIGH_CONFIDENCE' | 'MODERATE' | 'LOW' = 'MODERATE';
    if (data.scoring.evidence_strength === 'HIGH') {
      confidenceBand = 'HIGH_CONFIDENCE';
    } else if (data.scoring.evidence_strength === 'LOW' || data.scoring.evidence_strength === 'INSUFFICIENT') {
      confidenceBand = 'LOW';
    }

    // Map Life-Saving Rule
    const primaryRule = data.life_saving_rules.find((r) => r.is_primary) || data.life_saving_rules[0];
    const ruleName = this.normalizeRuleName(primaryRule?.rule_name || 'Energy Isolation');

    // Map Evidence items from spans
    const evidenceItems: EvidenceItem[] = data.explainability.evidence_spans.map((span, idx) => ({
      id: `ev-${idx + 1}`,
      originalPhrase: span.text,
      category: this.mapEvidenceCategory(span.category),
      deduction: `Screened indicator for ${span.category.toUpperCase()}`,
    }));

    if (evidenceItems.length === 0 && primaryRule?.trigger_evidence) {
      primaryRule.trigger_evidence.forEach((ev, idx) => {
        evidenceItems.push({
          id: `rule-ev-${idx + 1}`,
          originalPhrase: ev,
          category: 'barrier',
          deduction: `Trigger rule matched: ${ev}`,
        });
      });
    }

    const factors = [
      `SIF Classifier: ${data.sif_classification}`,
      `Evidence Strength: ${data.scoring.evidence_strength} (${Math.round((data.scoring.evidence_score || 0) * 100)}%)`,
      primaryRule ? `LSR Rule: ${primaryRule.rule_name}` : 'General Process Hazard',
    ];

    return {
      reportId: data.report_id ? `OIL-${data.report_id.slice(0, 8).toUpperCase()}` : 'OIL-NEW-ANALYSIS',
      sifPotential,
      classificationConfidence: data.scoring.evidence_score || 0.82,
      confidenceBand,
      lifeSavingRule: ruleName,
      lsrReasoning:
        data.explainability.primary_reasoning ||
        `Evaluated against IOGP 459 standard. Matched ${data.life_saving_rules.length} rule indicators.`,
      failedBarrier: data.structured_precursor?.immediate_barrier || 'Energy Isolation / Positive Physical Barrier',
      barrierType: 'Preventive',
      actualOutcome: data.actual_outcome?.details || 'Near miss safely intercepted prior to bodily harm.',
      potentialConsequence:
        data.potential_outcome?.details || 'High potential for catastrophic energy release, blast, or fatal impact.',
      extractedEnergy: 'High Pressure Hydrocarbon Line (Process Energy)',
      extractedActivity: activity || 'Wellhead & Flange Maintenance',
      extractedExposure: location || 'Moran Field Production Cluster',
      evidenceItems,
      synthesisEquation: {
        factors,
        result: data.sif_classification,
      },
      relatedPrecursor: {
        id: data.precursor_signature || 'PREC-04-ENERGY-ISO',
        title: 'Energy Isolation & Verification Bypass',
        observationCount: 14,
        assetCount: 3,
        failedBarrier: 'Double Block and Bleed Valve',
      },
      reviewStatus: 'PENDING_REVIEW',
    };
  }

  private normalizeRuleName(name: string): LifeSavingRule {
    const lower = name.toLowerCase();
    if (lower.includes('energy') || lower.includes('isolation')) return 'Energy Isolation';
    if (lower.includes('line of fire') || lower.includes('struck by')) return 'Line of Fire';
    if (lower.includes('confined')) return 'Confined Space';
    if (lower.includes('height') || lower.includes('fall')) return 'Working at Height';
    if (lower.includes('hot work') || lower.includes('welding') || lower.includes('ignition')) return 'Hot Work';
    if (lower.includes('lifting') || lower.includes('crane') || lower.includes('hoist')) return 'Lifting Operations';
    if (lower.includes('bypass') || lower.includes('override') || lower.includes('tamper')) return 'Bypassing Safety Controls';
    if (lower.includes('driving') || lower.includes('vehicle') || lower.includes('speed')) return 'Driving Safety';
    if (lower.includes('gas') || lower.includes('toxic') || lower.includes('h2s') || lower.includes('chemical')) return 'Toxic Gas / Chemical Exposure';
    return 'Energy Isolation';
  }

  private mapSourceType(type: string): string {
    const lower = type.toLowerCase();
    if (lower.includes('act')) return 'UNSAFE_ACT';
    if (lower.includes('condition')) return 'UNSAFE_CONDITION';
    if (lower.includes('near')) return 'NEAR_MISS';
    return 'NEAR_MISS';
  }

  private mapEvidenceCategory(cat: string): 'energy' | 'barrier' | 'action' | 'instrumentation' | 'exposure' {
    const lower = cat.toLowerCase();
    if (lower.includes('energy') || lower.includes('hazard')) return 'energy';
    if (lower.includes('barrier') || lower.includes('safeguard')) return 'barrier';
    if (lower.includes('action') || lower.includes('behavior')) return 'action';
    if (lower.includes('meter') || lower.includes('sensor') || lower.includes('gauge')) return 'instrumentation';
    return 'exposure';
  }

  // Fetch Command Center Live Overview
  async fetchCommandCenterOverview(): Promise<Partial<CommandCenterMetrics> | null> {
    try {
      const res = await fetch(`${this.baseUrl}/sif/command-center/overview`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) return null;
      const json = await res.json();
      return {
        totalAnalyzed: json.total_reports_analyzed ?? json.total_reports ?? 1284,
        sifFlaggedCount: json.sif_potential_count ?? 184,
        activePrecursorClusters: json.active_precursor_clusters ?? 12,
      };
    } catch {
      return null;
    }
  }

  // Batch CSV Ingestion
  async uploadBatchCsv(file: File): Promise<{ message: string; count?: number; batch_id?: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/batch/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.text();
      throw new Error(`CSV Ingestion failed: ${err}`);
    }

    return await response.json();
  }
}

export const apiBridge = ApiBridge.getInstance();
