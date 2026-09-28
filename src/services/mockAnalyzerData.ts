import type { DemoObservationFixture } from '../types/safety';

export const DEMO_OBSERVATION_FIXTURES: DemoObservationFixture[] = [
  {
    id: 'DEMO-01-ENERGY-ISO',
    title: 'High-Pressure Mud Pump Flange Loosening',
    reportType: 'Unsafe Act',
    siteName: 'Duliajan Deep Drill Rig #14',
    activity: 'Mud Pump Fluid End Maintenance',
    narrative:
      'During maintenance on high-pressure mud pump line at Rig 14, the technician began loosening the discharge flange before the bleed-off point was verified. The local analog gauge showed zero due to a stuck needle, but the line still contained trapped pressure. Residual slurry sprayed out under force when the final stud was turned. No worker was struck.',
    analysisResult: {
      reportId: 'SYN-2026-0842',
      sifPotential: 'SIF_POTENTIAL',
      classificationConfidence: 0.94,
      confidenceBand: 'HIGH_CONFIDENCE',
      lifeSavingRule: 'Energy Isolation',
      lsrReasoning:
        'The task involved mechanical breach of pressurized containment without verifying positive zero-energy isolation or bleeding off residual head pressure.',
      failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
      barrierType: 'Preventive',
      actualOutcome: 'No worker was struck; minor fluid spray onto deck grating.',
      potentialConsequence:
        'Catastrophic line detachment under hydraulic surge; fatal blunt-force trauma or high-velocity fluid injection injury to technicians.',
      extractedEnergy: 'Hydraulic drilling mud line pressure (rated 3,500 PSI)',
      extractedActivity: 'Mud pump fluid end overhaul and discharge flange loosening',
      extractedExposure: 'Technician positioned directly in line of fire over flange face during stud unbolting',
      evidenceItems: [
        {
          id: 'ev-1',
          originalPhrase: 'high-pressure mud pump line',
          deduction: 'High-hazard hydraulic energy source present (rated up to 3,500 PSI).',
          category: 'energy',
        },
        {
          id: 'ev-2',
          originalPhrase: 'before the bleed-off point was verified',
          deduction: 'Primary preventive barrier omitted: zero-energy state was not positively confirmed.',
          category: 'barrier',
        },
        {
          id: 'ev-3',
          originalPhrase: 'gauge showed zero due to a stuck needle',
          deduction: 'Instrumentation defect masked live energy state; visual dial relied upon without physical bleed.',
          category: 'instrumentation',
        },
        {
          id: 'ev-4',
          originalPhrase: 'loosening the discharge flange',
          deduction: 'Worker placed directly in the line of fire during breach of pressurized boundary.',
          category: 'action',
        },
      ],
      synthesisEquation: {
        factors: [
          'Stored 3,500 PSI Hydraulic Energy',
          'Unverified Isolation State',
          'Direct Line Breach Exposure',
        ],
        result: 'High SIF-Potential Precursor Exposure',
      },
      relatedPrecursor: {
        id: 'PREC-04-ENERGY-ISO',
        title: 'High-Pressure Energy Isolation & Zero-Verification Bypass',
        observationCount: 7,
        assetCount: 4,
        failedBarrier: 'Positive Physical Isolation & Bleed-off Verification',
      },
      reviewStatus: 'PENDING_REVIEW',
    },
  },
  {
    id: 'DEMO-02-CONFINED-SPACE',
    title: 'Crude Separator Entry Without Continuous Gas Monitoring',
    reportType: 'Unsafe Act',
    siteName: 'Digboi Oil Collection Station (OCS-2)',
    activity: 'Internal Separator Vessel Inspection',
    narrative:
      'Contractor technician stepped through the manway of the crude test separator at Digboi OCS-2 to inspect sludge baffle without donning continuous four-gas monitor. Initial gas test was logged 4 hours prior, but no forced ventilation was running and no standby observer was stationed at the vessel hatch. Worker felt light-headed and climbed back out.',
    analysisResult: {
      reportId: 'SYN-2026-0856',
      sifPotential: 'SIF_POTENTIAL',
      classificationConfidence: 0.96,
      confidenceBand: 'HIGH_CONFIDENCE',
      lifeSavingRule: 'Confined Space',
      lsrReasoning:
        'Permit-required confined space entered with stale atmospheric certification, absent continuous multi-gas detection, and missing standby surveillance.',
      failedBarrier: 'Continuous Atmospheric Gas Testing & Dedicated Standby Observer',
      barrierType: 'Preventive',
      actualOutcome: 'Worker felt light-headed, recognized dizziness, and climbed out through manway unassisted.',
      potentialConsequence:
        'Rapid toxic H2S incapacitation or oxygen-deficient asphyxiation leading to fatal respiratory arrest within 90 seconds.',
      extractedEnergy: 'Toxic chemical / gaseous reservoir energy (H2S and hydrocarbon vapor)',
      extractedActivity: 'Internal vessel inspection inside closed test separator',
      extractedExposure: 'Whole-body entry inside poorly ventilated hydrocarbon vessel',
      evidenceItems: [
        {
          id: 'ev-1',
          originalPhrase: 'stepped through the manway of the crude test separator',
          deduction: 'Physical entry into an enclosed permit-required confined space.',
          category: 'exposure',
        },
        {
          id: 'ev-2',
          originalPhrase: 'without donning continuous four-gas monitor',
          deduction: 'Continuous atmospheric defense barrier bypassed; blind to real-time gas ingress.',
          category: 'barrier',
        },
        {
          id: 'ev-3',
          originalPhrase: 'Initial gas test was logged 4 hours prior',
          deduction: 'Atmospheric clearance was invalid/stale; stratification occurs rapidly in closed vessels.',
          category: 'barrier',
        },
        {
          id: 'ev-4',
          originalPhrase: 'no standby observer was stationed at the vessel hatch',
          deduction: 'Emergency rescue and communication safeguard completely omitted.',
          category: 'barrier',
        },
      ],
      synthesisEquation: {
        factors: [
          'Confined Hydrocarbon Space',
          'Expired Atmospheric Clearance',
          'No Standby Guardian',
        ],
        result: 'High SIF Toxic Asphyxiation Precursor',
      },
      relatedPrecursor: {
        id: 'PREC-07-CONFINED-SPACE',
        title: 'Confined Space Entry Without Live Gas Verification',
        observationCount: 5,
        assetCount: 3,
        failedBarrier: 'Continuous Atmospheric Gas Testing & Dedicated Standby Observer',
      },
      reviewStatus: 'PENDING_REVIEW',
    },
  },
  {
    id: 'DEMO-03-NON-SIF-TRIP',
    title: 'Hose Tripping Hazard on Flat Walkway',
    reportType: 'Unsafe Condition',
    siteName: 'Moran Workover Rig #07',
    activity: 'Routine Deck Washdown',
    narrative:
      'Water supply hose was left coiled loosely across the mud pump access walkway near the shale shaker house. Handrails and grating were clean, but floorhand tripped slightly while carrying a bucket of wash water. No fall occurred and worker caught balance on handrail.',
    analysisResult: {
      reportId: 'SYN-2026-0870',
      sifPotential: 'NON_SIF_POTENTIAL',
      classificationConfidence: 0.95,
      confidenceBand: 'HIGH_CONFIDENCE',
      lifeSavingRule: 'Working at Height',
      lsrReasoning:
        'Observation evaluated against Line of Fire and Height rules; event occurred at zero ground elevation with low kinetic energy and effective secondary handrail controls.',
      failedBarrier: 'Walkway Housekeeping & Cable Ramping Protocol',
      barrierType: 'Preventive',
      actualOutcome: 'Floorhand tripped slightly and caught balance on handrail; zero injury occurred.',
      potentialConsequence:
        'Minor trip resulting in localized ankle strain or contusion; zero credible fatal consequence.',
      extractedEnergy: 'Low kinetic energy from walking pace trip at zero elevation',
      extractedActivity: 'Routine walkway transit carrying wash water',
      extractedExposure: 'Worker foot contacting flexible rubber wash hose',
      evidenceItems: [
        {
          id: 'ev-1',
          originalPhrase: 'Water supply hose was left coiled loosely across the mud pump access walkway',
          deduction: 'Minor physical housekeeping trip hazard on level ground.',
          category: 'barrier',
        },
        {
          id: 'ev-2',
          originalPhrase: 'caught balance on handrail',
          deduction: 'Secondary passive protection barrier (handrail) functioned effectively.',
          category: 'barrier',
        },
        {
          id: 'ev-3',
          originalPhrase: 'No fall occurred',
          deduction: 'No mechanical trauma or impact sustained.',
          category: 'action',
        },
      ],
      synthesisEquation: {
        factors: [
          'Zero Elevated Fall Height',
          'Low Walking Momentum',
          'Effective Handrail Catch',
        ],
        result: 'Non-SIF Routine Workplace Observation',
      },
      relatedPrecursor: {
        id: 'PREC-NON-SIF-HOUSEKEEPING',
        title: 'Rig Floor Housekeeping & Hose Routing',
        observationCount: 14,
        assetCount: 6,
        failedBarrier: 'Walkway Housekeeping & Cable Ramping Protocol',
      },
      reviewStatus: 'HSE_VERIFIED',
    },
  },
];
