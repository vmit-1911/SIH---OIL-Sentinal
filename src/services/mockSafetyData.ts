import type { SafetyReport, PrecursorCluster, CommandCenterMetrics } from '../types/safety';

export const MOCK_COMMAND_CENTER_METRICS: CommandCenterMetrics = {
  totalAnalyzed: 1482,
  sifFlaggedCount: 164,
  sifDensityPercent: 11.1,
  activePrecursorClusters: 4,
  verifiedByHsePercent: 78.6,
  highRiskAssetsCount: 6,
};

export const MOCK_PRECURSOR_CLUSTER: PrecursorCluster = {
  id: 'PREC-04-ENERGY-ISO',
  title: 'High-Pressure Energy Isolation & Zero-Verification Bypass',
  lifeSavingRule: 'Energy Isolation',
  severity: 'CRITICAL_SIGNAL',
  headlineSummary:
    '7 separate observations across 4 production & drilling assets reveal repeated unbolting or servicing of pressurized lines without positive zero-energy verification or physical LOTO.',
  rootCausalMechanisms:
    'Crews are relying on digital panel indicators or closed manual valves without physical lockouts, bleed-off line venting, or independent verification of residual pressure before line breach.',
  primaryFailedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
  primaryActivity: 'High-Pressure Line, Pump & Valve Servicing',
  reportCount: 7,
  assetsInvolved: [
    { siteId: 'site-duliajan-14', siteName: 'Duliajan Deep Drill Rig #14', reportCount: 2 },
    { siteId: 'site-moran-07', siteName: 'Moran Workover Rig #07', reportCount: 2 },
    { siteId: 'site-digboi-ocs2', siteName: 'Digboi Oil Collection Station (OCS-2)', reportCount: 2 },
    { siteId: 'site-nhk-11', siteName: 'Naharkatiya Wellhead #11', reportCount: 1 },
  ],
  trendVelocity: '+40% in 14 days',
  earliestReport: '2026-09-08',
  latestReport: '2026-09-22',
  reportIds: [
    'OIL-UA-2026-0842',
    'OIL-UA-2026-0849',
    'OIL-UA-2026-0855',
    'OIL-UA-2026-0861',
    'OIL-UA-2026-0867',
    'OIL-UA-2026-0873',
    'OIL-UA-2026-0880',
  ],
};

export const MOCK_SAFETY_REPORTS: SafetyReport[] = [
  {
    id: 'OIL-UA-2026-0842',
    timestamp: '2026-09-22 09:40 IST',
    siteId: 'site-duliajan-14',
    siteName: 'Duliajan Deep Drill Rig #14',
    operationalArea: 'Assam Asset',
    assetType: 'Drilling Rig',
    reportType: 'Unsafe Act',
    activity: 'Mud Pump Fluid End Overhaul',
    rawNarrative:
      'During morning shift at Rig 14, floorhand unbolted mud pump discharge line flange without closing suction isolation valve and without venting the bleed-off cock. Local analog gauge read 0 PSI due to stuck needle. Slurry residue sprayed out with force when final stud loosened. No one was injured.',
    actualOutcome: 'No injury; minor fluid spray onto deck grating.',
    potentialConsequence:
      'Catastrophic line detachment under hydraulic surge; potential fatal blunt-force trauma or fluid injection injury to technicians within line of fire.',
    sifPotential: 'SIF_POTENTIAL',
    lifeSavingRule: 'Energy Isolation',
    failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
    precursorClusterId: 'PREC-04-ENERGY-ISO',
    explainability: {
      detectedEnergy: 'High-pressure drilling mud hydraulic head (3,500 PSI rated line)',
      workerExposure: 'Technician positioned directly over line flange during unbolting',
      failedBarrier: 'Suction isolation valve left unclosed; bleed-off cock unvented; zero-energy state unverified',
      barrierType: 'Preventive',
      potentialConsequence: 'High-velocity fluid injection or metal flange projectile impact with fatal consequence',
      reasoningNarrative:
        'The operation involved opening a closed system rated for high hydraulic energy. The primary prevention barrier (double block & bleed with verified zero pressure) was omitted. Relying on an uncalibrated pressure gauge created immediate fatal exposure had full pump pressure kicked in.',
      tokens: [
        { text: 'unbolted mud pump discharge line flange', category: 'action', explanation: 'Mechanical opening of pressurized containment' },
        { text: 'without closing suction isolation valve', category: 'barrier', explanation: 'Omission of primary upstream physical barrier' },
        { text: 'without venting the bleed-off cock', category: 'barrier', explanation: 'Absence of zero-energy verification procedure' },
        { text: 'stuck needle', category: 'hazard', explanation: 'Faulty telemetry creating false perception of safe zero state' },
        { text: 'sprayed out with force', category: 'consequence', explanation: 'Release of trapped stored kinetic/hydraulic energy' }
      ],
      confidenceScore: 0.94,
      confidenceBand: 'HIGH_CONFIDENCE',
    },
    hseReview: {
      status: 'HSE_VERIFIED',
      verifiedBy: 'D. Borah, HSE Lead Superintendent',
      verifiedRole: 'Assam Asset Safety Directorate',
      verifiedAt: '2026-09-22 14:15 IST',
      notes: 'Confirmed SIF-potential. Issued immediate LOTO stand-down to all shift drillers at Duliajan Rig 14.',
    },
  },
  {
    id: 'OIL-UA-2026-0849',
    timestamp: '2026-09-20 16:15 IST',
    siteId: 'site-moran-07',
    siteName: 'Moran Workover Rig #07',
    operationalArea: 'Assam Asset',
    assetType: 'Workover Rig',
    reportType: 'Near Miss',
    activity: 'Swabbing & Kelly Hose Disconnection',
    rawNarrative:
      'Contractor roughneck attempted to break hammer union on 4-inch standpipe rotary hose while swivel packoff line still held residual gas cushion. Bleed-off line was choked with dried mud cakes. Sledgehammer blow released gas kick whistling past worker face.',
    actualOutcome: 'Near miss; worker startled, no physical strike.',
    potentialConsequence:
      'High-velocity rotary hose whip or gas cloud ignition near wellbore; high likelihood of fatal impact or flash burn.',
    sifPotential: 'SIF_POTENTIAL',
    lifeSavingRule: 'Energy Isolation',
    failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
    precursorClusterId: 'PREC-04-ENERGY-ISO',
    explainability: {
      detectedEnergy: 'Trapped gas pocket pressure under standpipe line',
      workerExposure: 'Worker hammering union in direct arc of potential hose whip',
      failedBarrier: 'Choked bleed line not verified clear before striking hammer union',
      barrierType: 'Preventive',
      potentialConsequence: 'Rotary hose flailing under stored gas pressure causing fatal impact',
      reasoningNarrative:
        'Line of fire and energy isolation were both compromised simultaneously. Striking a hammer union with trapped pneumatic energy without verified depressurization is a well-documented global oilfield fatality precursor.',
      tokens: [
        { text: 'break hammer union on 4-inch standpipe', category: 'action', explanation: 'Mechanical force applied to pressurized fitting' },
        { text: 'held residual gas cushion', category: 'energy', explanation: 'Compressible gas energy source' },
        { text: 'Bleed-off line was choked', category: 'barrier', explanation: 'Failure of auxiliary depressurization barrier' },
        { text: 'whistling past worker face', category: 'consequence', explanation: 'Narrow near-miss trajectory of released gas' }
      ],
      confidenceScore: 0.92,
      confidenceBand: 'HIGH_CONFIDENCE',
    },
    hseReview: {
      status: 'HSE_VERIFIED',
      verifiedBy: 'R. K. Saikia, Field Safety Officer',
      verifiedRole: 'Moran Workover Division',
      verifiedAt: '2026-09-21 10:00 IST',
      notes: 'Reviewed and categorized as SIF Precursor. Tool pusher reminded on rotary hose depressurization checklists.',
    },
  },
  {
    id: 'OIL-UA-2026-0855',
    timestamp: '2026-09-18 11:30 IST',
    siteId: 'site-digboi-ocs2',
    siteName: 'Digboi Oil Collection Station (OCS-2)',
    operationalArea: 'Assam Asset',
    assetType: 'Oil Processing Plant',
    reportType: 'Unsafe Condition',
    activity: 'Crude Oil Separator Maintenance',
    rawNarrative:
      'Maintenance crew unbolted inlet manifold on test separator while isolation gate valve MV-104 had no padlock or tag applied on handwheel. In control room, mimic panel displayed valve closed, but valve stem indicator on site showed 15% open due to stripped worm gear.',
    actualOutcome: 'No injury; supervisor caught discrepancy during permit audit.',
    potentialConsequence:
      'Full crude oil & associated gas breakout under 45 bar inlet pressure; severe vapor cloud formation with high SIF explosion potential.',
    sifPotential: 'SIF_POTENTIAL',
    lifeSavingRule: 'Energy Isolation',
    failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
    precursorClusterId: 'PREC-04-ENERGY-ISO',
    explainability: {
      detectedEnergy: 'Hydrocarbon fluid & associated gas at 45 bar line pressure',
      workerExposure: 'Four technicians standing around open flange face in enclosed manifold shed',
      failedBarrier: 'Zero physical LOTO; mechanical valve position discrepancy not verified on-site',
      barrierType: 'Preventive',
      potentialConsequence: 'High-volume hydrocarbon release leading to catastrophic fire/explosion and multiple fatalities',
      reasoningNarrative:
        'A critical safety barrier (positive physical lockout) was replaced by an unverified control room assumption. Unbolting live hydrocarbon manifolds without physical blinds or verified zero differential is a Tier-1 process safety event precursor.',
      tokens: [
        { text: 'unbolted inlet manifold on test separator', category: 'action', explanation: 'Flange disassembly on hydrocarbon vessel' },
        { text: 'no padlock or tag applied', category: 'barrier', explanation: 'Failure of Lockout/Tagout protocol' },
        { text: 'valve stem indicator on site showed 15% open', category: 'hazard', explanation: 'Passing valve allowing continuous energy flow' },
        { text: 'stripped worm gear', category: 'hazard', explanation: 'Mechanical failure masking live valve state' }
      ],
      confidenceScore: 0.96,
      confidenceBand: 'HIGH_CONFIDENCE',
    },
    hseReview: {
      status: 'HSE_VERIFIED',
      verifiedBy: 'M. Neog, Process Safety Engineer',
      verifiedRole: 'Digboi Production Directorate',
      verifiedAt: '2026-09-18 17:30 IST',
      notes: 'Critical SIF precursor confirmed. Mechanical blind must be inserted prior to any separator bolting work.',
    },
  },
  {
    id: 'OIL-UA-2026-0861',
    timestamp: '2026-09-15 14:05 IST',
    siteId: 'site-nhk-11',
    siteName: 'Naharkatiya Wellhead #11',
    operationalArea: 'Assam Asset',
    assetType: 'Drilling Rig',
    reportType: 'Unsafe Act',
    activity: 'Wellhead Christmas Tree Gland Tightening',
    rawNarrative:
      'Contractor technician was observed tightening gland packing nuts on lower master valve with 36-inch pipe wrench while well shut-in tubing pressure was 2,800 PSI. No permit to work was displayed, and well was not equalized or isolated downstream.',
    actualOutcome: 'Gland stopped weeping; worker walked away unharmed.',
    potentialConsequence:
      'Stem ejection or bonnet stud shear under 2,800 PSI gas pressure; projectile could cause fatal blunt-force trauma to operator.',
    sifPotential: 'SIF_POTENTIAL',
    lifeSavingRule: 'Energy Isolation',
    failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
    precursorClusterId: 'PREC-04-ENERGY-ISO',
    explainability: {
      detectedEnergy: 'High-pressure reservoir gas (2,800 PSI)',
      workerExposure: 'Technician directly facing valve bonnet during forceful wrench tightening',
      failedBarrier: 'Adjustment performed under live pressure without depressurizing or barrier controls',
      barrierType: 'Preventive',
      potentialConsequence: 'High-pressure gas stem blowout causing fatal impact or shrapnel injuries',
      reasoningNarrative:
        'Tightening pressurized gland nuts without verified engineering controls on live 2,800 PSI wellheads bypasses fundamental well integrity barriers. Represents high fatal potential despite zero injury outcome.',
      tokens: [
        { text: 'tightening gland packing nuts', category: 'action', explanation: 'Mechanical work on pressurized component' },
        { text: 'tubing pressure was 2,800 PSI', category: 'energy', explanation: 'Extreme stored pressure energy' },
        { text: 'No permit to work was displayed', category: 'barrier', explanation: 'Administrative verification control bypassed' },
        { text: 'not equalized or isolated', category: 'barrier', explanation: 'Zero barrier verification before intervention' }
      ],
      confidenceScore: 0.89,
      confidenceBand: 'HIGH_CONFIDENCE',
    },
    hseReview: {
      status: 'HSE_VERIFIED',
      verifiedBy: 'D. Borah, HSE Lead Superintendent',
      verifiedRole: 'Assam Asset Safety Directorate',
      verifiedAt: '2026-09-16 09:10 IST',
      notes: 'Verified as SIF Precursor. Contractor company warned regarding live wellhead interventions.',
    },
  },
  {
    id: 'OIL-UA-2026-0867',
    timestamp: '2026-09-12 21:50 IST',
    siteId: 'site-duliajan-14',
    siteName: 'Duliajan Deep Drill Rig #14',
    operationalArea: 'Assam Asset',
    assetType: 'Drilling Rig',
    reportType: 'Unsafe Condition',
    activity: 'Blowout Preventer (BOP) Hydraulic Unit Maintenance',
    rawNarrative:
      'Mechanic unscrewed manifold check valve on Koomey BOP accumulator unit while 3,000 PSI nitrogen pre-charge bottles were still connected to line header. Isolator needle valve NV-04 was stiff and stopped midway without fully seating.',
    actualOutcome: 'Sudden burst of nitrogen hissed into room; mechanic dropped wrench and retreated.',
    potentialConsequence:
      'Catastrophic check valve assembly projectile ejection under 3,000 PSI gas expansion; fatal cranial or chest trauma.',
    sifPotential: 'SIF_POTENTIAL',
    lifeSavingRule: 'Energy Isolation',
    failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
    precursorClusterId: 'PREC-04-ENERGY-ISO',
    explainability: {
      detectedEnergy: 'Compressed nitrogen gas pre-charge at 3,000 PSI in accumulator bottles',
      workerExposure: 'Mechanic hands and head positioned in direct trajectory of unscrewed valve',
      failedBarrier: 'Incomplete valve seating; bleed-down to atmosphere not confirmed before thread unseating',
      barrierType: 'Preventive',
      potentialConsequence: 'High-pressure valve body missile strike with fatal trauma potential',
      reasoningNarrative:
        'Nitrogen accumulator pressure is an explosive stored energy source. Unscrewing components without complete bottle depressurization and bleed verification is a direct precursor to fatal pneumatic ejection incidents.',
      tokens: [
        { text: 'unscrewed manifold check valve', category: 'action', explanation: 'Disassembly of high-pressure fitting' },
        { text: '3,000 PSI nitrogen pre-charge bottles', category: 'energy', explanation: 'High-energy pneumatic source' },
        { text: 'stopped midway without fully seating', category: 'barrier', explanation: 'Latent barrier failure preventing isolation' },
        { text: 'Sudden burst of nitrogen hissed', category: 'consequence', explanation: 'Uncontrolled energy release' }
      ],
      confidenceScore: 0.95,
      confidenceBand: 'HIGH_CONFIDENCE',
    },
    hseReview: {
      status: 'HSE_VERIFIED',
      verifiedBy: 'D. Borah, HSE Lead Superintendent',
      verifiedRole: 'Assam Asset Safety Directorate',
      verifiedAt: '2026-09-13 08:30 IST',
      notes: 'Second isolation-related report from Rig 14 this month. Tool Pusher summoned for operational review.',
    },
  },
  {
    id: 'OIL-UA-2026-0873',
    timestamp: '2026-09-10 15:20 IST',
    siteId: 'site-moran-07',
    siteName: 'Moran Workover Rig #07',
    operationalArea: 'Assam Asset',
    assetType: 'Workover Rig',
    reportType: 'Unsafe Act',
    activity: 'Mud Agitator Drive Shaft Inspection',
    rawNarrative:
      'Electrician stuck his hand into the mud tank agitator belt guard to inspect tension. Start/stop push button on local station had a cardboard tag taped over it, but main MCC breaker switch 300 meters away was not padlocked in OFF position.',
    actualOutcome: 'Agitator did not start; colleague noticed and instructed electrician to pull hand back.',
    potentialConsequence:
      'Remote or automated PLC motor start; amputation or entangling of arm resulting in fatal traumatic shock.',
    sifPotential: 'SIF_POTENTIAL',
    lifeSavingRule: 'Energy Isolation',
    failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
    precursorClusterId: 'PREC-04-ENERGY-ISO',
    explainability: {
      detectedEnergy: '415V 3-phase electric motor with high-torque mechanical gearbox',
      workerExposure: 'Hand inserted inside moving machinery belt enclosure',
      failedBarrier: 'Cardboard tape used instead of primary Lockout/Tagout at the motor control center',
      barrierType: 'Preventive',
      potentialConsequence: 'Severe crushing or fatal rotational entanglement in drive pulleys',
      reasoningNarrative:
        'Taping over a local pushbutton is an informal shortcut that completely circumvents electrical isolation rules. The system was live at the breaker and capable of automated start at any moment.',
      tokens: [
        { text: 'stuck his hand into the mud tank agitator belt guard', category: 'action', explanation: 'Exposure inside entrapment hazard zone' },
        { text: 'cardboard tag taped over it', category: 'barrier', explanation: 'Informal, non-compliant bypass of physical LOTO' },
        { text: 'main MCC breaker switch was not padlocked', category: 'barrier', explanation: 'Failure of primary electrical isolation point' }
      ],
      confidenceScore: 0.93,
      confidenceBand: 'HIGH_CONFIDENCE',
    },
    hseReview: {
      status: 'HSE_VERIFIED',
      verifiedBy: 'R. K. Saikia, Field Safety Officer',
      verifiedRole: 'Moran Workover Division',
      verifiedAt: '2026-09-11 11:20 IST',
      notes: 'Strict non-conformance issued. All rig floor crews required to use standardized padlock hasps.',
    },
  },
  {
    id: 'OIL-UA-2026-0880',
    timestamp: '2026-09-08 10:10 IST',
    siteId: 'site-digboi-ocs2',
    siteName: 'Digboi Oil Collection Station (OCS-2)',
    operationalArea: 'Assam Asset',
    assetType: 'Oil Processing Plant',
    reportType: 'Near Miss',
    activity: 'Crude Oil Pipeline Pigging Operation',
    rawNarrative:
      'Operator started slacking safety bolts on 16-inch crude pipeline pig receiver door while vent valve VV-02 was whistling faint vapor. Operator assumed line was clear because receiver drain was dripping slowly. When locking ring was loosened half turn, door kicked violently 2 inches.',
    actualOutcome: 'Safety locking interlock pin prevented door from opening fully; operator suffered minor bruise.',
    potentialConsequence:
      '16-inch high-mass receiver door blowing open under residual crude gas pressure; fatal blunt-force impact to operator standing in doorway arc.',
    sifPotential: 'SIF_POTENTIAL',
    lifeSavingRule: 'Energy Isolation',
    failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
    precursorClusterId: 'PREC-04-ENERGY-ISO',
    explainability: {
      detectedEnergy: 'Trapped pipeline hydrocarbon pressure in 16-inch heavy steel chamber',
      workerExposure: 'Operator standing directly in line of travel of pig receiver door',
      failedBarrier: 'Unbolting started while vent was still hissing and pressure verification incomplete',
      barrierType: 'Preventive',
      potentialConsequence: '200kg steel door blown open under pneumatic force causing fatal chest crush',
      reasoningNarrative:
        'A textbook SIF precursor. The presence of whistling vapor was an active warning of unverified zero pressure. Only the secondary mechanical safety pin prevented a catastrophic door flyout fatality.',
      tokens: [
        { text: 'slacking safety bolts on 16-inch pig receiver door', category: 'action', explanation: 'Loosening pressure vessel closure' },
        { text: 'vent valve was whistling faint vapor', category: 'hazard', explanation: 'Audible evidence of trapped pressurized fluid' },
        { text: 'door kicked violently 2 inches', category: 'consequence', explanation: 'Sudden release of trapped kinetic energy' },
        { text: 'Safety locking interlock pin prevented door from opening', category: 'barrier', explanation: 'Mitigative mechanical barrier holding' }
      ],
      confidenceScore: 0.97,
      confidenceBand: 'HIGH_CONFIDENCE',
    },
    hseReview: {
      status: 'HSE_VERIFIED',
      verifiedBy: 'M. Neog, Process Safety Engineer',
      verifiedRole: 'Digboi Production Directorate',
      verifiedAt: '2026-09-08 16:45 IST',
      notes: 'Identified as critical multi-site precursor. Sent urgent memo to Duliajan and Moran field engineers.',
    },
  },
];
