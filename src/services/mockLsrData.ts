import type { LsrIntelligenceSummary } from '../types/safety';

export const MOCK_LSR_SUMMARIES: LsrIntelligenceSummary[] = [
  {
    ruleId: 'Energy Isolation',
    ruleName: 'Energy Isolation',
    statusClassification: 'MOST_OBSERVED',
    totalConnectedObservations: 42,
    sifPotentialObservations: 11,
    recurringPrecursorsCount: 2,
    affectedAssetsCount: 4,
    whyAppearingText:
      'Observations repeatedly document technicians loosening fluid line flanges, breaking rotary unions, or adjusting valve packings on high-pressure lines without independent zero-energy verification or physical LOTO padlocks.',
    reportedOutcomeSummary: 'No injury; minor slurry spray or trapped gas whistling out.',
    potentialConsequenceSummary:
      'Catastrophic high-velocity fluid injection, metal flange projectile impact, or pressurized hose whip resulting in fatal trauma.',
    ruleAssociationEvidence: {
      energySource: 'High-pressure hydraulic drilling mud (3,500 PSI) & pressurized gas',
      activityContext: 'Mud pump fluid end overhaul, wellhead valve maintenance, pipeline pigging',
      barrierEvidence: 'Omission of double block & bleed; relying on uncalibrated analog gauges',
      exposurePathway: 'Worker positioned directly in line of fire over flange face during line break',
    },
    primaryFailedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
    failedBarrierReportCount: 7,
    failedBarrierDescription:
      'Primary preventive barrier repeatedly bypassed or missing independent verification before breaking containment.',
    precursors: [
      {
        id: 'PREC-04-ENERGY-ISO',
        title: 'High-Pressure Energy Isolation & Zero-Verification Bypass',
        severity: 'CRITICAL_SIGNAL',
        connectedObservations: 7,
        failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
        affectedAssets: ['Duliajan Drill Rig #14', 'Moran Workover #07', 'Digboi OCS-2', 'Naharkatiya #11'],
        activities: ['Mud pump fluid end overhaul', 'Rotary hose hammer union break', 'Pig receiver unbolting'],
      },
      {
        id: 'PREC-05-ELECTRICAL-LOTO',
        title: 'Incomplete Electrical MCC Breaker Lockout',
        severity: 'ELEVATED',
        connectedObservations: 4,
        failedBarrier: 'Padlock Lockout at Main Motor Control Center (MCC)',
        affectedAssets: ['Moran Workover #07', 'Digboi OCS-2'],
        activities: ['Mud tank agitator drive inspection', 'Transfer pump motor servicing'],
      },
    ],
    activities: [
      { activityName: 'Mud pump fluid end overhaul', count: 12 },
      { activityName: 'Test separator manifold bolting', count: 11 },
      { activityName: 'Pipeline pig launcher/receiver operations', count: 9 },
      { activityName: 'Wellhead Christmas tree valve maintenance', count: 6 },
      { activityName: 'Rotary hose connection break', count: 4 },
    ],
    affectedAssets: [
      { siteId: 'site-duliajan-14', siteName: 'Duliajan Deep Drill Rig #14', count: 2 },
      { siteId: 'site-moran-07', siteName: 'Moran Workover Rig #07', count: 2 },
      { siteId: 'site-digboi-ocs2', siteName: 'Digboi Oil Collection Station (OCS-2)', count: 2 },
      { siteId: 'site-nhk-11', siteName: 'Naharkatiya Wellhead #11', count: 1 },
    ],
    trendVelocity: '+40% frequency in 14 days',
  },
  {
    ruleId: 'Line of Fire',
    ruleName: 'Line of Fire',
    statusClassification: 'MULTIPLE_PRECURSORS',
    totalConnectedObservations: 28,
    sifPotentialObservations: 5,
    recurringPrecursorsCount: 1,
    affectedAssetsCount: 3,
    whyAppearingText:
      'Personnel standing inside winch line bights under tension, in the rotational arc of rotary tables, or within the swing trajectory of suspended drill tubulars.',
    reportedOutcomeSummary: 'Near miss; floorhand stepped back before cable snap or crane hook swing.',
    potentialConsequenceSummary:
      'Fatal blunt-force cranial or thoracic impact from tensioned wireline recoil or suspended tubular strike.',
    ruleAssociationEvidence: {
      energySource: 'Mechanically tensioned wire rope & suspended tubular kinetic mass',
      activityContext: 'Tripping drill pipe out of hole & yard crane offloading',
      barrierEvidence: 'Exclusion zone barricades breached; personnel inside winch bight',
      exposurePathway: 'Worker standing in direct line of recoil tension',
    },
    primaryFailedBarrier: 'Exclusion Zone Barricading & Standoff Protocols',
    failedBarrierReportCount: 5,
    failedBarrierDescription:
      'Physical demarcation and personnel exclusion perimeter around active drawworks line not maintained.',
    precursors: [
      {
        id: 'PREC-02-LINE-FIRE',
        title: 'Line of Fire During Heavy Tubular Handling',
        severity: 'CRITICAL_SIGNAL',
        connectedObservations: 5,
        failedBarrier: 'Exclusion Zone Barricading & Standoff Protocols',
        affectedAssets: ['Duliajan Drill Rig #14', 'Moran Workover Yard', 'Moran Rig #07'],
        activities: ['Drill string tripping', 'Tubular casing loading onto flatbeds'],
      },
    ],
    activities: [
      { activityName: 'Drill string pipe tripping', count: 15 },
      { activityName: 'Yard casing offloading', count: 8 },
      { activityName: 'Winch hoist positioning', count: 5 },
    ],
    affectedAssets: [
      { siteId: 'site-duliajan-14', siteName: 'Duliajan Deep Drill Rig #14', count: 2 },
      { siteId: 'site-moran-yard', siteName: 'Moran Central Workover Yard', count: 2 },
      { siteId: 'site-moran-07', siteName: 'Moran Workover Rig #07', count: 1 },
    ],
    trendVelocity: '+15% frequency in 30 days',
  },
  {
    ruleId: 'Confined Space',
    ruleName: 'Confined Space',
    statusClassification: 'MULTIPLE_PRECURSORS',
    totalConnectedObservations: 18,
    sifPotentialObservations: 4,
    recurringPrecursorsCount: 1,
    affectedAssetsCount: 2,
    whyAppearingText:
      'Personnel entering crude oil separator vessels and compressor scrubbers with expired 4-hour atmospheric tests, without continuous 4-gas monitors, and with no standby observer.',
    reportedOutcomeSummary: 'Worker felt light-headed and climbed back out unassisted.',
    potentialConsequenceSummary:
      'Rapid toxic H2S incapacitation or oxygen-deficient asphyxiation leading to fatal respiratory arrest within 90 seconds.',
    ruleAssociationEvidence: {
      energySource: 'Toxic hydrogen sulfide (H2S) & oxygen-depleted hydrocarbon vapor',
      activityContext: 'Internal vessel wash, sludge baffle inspection',
      barrierEvidence: 'Continuous gas detection omitted; standby rescue guardian absent',
      exposurePathway: 'Whole-body entry through manway hatch into unventilated chamber',
    },
    primaryFailedBarrier: 'Continuous Atmospheric Gas Testing & Dedicated Standby Observer',
    failedBarrierReportCount: 4,
    failedBarrierDescription:
      'Dual failure: real-time gas monitoring omitted and emergency standby observer missing at hatch.',
    precursors: [
      {
        id: 'PREC-07-CONFINED-SPACE',
        title: 'Confined Space Entry Without Live Gas Verification',
        severity: 'CRITICAL_SIGNAL',
        connectedObservations: 4,
        failedBarrier: 'Continuous Atmospheric Gas Testing & Dedicated Standby Observer',
        affectedAssets: ['Digboi OCS-2', 'Gas Compression Station #03'],
        activities: ['Test separator internal wash', 'Scrubber vessel entry'],
      },
    ],
    activities: [
      { activityName: 'Test separator internal wash', count: 9 },
      { activityName: 'Compressor scrubber cleaning', count: 5 },
      { activityName: 'Mud tank desander entry', count: 4 },
    ],
    affectedAssets: [
      { siteId: 'site-digboi-ocs2', siteName: 'Digboi Oil Collection Station (OCS-2)', count: 2 },
      { siteId: 'site-duliajan-gcs3', siteName: 'Gas Compression Station #03', count: 2 },
    ],
    trendVelocity: 'Stable (+0% in 14 days)',
  },
  {
    ruleId: 'Working at Height',
    ruleName: 'Working at Height',
    statusClassification: 'EMERGING_SIGNAL',
    totalConnectedObservations: 12,
    sifPotentialObservations: 2,
    recurringPrecursorsCount: 1,
    affectedAssetsCount: 2,
    whyAppearingText:
      'Derrickmen working on monkey board 24 meters above rig floor observed with single lanyard unclipped before connecting secondary hook during pipe latching.',
    reportedOutcomeSummary: 'Floorhand tripped on monkey board grating and caught balance on handrail.',
    potentialConsequenceSummary:
      'Unrestrained 24-meter free fall from mast derrick to drill floor with fatal impact.',
    ruleAssociationEvidence: {
      energySource: 'Gravitational potential energy (24-meter elevation)',
      activityContext: 'Monkey board derrick operations during drill pipe latching',
      barrierEvidence: '100% dual-lanyard tie-off rule breached during transition',
      exposurePathway: 'Worker untethered above open rig floor aperture',
    },
    primaryFailedBarrier: '100% Dual-Lanyard Tie-Off Protocol',
    failedBarrierReportCount: 2,
    failedBarrierDescription:
      'Derrick workers unhooking primary lanyard before secondary anchor point is secured.',
    precursors: [
      {
        id: 'PREC-09-WORKING-HEIGHT',
        title: 'Derrick Working at Height 100% Tie-Off',
        severity: 'ELEVATED',
        connectedObservations: 2,
        failedBarrier: '100% Dual-Lanyard Tie-Off Protocol',
        affectedAssets: ['Duliajan Drill Rig #14', 'Moran Workover #07'],
        activities: ['Monkey board pipe racking', 'Derrick ladder climbing'],
      },
    ],
    activities: [
      { activityName: 'Monkey board pipe racking', count: 7 },
      { activityName: 'Substructure ladder climbing', count: 3 },
      { activityName: 'Crown block grease inspection', count: 2 },
    ],
    affectedAssets: [
      { siteId: 'site-duliajan-14', siteName: 'Duliajan Deep Drill Rig #14', count: 1 },
      { siteId: 'site-moran-07', siteName: 'Moran Workover Rig #07', count: 1 },
    ],
    trendVelocity: 'Emerging (2 observations in 14 days)',
  },
  {
    ruleId: 'Hot Work',
    ruleName: 'Hot Work',
    statusClassification: 'EMERGING_SIGNAL',
    totalConnectedObservations: 6,
    sifPotentialObservations: 1,
    recurringPrecursorsCount: 0,
    affectedAssetsCount: 1,
    whyAppearingText:
      'Oxy-acetylene cutting torch ignited 8 meters from crude oil sample point before combustible LEL gas test was repeated following lunch break.',
    reportedOutcomeSummary: 'Fire watch halted work immediately; zero spark spread.',
    potentialConsequenceSummary:
      'Hydrocarbon vapor cloud ignition leading to flash fire or vessel rupture.',
    ruleAssociationEvidence: {
      energySource: 'Thermal ignition source (cutting torch) near flammable hydrocarbon vapors',
      activityContext: 'Structural deck grating hot cutting near manifold',
      barrierEvidence: 'LEL gas test not re-verified following 1-hour work interruption',
      exposurePathway: 'Open flame within 10 meters of active oil sampling line',
    },
    primaryFailedBarrier: 'Continuous Combustible LEL Gas Monitoring within 15m Radius',
    failedBarrierReportCount: 1,
    failedBarrierDescription:
      'Gas monitoring not re-executed following lunch break work pause.',
    precursors: [],
    activities: [
      { activityName: 'Grating torch cutting', count: 4 },
      { activityName: 'Pipe support welding', count: 2 },
    ],
    affectedAssets: [
      { siteId: 'site-digboi-ocs2', siteName: 'Digboi Oil Collection Station (OCS-2)', count: 1 },
    ],
    trendVelocity: '1 observation in 30 days',
  },
  {
    ruleId: 'Bypassing Safety Controls',
    ruleName: 'Bypassing Safety Controls',
    statusClassification: 'LIMITED_EVIDENCE',
    totalConnectedObservations: 4,
    sifPotentialObservations: 0,
    recurringPrecursorsCount: 0,
    affectedAssetsCount: 1,
    whyAppearingText:
      'High-vibration sensor jumpered on water cooling pump during maintenance; no recurring SIF precursor pattern established for the selected period.',
    reportedOutcomeSummary: 'Pump inspected by shift lead and temporary jumper removed.',
    potentialConsequenceSummary:
      'Cooling pump mechanical seal failure; low fatal potential.',
    ruleAssociationEvidence: {
      energySource: 'Mechanical vibration / low-pressure auxiliary cooling water',
      activityContext: 'Pump vibration sensor troubleshooting',
      barrierEvidence: 'Sensor bypass not logged on central override register',
      exposurePathway: 'Auxiliary cooling line only; no hydrocarbon or high pressure',
    },
    primaryFailedBarrier: 'Formal Safety Critical Element Bypass Authorization',
    failedBarrierReportCount: 0,
    failedBarrierDescription:
      'Administrative override permit not signed by maintenance engineer.',
    precursors: [],
    activities: [
      { activityName: 'Auxiliary sensor maintenance', count: 3 },
      { activityName: 'Alarm panel troubleshooting', count: 1 },
    ],
    affectedAssets: [
      { siteId: 'site-duliajan-gcs3', siteName: 'Gas Compression Station #03', count: 1 },
    ],
    trendVelocity: 'Limited evidence (no recurring SIF pattern)',
  },
];

export interface LsrTrendPoint {
  timeLabel: string;
  totalConnected: number;
  sifPotential: number;
}

export const MOCK_LSR_TRENDS: Record<string, Record<'7d' | '30d' | '90d', LsrTrendPoint[]>> = {
  'Energy Isolation': {
    '7d': [
      { timeLabel: 'Sep 16', totalConnected: 4, sifPotential: 1 },
      { timeLabel: 'Sep 17', totalConnected: 6, sifPotential: 2 },
      { timeLabel: 'Sep 18', totalConnected: 7, sifPotential: 2 },
      { timeLabel: 'Sep 19', totalConnected: 5, sifPotential: 1 },
      { timeLabel: 'Sep 20', totalConnected: 8, sifPotential: 2 },
      { timeLabel: 'Sep 21', totalConnected: 6, sifPotential: 1 },
      { timeLabel: 'Sep 22', totalConnected: 6, sifPotential: 2 },
    ],
    '30d': [
      { timeLabel: 'Aug 25 - Aug 31', totalConnected: 8, sifPotential: 2 },
      { timeLabel: 'Sep 01 - Sep 07', totalConnected: 10, sifPotential: 2 },
      { timeLabel: 'Sep 08 - Sep 14', totalConnected: 11, sifPotential: 3 },
      { timeLabel: 'Sep 15 - Sep 22', totalConnected: 13, sifPotential: 4 },
    ],
    '90d': [
      { timeLabel: 'Jul 2026', totalConnected: 24, sifPotential: 5 },
      { timeLabel: 'Aug 2026', totalConnected: 35, sifPotential: 8 },
      { timeLabel: 'Sep 2026', totalConnected: 42, sifPotential: 11 },
    ],
  },
  'Line of Fire': {
    '7d': [
      { timeLabel: 'Sep 16', totalConnected: 3, sifPotential: 1 },
      { timeLabel: 'Sep 17', totalConnected: 4, sifPotential: 1 },
      { timeLabel: 'Sep 18', totalConnected: 3, sifPotential: 0 },
      { timeLabel: 'Sep 19', totalConnected: 5, sifPotential: 1 },
      { timeLabel: 'Sep 20', totalConnected: 4, sifPotential: 1 },
      { timeLabel: 'Sep 21', totalConnected: 5, sifPotential: 1 },
      { timeLabel: 'Sep 22', totalConnected: 4, sifPotential: 0 },
    ],
    '30d': [
      { timeLabel: 'Aug 25 - Aug 31', totalConnected: 6, sifPotential: 1 },
      { timeLabel: 'Sep 01 - Sep 07', totalConnected: 7, sifPotential: 1 },
      { timeLabel: 'Sep 08 - Sep 14', totalConnected: 7, sifPotential: 1 },
      { timeLabel: 'Sep 15 - Sep 22', totalConnected: 8, sifPotential: 2 },
    ],
    '90d': [
      { timeLabel: 'Jul 2026', totalConnected: 18, sifPotential: 3 },
      { timeLabel: 'Aug 2026', totalConnected: 22, sifPotential: 4 },
      { timeLabel: 'Sep 2026', totalConnected: 28, sifPotential: 5 },
    ],
  },
  'Confined Space': {
    '7d': [
      { timeLabel: 'Sep 16', totalConnected: 2, sifPotential: 0 },
      { timeLabel: 'Sep 17', totalConnected: 2, sifPotential: 1 },
      { timeLabel: 'Sep 18', totalConnected: 3, sifPotential: 1 },
      { timeLabel: 'Sep 19', totalConnected: 2, sifPotential: 0 },
      { timeLabel: 'Sep 20', totalConnected: 3, sifPotential: 1 },
      { timeLabel: 'Sep 21', totalConnected: 3, sifPotential: 1 },
      { timeLabel: 'Sep 22', totalConnected: 3, sifPotential: 0 },
    ],
    '30d': [
      { timeLabel: 'Aug 25 - Aug 31', totalConnected: 4, sifPotential: 1 },
      { timeLabel: 'Sep 01 - Sep 07', totalConnected: 4, sifPotential: 1 },
      { timeLabel: 'Sep 08 - Sep 14', totalConnected: 5, sifPotential: 1 },
      { timeLabel: 'Sep 15 - Sep 22', totalConnected: 5, sifPotential: 1 },
    ],
    '90d': [
      { timeLabel: 'Jul 2026', totalConnected: 12, sifPotential: 2 },
      { timeLabel: 'Aug 2026', totalConnected: 15, sifPotential: 3 },
      { timeLabel: 'Sep 2026', totalConnected: 18, sifPotential: 4 },
    ],
  },
  'Working at Height': {
    '7d': [
      { timeLabel: 'Sep 16', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 17', totalConnected: 2, sifPotential: 0 },
      { timeLabel: 'Sep 18', totalConnected: 1, sifPotential: 1 },
      { timeLabel: 'Sep 19', totalConnected: 2, sifPotential: 0 },
      { timeLabel: 'Sep 20', totalConnected: 2, sifPotential: 1 },
      { timeLabel: 'Sep 21', totalConnected: 2, sifPotential: 0 },
      { timeLabel: 'Sep 22', totalConnected: 2, sifPotential: 0 },
    ],
    '30d': [
      { timeLabel: 'Aug 25 - Aug 31', totalConnected: 3, sifPotential: 0 },
      { timeLabel: 'Sep 01 - Sep 07', totalConnected: 3, sifPotential: 1 },
      { timeLabel: 'Sep 08 - Sep 14', totalConnected: 3, sifPotential: 0 },
      { timeLabel: 'Sep 15 - Sep 22', totalConnected: 3, sifPotential: 1 },
    ],
    '90d': [
      { timeLabel: 'Jul 2026', totalConnected: 8, sifPotential: 1 },
      { timeLabel: 'Aug 2026', totalConnected: 10, sifPotential: 1 },
      { timeLabel: 'Sep 2026', totalConnected: 12, sifPotential: 2 },
    ],
  },
  'Hot Work': {
    '7d': [
      { timeLabel: 'Sep 16', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 17', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 18', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 19', totalConnected: 1, sifPotential: 1 },
      { timeLabel: 'Sep 20', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 21', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 22', totalConnected: 0, sifPotential: 0 },
    ],
    '30d': [
      { timeLabel: 'Aug 25 - Aug 31', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 01 - Sep 07', totalConnected: 2, sifPotential: 0 },
      { timeLabel: 'Sep 08 - Sep 14', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 15 - Sep 22', totalConnected: 2, sifPotential: 1 },
    ],
    '90d': [
      { timeLabel: 'Jul 2026', totalConnected: 4, sifPotential: 0 },
      { timeLabel: 'Aug 2026', totalConnected: 5, sifPotential: 0 },
      { timeLabel: 'Sep 2026', totalConnected: 6, sifPotential: 1 },
    ],
  },
  'Bypassing Safety Controls': {
    '7d': [
      { timeLabel: 'Sep 16', totalConnected: 0, sifPotential: 0 },
      { timeLabel: 'Sep 17', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 18', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 19', totalConnected: 0, sifPotential: 0 },
      { timeLabel: 'Sep 20', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 21', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 22', totalConnected: 0, sifPotential: 0 },
    ],
    '30d': [
      { timeLabel: 'Aug 25 - Aug 31', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 01 - Sep 07', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 08 - Sep 14', totalConnected: 1, sifPotential: 0 },
      { timeLabel: 'Sep 15 - Sep 22', totalConnected: 1, sifPotential: 0 },
    ],
    '90d': [
      { timeLabel: 'Jul 2026', totalConnected: 3, sifPotential: 0 },
      { timeLabel: 'Aug 2026', totalConnected: 3, sifPotential: 0 },
      { timeLabel: 'Sep 2026', totalConnected: 4, sifPotential: 0 },
    ],
  },
};

// Additional representative reports for non-Energy-Isolation rules
export const MOCK_ADDITIONAL_RULE_REPORTS: Record<string, import('../types/safety').SafetyReport[]> = {
  'Line of Fire': [
    {
      id: 'OIL-NM-2026-0912',
      timestamp: '2026-09-21 14:20 IST',
      siteId: 'site-duliajan-14',
      siteName: 'Duliajan Deep Drill Rig #14',
      operationalArea: 'Assam Asset',
      assetType: 'Drilling Rig',
      reportType: 'Near Miss',
      activity: 'Drill string pipe tripping',
      rawNarrative:
        'During drill string tripping at Rig 14, floorhand stood inside the bight of the high-tension tugger winch line while pulling elevators. Tugger winch shuddered violently under shock load. Supervisor yelled and worker jumped backward right as the cable whiplashed across grating.',
      actualOutcome: 'Near miss; floorhand stepped back in time with no physical contact.',
      potentialConsequence:
        'Cable snap or high-tension wireline recoil causing fatal blunt-force cranial or thoracic trauma.',
      sifPotential: 'SIF_POTENTIAL',
      lifeSavingRule: 'Line of Fire',
      failedBarrier: 'Exclusion Zone Barricading & Standoff Protocols',
      precursorClusterId: 'PREC-02-LINE-FIRE',
      explainability: {
        detectedEnergy: 'High-tension mechanical wireline stored kinetic energy',
        workerExposure: 'Worker positioned directly inside cable recoil bight',
        failedBarrier: 'Winch operating exclusion zone not demarcated or enforced',
        barrierType: 'Preventive',
        potentialConsequence: 'Cable whiplash projectile strike with fatal impact severity',
        reasoningNarrative:
          'Standing in the bight of an active winch line under load is a primary Line of Fire violation. High tension line failure creates lethal projectile force.',
        tokens: [
          { text: 'inside the bight of the high-tension tugger winch line', category: 'action', explanation: 'Direct line of fire exposure' },
          { text: 'cable whiplashed across grating', category: 'consequence', explanation: 'High energy recoil trajectory' },
        ],
        confidenceScore: 0.94,
        confidenceBand: 'HIGH_CONFIDENCE',
      },
      hseReview: {
        status: 'HSE_VERIFIED',
        verifiedBy: 'D. Borah, HSE Lead Superintendent',
        verifiedRole: 'Assam Asset Safety Directorate',
        verifiedAt: '2026-09-21 17:30 IST',
        notes: 'Confirmed SIF precursor. Winch line exclusion zone markings repainted on rig floor.',
      },
    },
    {
      id: 'OIL-UA-2026-0919',
      timestamp: '2026-09-19 11:10 IST',
      siteId: 'site-moran-yard',
      siteName: 'Moran Central Workover Yard',
      operationalArea: 'Assam Asset',
      assetType: 'Workover Rig',
      reportType: 'Unsafe Act',
      activity: 'Yard casing offloading',
      rawNarrative:
        'Mobile crane operator slewed 3 bundles of 7-inch production casing directly over transport trailer cab while truck driver was sitting inside cab filling dispatch paperwork. Tag lines were not used to control load swing.',
      actualOutcome: 'Tubulars set down safely without impact.',
      potentialConsequence:
        'Sling failure or load drop crushing truck cab with fatal crush trauma to driver.',
      sifPotential: 'SIF_POTENTIAL',
      lifeSavingRule: 'Line of Fire',
      failedBarrier: 'Exclusion Zone Barricading & Standoff Protocols',
      precursorClusterId: 'PREC-02-LINE-FIRE',
      explainability: {
        detectedEnergy: 'Suspended load gravitational kinetic energy (4.2 metric tons)',
        workerExposure: 'Occupied vehicle directly below crane swing radius',
        failedBarrier: 'Crane lift exclusion perimeter not cleared before slewing',
        barrierType: 'Preventive',
        potentialConsequence: 'Crush trauma from suspended tubular release',
        reasoningNarrative:
          'Slewing suspended heavy tubular bundles over occupied vehicle cabins is a direct violation of Line of Fire and Lifting Operations safeguards.',
        tokens: [
          { text: 'slewed 3 bundles of 7-inch production casing directly over cab', category: 'action', explanation: 'Suspended load above human occupancy' },
        ],
        confidenceScore: 0.91,
        confidenceBand: 'HIGH_CONFIDENCE',
      },
      hseReview: {
        status: 'HSE_VERIFIED',
        verifiedBy: 'R. K. Saikia, Field Safety Officer',
        verifiedRole: 'Moran Workover Division',
        verifiedAt: '2026-09-19 15:45 IST',
        notes: 'SIF precursor verified. Yard lift permits halted until exclusion zone barrier protocol refreshed.',
      },
    },
  ],
  'Confined Space': [
    {
      id: 'OIL-UA-2026-0771',
      timestamp: '2026-09-18 10:45 IST',
      siteId: 'site-digboi-ocs2',
      siteName: 'Digboi Oil Collection Station (OCS-2)',
      operationalArea: 'Assam Asset',
      assetType: 'Oil Processing Plant',
      reportType: 'Unsafe Act',
      activity: 'Test separator internal wash',
      rawNarrative:
        'Contractor entered No. 2 Test Separator through bottom manway hatch to clean residual sludge. Gas test certificate was issued at 06:00 AM (4.5 hours prior). Continuous multi-gas monitor was left on outside platform. No dedicated standby observer stationed at entry hatch.',
      actualOutcome: 'Worker experienced dizziness after 4 minutes and exited vessel unassisted.',
      potentialConsequence:
        'Toxic H2S pocket release or oxygen deficiency causing sudden loss of consciousness and fatal asphyxiation.',
      sifPotential: 'SIF_POTENTIAL',
      lifeSavingRule: 'Confined Space',
      failedBarrier: 'Continuous Atmospheric Gas Testing & Dedicated Standby Observer',
      precursorClusterId: 'PREC-07-CONFINED-SPACE',
      explainability: {
        detectedEnergy: 'Toxic chemical hazard (H2S gas) & asphyxiant atmosphere',
        workerExposure: 'Full enclosed entry into unventilated separator vessel',
        failedBarrier: 'No continuous gas detector on entrant; standby observer absent',
        barrierType: 'Preventive',
        potentialConsequence: 'Rapid fatal incapacitation from acute H2S exposure',
        reasoningNarrative:
          'Entering hydrocarbon vessels with stale atmospheric tests and no real-time gas monitoring is the textbook precursor for oilfield confined space fatalities.',
        tokens: [
          { text: 'Gas test certificate was issued 4.5 hours prior', category: 'barrier', explanation: 'Expired atmospheric verification' },
          { text: 'No dedicated standby observer', category: 'barrier', explanation: 'Absence of secondary life-safety barrier' },
        ],
        confidenceScore: 0.95,
        confidenceBand: 'HIGH_CONFIDENCE',
      },
      hseReview: {
        status: 'HSE_VERIFIED',
        verifiedBy: 'M. Neog, Process Safety Engineer',
        verifiedRole: 'Digboi Production Directorate',
        verifiedAt: '2026-09-18 16:00 IST',
        notes: 'Critical SIF precursor. Immediate shut-in of cleaning permit until entry controls re-certified.',
      },
    },
  ],
  'Working at Height': [
    {
      id: 'OIL-UA-2026-0611',
      timestamp: '2026-09-16 15:30 IST',
      siteId: 'site-duliajan-14',
      siteName: 'Duliajan Deep Drill Rig #14',
      operationalArea: 'Assam Asset',
      assetType: 'Drilling Rig',
      reportType: 'Unsafe Act',
      activity: 'Monkey board pipe racking',
      rawNarrative:
        'Derrickman working on monkey board at 24m elevation unclipped primary safety harness lanyard to reach a sticking drill collar latch before securing his secondary lanyard to the mast inertia reel line. He slipped on oily grating but grabbed the handrail.',
      actualOutcome: 'Worker caught himself on handrail; no fall occurred.',
      potentialConsequence:
        'Free fall of 24 meters to drill floor or rotary table resulting in fatal traumatic impact.',
      sifPotential: 'SIF_POTENTIAL',
      lifeSavingRule: 'Working at Height',
      failedBarrier: '100% Dual-Lanyard Tie-Off Protocol',
      precursorClusterId: 'PREC-09-WORKING-HEIGHT',
      explainability: {
        detectedEnergy: 'Gravitational potential energy at 24-meter height',
        workerExposure: 'Worker totally untethered at elevation above open rig floor',
        failedBarrier: '100% tie-off protocol breached during pipe transition',
        barrierType: 'Preventive',
        potentialConsequence: 'Fatal fall from height onto steel drill floor',
        reasoningNarrative:
          'Unclipping both lanyards even momentarily at 24 meters height removes the only physical barrier preventing fatal fall.',
        tokens: [
          { text: 'unclipped primary safety harness lanyard before securing secondary', category: 'action', explanation: 'Zero fall arrest protection' },
        ],
        confidenceScore: 0.93,
        confidenceBand: 'HIGH_CONFIDENCE',
      },
      hseReview: {
        status: 'HSE_VERIFIED',
        verifiedBy: 'D. Borah, HSE Lead Superintendent',
        verifiedRole: 'Assam Asset Safety Directorate',
        verifiedAt: '2026-09-17 08:30 IST',
        notes: 'Confirmed SIF precursor. Retrained derrick crew on dual-lanyard latching sequence.',
      },
    },
  ],
  'Hot Work': [
    {
      id: 'OIL-UA-2026-0521',
      timestamp: '2026-09-19 13:40 IST',
      siteId: 'site-digboi-ocs2',
      siteName: 'Digboi Oil Collection Station (OCS-2)',
      operationalArea: 'Assam Asset',
      assetType: 'Oil Processing Plant',
      reportType: 'Unsafe Act',
      activity: 'Grating torch cutting',
      rawNarrative:
        'Contractor welder ignited oxy-acetylene torch to cut structural deck grating 8 meters from live crude oil sample header without performing a 2nd round combustible gas check after the 1-hour lunch break.',
      actualOutcome: 'Fire watch intervened immediately and extinguished torch; zero flash fire.',
      potentialConsequence:
        'Hydrocarbon vapor cloud ignition resulting in flash fire or separator manifold rupture with fatal burn severity.',
      sifPotential: 'SIF_POTENTIAL',
      lifeSavingRule: 'Hot Work',
      failedBarrier: 'Continuous Combustible LEL Gas Monitoring within 15m Radius',
      precursorClusterId: 'PREC-HOTWORK-01',
      explainability: {
        detectedEnergy: 'Thermal open flame ignition source in hazardous Zone 1/2 boundary',
        workerExposure: 'Welder and fire watch in proximity to potential vapor cloud',
        failedBarrier: 'LEL gas test not re-executed after work pause',
        barrierType: 'Preventive',
        potentialConsequence: 'Flash fire and thermal blast trauma',
        reasoningNarrative:
          'Open flame in hydrocarbon handling facility without re-verifying zero explosive gas atmosphere after work stoppage is a high fatal risk event.',
        tokens: [
          { text: 'ignited oxy-acetylene torch 8 meters from live crude oil sample header', category: 'hazard', explanation: 'Ignition source in hydrocarbon zone' },
        ],
        confidenceScore: 0.88,
        confidenceBand: 'HIGH_CONFIDENCE',
      },
      hseReview: {
        status: 'HSE_VERIFIED',
        verifiedBy: 'M. Neog, Process Safety Engineer',
        verifiedRole: 'Digboi Production Directorate',
        verifiedAt: '2026-09-19 16:15 IST',
        notes: 'SIF precursor verified. Hot work permit suspended until gas testing protocol audited.',
      },
    },
  ],
  'Bypassing Safety Controls': [
    {
      id: 'OIL-UC-2026-0314',
      timestamp: '2026-09-17 09:15 IST',
      siteId: 'site-duliajan-gcs3',
      siteName: 'Gas Compression Station #03',
      operationalArea: 'Assam Asset',
      assetType: 'Gas Gathering Station',
      reportType: 'Unsafe Condition',
      activity: 'Auxiliary sensor maintenance',
      rawNarrative:
        'High-vibration sensor jumpered on auxiliary cooling water pump during electrical maintenance; no formal override permit was logged on the safety-critical element bypass register.',
      actualOutcome: 'Temporary jumper detected during morning inspection and removed.',
      potentialConsequence:
        'Cooling pump mechanical seal failure; non-fatal equipment damage.',
      sifPotential: 'NON_SIF_POTENTIAL',
      lifeSavingRule: 'Bypassing Safety Controls',
      failedBarrier: 'Formal Safety Critical Element Bypass Authorization',
      precursorClusterId: '',
      explainability: {
        detectedEnergy: 'Low-pressure utility cooling water',
        workerExposure: 'Utility pump shed; isolated from high pressure or hydrocarbons',
        failedBarrier: 'Administrative override permit log not completed',
        barrierType: 'Preventive',
        potentialConsequence: 'Auxiliary motor bearing wear; no fatal exposure pathway',
        reasoningNarrative:
          'Non-SIF event. While bypassing a sensor is an operational non-conformance, the medium is low-pressure cooling water without catastrophic energy potential.',
        tokens: [
          { text: 'High-vibration sensor jumpered on auxiliary cooling water pump', category: 'action', explanation: 'Safety control bypass on non-critical utility' },
        ],
        confidenceScore: 0.96,
        confidenceBand: 'HIGH_CONFIDENCE',
      },
      hseReview: {
        status: 'HSE_VERIFIED',
        verifiedBy: 'D. Borah, HSE Lead Superintendent',
        verifiedRole: 'Assam Asset Safety Directorate',
        verifiedAt: '2026-09-17 11:00 IST',
        notes: 'Non-SIF event confirmed. Emphasized override logging protocol to maintenance team.',
      },
    },
  ],
  'Toxic Gas / Chemical Exposure': [
    {
      id: 'OIL-NM-2026-0419',
      timestamp: '2026-09-15 08:30 IST',
      siteId: 'site-digboi-ocs2',
      siteName: 'Digboi Oil Collection Station (OCS-2)',
      operationalArea: 'Assam Asset',
      assetType: 'Oil Processing Plant',
      reportType: 'Near Miss',
      activity: 'Crude Storage Tank Dip Gauging',
      rawNarrative:
        'During morning manual dip tape gauging at Tank T-04, portable H2S sensor alarmed at 15 PPM near open thief hatch. Operator was standing upwind and immediately closed hatch before symptoms occurred. Tank vapor seal was discovered perished.',
      actualOutcome: 'Near miss; operator retreated safely upwind without inhalation symptoms.',
      potentialConsequence:
        'Acute H2S toxic gas exposure causing rapid loss of consciousness, fall from tank stair tower, and fatal asphyxiation.',
      sifPotential: 'SIF_POTENTIAL',
      lifeSavingRule: 'Toxic Gas / Chemical Exposure',
      failedBarrier: 'Tank Vapor Seal Integrity & Automatic Gauge Systems',
      precursorClusterId: 'PREC-07-CONFINED-SPACE',
      explainability: {
        detectedEnergy: 'Toxic chemical inhalation hazard (Hydrogen Sulfide gas)',
        workerExposure: 'Worker positioned directly above open tank thief hatch at 12m height',
        failedBarrier: 'Perished vapor seal allowed fugitive H2S release during manual intervention',
        barrierType: 'Preventive',
        potentialConsequence: 'Fatal toxic gas inhalation and secondary fall from height',
        reasoningNarrative:
          'H2S concentrations exceeding 10 PPM in elevated locations represent severe SIF potential due to rapid olfactory fatigue, incapacitation, and fall trauma.',
        tokens: [
          { text: 'portable H2S sensor alarmed at 15 PPM', category: 'hazard', explanation: 'Toxic concentration above ceiling threshold' },
          { text: 'open thief hatch', category: 'action', explanation: 'Atmospheric boundary breach' },
          { text: 'Tank vapor seal was discovered perished', category: 'barrier', explanation: 'Containment barrier degradation' },
        ],
        confidenceScore: 0.94,
        confidenceBand: 'HIGH_CONFIDENCE',
      },
      hseReview: {
        status: 'HSE_VERIFIED',
        verifiedBy: 'M. Neog, Process Safety Engineer',
        verifiedRole: 'Digboi Production Directorate',
        verifiedAt: '2026-09-15 14:00 IST',
        notes: 'Verified SIF Precursor. Tank thief hatch replaced with radar gauge transmitter.',
      },
    },
  ],
  'Lifting Operations': [
    {
      id: 'OIL-UC-2026-0785',
      timestamp: '2026-09-14 16:45 IST',
      siteId: 'site-moran-07',
      siteName: 'Moran Workover Rig #07',
      operationalArea: 'Assam Asset',
      assetType: 'Workover Rig',
      reportType: 'Unsafe Condition',
      activity: 'Tubular Hoisting & Drawworks Inspection',
      rawNarrative:
        'Routine visual inspection on crown block traveling sheave revealed deep metal fatigue cracking and worn flange rim on center groove wireline track. Drawworks wire rope showed 4 broken outer strands within 1 foot pitch.',
      actualOutcome: 'Unsafe condition flagged before rig startup; traveling block locked out for sheave replacement.',
      potentialConsequence:
        'Catastrophic wire rope parting or sheave failure under 80-ton hook load dropping traveling assembly with multiple fatalities on drill floor.',
      sifPotential: 'SIF_POTENTIAL',
      lifeSavingRule: 'Lifting Operations',
      failedBarrier: 'Drawworks Wire Rope & Sheave Critical Load Inspection Limit',
      precursorClusterId: 'PREC-02-LINE-FIRE',
      explainability: {
        detectedEnergy: 'Heavy suspended gravitational mass (80-ton traveling block assembly)',
        workerExposure: 'Rig floor crew positioned directly beneath traveling block path',
        failedBarrier: 'Sheave wear limit exceeded; rope fatigue strands exceeding retirement criteria',
        barrierType: 'Preventive',
        potentialConsequence: 'Catastrophic equipment drop causing multiple fatal crush impacts',
        reasoningNarrative:
          'Traveling block sheave crack and broken rope strands under heavy cyclic hook load are primary precursors to catastrophic mast dropping incidents.',
        tokens: [
          { text: 'deep metal fatigue cracking and worn flange rim', category: 'hazard', explanation: 'Critical load-bearing structural degradation' },
          { text: '4 broken outer strands within 1 foot pitch', category: 'hazard', explanation: 'Hoisting line retirement criterion breached' },
        ],
        confidenceScore: 0.96,
        confidenceBand: 'HIGH_CONFIDENCE',
      },
      hseReview: {
        status: 'HSE_VERIFIED',
        verifiedBy: 'R. K. Saikia, Field Safety Officer',
        verifiedRole: 'Moran Workover Division',
        verifiedAt: '2026-09-15 09:30 IST',
        notes: 'Verified SIF Precursor. Full mast line spooling and sheave replacement ordered.',
      },
    },
  ],
};
