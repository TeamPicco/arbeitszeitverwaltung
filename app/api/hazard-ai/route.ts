import { FEATURES, isFeatureEnabled } from "../../../lib/features/featureFlags";

const SYSTEM_PROMPT = `Du bist ein Experte für deutsche Arbeitssicherheit. 
Du kennst §5 ArbSchG, die DGUV-Vorschriften und alle 
relevanten deutschen Arbeitsschutzgesetze auswendig. 
Gib konkrete, praxisnahe und rechtssichere Vorschläge 
für Gefährdungsbeurteilungen. Passe deine Antwort immer 
an die genannte Branche an. Antworte ausschließlich auf Deutsch. 
Halte deine Antwort unter 200 Wörtern.`;

type HazardAiRequestBody = {
  step: number;
  stepName: string;
  industry: string;
  existingText: string;
};

type FeaturePlan = "starter" | "professional" | "compliance" | "complete";

const PLAN_FEATURES: Record<FeaturePlan, readonly string[]> = {
  starter: [],
  professional: [FEATURES.LABOR_LAW_GUARD],
  compliance: [FEATURES.LABOR_LAW_GUARD, FEATURES.HAZARD_ASSESSMENT],
  complete: [
    FEATURES.LABOR_LAW_GUARD,
    FEATURES.HAZARD_ASSESSMENT,
    FEATURES.DATEV_EXPORT,
  ],
};

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function isValidPayload(payload: unknown): payload is HazardAiRequestBody {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }

  const candidate = payload as Partial<HazardAiRequestBody>;
  const validStep = typeof candidate.step === "number" && candidate.step >= 1 && candidate.step <= 5;

  return (
    validStep &&
    typeof candidate.stepName === "string" &&
    candidate.stepName.trim().length > 0 &&
    typeof candidate.industry === "string" &&
    candidate.industry.trim().length > 0 &&
    typeof candidate.existingText === "string"
  );
}

function buildUserPrompt(payload: HazardAiRequestBody): string {
  return [
    `Schritt: ${payload.step}`,
    `Schrittname: ${payload.stepName}`,
    `Branche: ${payload.industry}`,
    "",
    "Bisheriger Text des Nutzers:",
    payload.existingText.trim().length > 0 ? payload.existingText : "(leer)",
    "",
    "Erstelle eine konkrete, sofort nutzbare Formulierung für diesen Schritt.",
  ].join("\n");
}

function normalizeFeaturePlan(value: string | null): FeaturePlan | null {
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

function extractFeaturePlanFromRequest(request: Request): FeaturePlan | null {
  const headerPlan = normalizeFeaturePlan(request.headers.get("x-feature-plan"));
  if (headerPlan) {
    return headerPlan;
  }

  const cookieHeader = request.headers.get("cookie");
  if (!cookieHeader) {
    return null;
  }

  const cookies = cookieHeader.split(";").map((cookie) => cookie.trim());
  for (const cookie of cookies) {
    const [key, ...rest] = cookie.split("=");
    if (!key || rest.length === 0) {
      continue;
    }

    const value = decodeURIComponent(rest.join("="));
    if (
      key === "feature_plan" ||
      key === "featurePlan" ||
      key === "user_plan" ||
      key === "userPlan"
    ) {
      const normalized = normalizeFeaturePlan(value);
      if (normalized) {
        return normalized;
      }
    }
  }

  return null;
}

function hasHazardFeatureAccess(request: Request): boolean {
  if (isFeatureEnabled(FEATURES.HAZARD_ASSESSMENT)) {
    return true;
  }

  const requestPlan = extractFeaturePlanFromRequest(request);
  if (!requestPlan) {
    return false;
  }

  return PLAN_FEATURES[requestPlan].includes(FEATURES.HAZARD_ASSESSMENT);
}

function createStreamingResponse(anthropicStream: ReadableStream<Uint8Array>): Response {
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  const reader = anthropicStream.getReader();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });

          while (buffer.includes("\n")) {
            const separatorIndex = buffer.indexOf("\n");
            const rawLine = buffer.slice(0, separatorIndex);
            buffer = buffer.slice(separatorIndex + 1);

            const line = rawLine.trim();
            if (!line.startsWith("data:")) {
              continue;
            }

            const data = line.slice("data:".length).trim();
            if (!data || data === "[DONE]") {
              continue;
            }

            try {
              const parsed = JSON.parse(data) as {
                type?: string;
                delta?: { text?: string };
                error?: { message?: string };
              };

              if (parsed.type === "error") {
                controller.enqueue(
                  encoder.encode(
                    "\n\nDie KI-Antwort konnte nicht vollständig verarbeitet werden.",
                  ),
                );
                continue;
              }

              const textChunk = parsed.delta?.text;
              if (typeof textChunk === "string" && textChunk.length > 0) {
                controller.enqueue(encoder.encode(textChunk));
              }
            } catch {
              // Nicht-JSON oder Meta-Events ohne Text ignorieren.
            }
          }
        }
      } catch {
        controller.enqueue(
          encoder.encode(
            "\n\nEs ist ein Fehler beim Streamen der KI-Antwort aufgetreten. Bitte versuche es erneut.",
          ),
        );
      } finally {
        controller.close();
        reader.releaseLock();
      }
    },
    async cancel() {
      await reader.cancel();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}

export async function POST(request: Request): Promise<Response> {
  try {
    const featureActive = hasHazardFeatureAccess(request);
    if (!featureActive) {
      return Response.json(
        {
          error:
            "Dieses Premium-Modul ist für deinen aktuellen Tarif nicht freigeschaltet.",
        },
        { status: 403 },
      );
    }

    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return Response.json(
        { error: "Ungültige Anfrage: JSON-Body konnte nicht gelesen werden." },
        { status: 400 },
      );
    }

    if (!isValidPayload(body)) {
      return Response.json(
        {
          error:
            "Ungültige Eingabedaten. Erwartet werden step (1-5), stepName, industry und existingText.",
        },
        { status: 400 },
      );
    }

    const anthropicApiKey = process.env.ANTHROPIC_API_KEY;
    if (!anthropicApiKey) {
      return Response.json(
        {
          error:
            "Die KI-Funktion ist derzeit nicht verfügbar (fehlender API-Schlüssel).",
        },
        { status: 500 },
      );
    }

    const model = process.env.ANTHROPIC_MODEL ?? "claude-3-7-sonnet-latest";
    const prompt = buildUserPrompt(body);

    const anthropicResponse = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": anthropicApiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model,
        max_tokens: 700,
        stream: true,
        system: SYSTEM_PROMPT,
        messages: [
          {
            role: "user",
            content: prompt,
          },
        ],
      }),
    });

    if (!anthropicResponse.ok) {
      const detail = await anthropicResponse.text();
      return Response.json(
        {
          error:
            "Die KI-Antwort konnte nicht erzeugt werden. Bitte versuche es in wenigen Minuten erneut.",
          details: detail,
        },
        { status: 502 },
      );
    }

    if (!anthropicResponse.body) {
      return Response.json(
        { error: "Die KI-Antwort enthält keinen Datenstrom." },
        { status: 502 },
      );
    }

    return createStreamingResponse(anthropicResponse.body);
  } catch {
    return Response.json(
      {
        error:
          "Beim Verarbeiten der Anfrage ist ein unerwarteter Fehler aufgetreten.",
      },
      { status: 500 },
    );
  }
}
