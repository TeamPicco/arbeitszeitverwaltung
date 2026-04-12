export const FEATURES = {
  HAZARD_ASSESSMENT: "HAZARD_ASSESSMENT",
  LABOR_LAW_GUARD: "LABOR_LAW_GUARD",
  DATEV_EXPORT: "DATEV_EXPORT",
} as const;

export type FeaturePlan = "starter" | "professional" | "compliance" | "complete";

type FeatureKey = (typeof FEATURES)[keyof typeof FEATURES];

export const FEATURE_PLAN_MAPPING: Record<FeaturePlan, readonly FeatureKey[]> = {
  starter: [],
  professional: [FEATURES.LABOR_LAW_GUARD],
  compliance: [FEATURES.LABOR_LAW_GUARD, FEATURES.HAZARD_ASSESSMENT],
  complete: [
    FEATURES.LABOR_LAW_GUARD,
    FEATURES.HAZARD_ASSESSMENT,
    FEATURES.DATEV_EXPORT,
  ],
};

type SessionWithPlan = {
  featurePlan?: FeaturePlan;
  user?: {
    featurePlan?: FeaturePlan;
    plan?: FeaturePlan;
  };
};

type FeatureRuntimeContext = {
  __FEATURE_PLAN__?: FeaturePlan;
  __DB_USER_PLAN__?: FeaturePlan;
  __SESSION__?: SessionWithPlan;
  sessionStorage?: {
    getItem: (key: string) => string | null;
  };
};

function normalizeFeaturePlan(value: unknown): FeaturePlan | null {
  if (
    value === "starter" ||
    value === "professional" ||
    value === "compliance" ||
    value === "complete"
  ) {
    return value;
  }

  return null;
}

function readPlanFromSession(): FeaturePlan | null {
  const runtime = globalThis as typeof globalThis & FeatureRuntimeContext;

  const explicitPlan = normalizeFeaturePlan(runtime.__FEATURE_PLAN__);
  if (explicitPlan) {
    return explicitPlan;
  }

  const sessionPlan = normalizeFeaturePlan(
    runtime.__SESSION__?.featurePlan ??
      runtime.__SESSION__?.user?.featurePlan ??
      runtime.__SESSION__?.user?.plan,
  );
  if (sessionPlan) {
    return sessionPlan;
  }

  const storage = runtime.sessionStorage;
  if (!storage) {
    return null;
  }

  return normalizeFeaturePlan(
    storage.getItem("feature_plan") ??
      storage.getItem("featurePlan") ??
      storage.getItem("user_plan") ??
      storage.getItem("userPlan"),
  );
}

function readPlanFromDatabase(): FeaturePlan | null {
  const runtime = globalThis as typeof globalThis & FeatureRuntimeContext;
  return normalizeFeaturePlan(runtime.__DB_USER_PLAN__);
}

function getCurrentFeaturePlan(): FeaturePlan {
  return readPlanFromSession() ?? readPlanFromDatabase() ?? "starter";
}

export function isFeatureEnabled(featureKey: string): boolean {
  const normalizedFeatureKey = featureKey as FeatureKey;
  const activePlan = getCurrentFeaturePlan();
  return FEATURE_PLAN_MAPPING[activePlan].includes(normalizedFeatureKey);
}
