export type SchemaVersion = "v1";

export interface LLMRequest {
  schemaVersion: SchemaVersion;
  taskId: string;
  imageUrl: string;
  locale?: string;
  userHints?: Record<string, unknown> | null;
  promptOverrides?: Record<string, unknown> | null;
}

export type Phase = "stype" | "style" | "subzone" | "struct";
export type LLMEventType =
  | "phase"
  | "delta"
  | "phase_done"
  | "radar"
  | "done"
  | "error";

export interface LLMEvent {
  type: LLMEventType;
  phase?: Phase;
  text?: string;
  payload?: Record<string, unknown>;
  radar?: { stype: number; style: number; subzone: number; struct: number };
  error?: { code: string; message?: string; retryable?: boolean };
}

// ----- 4S Report v1 payload structures -----
export type LayerStatus = "good" | "watch" | "attention";

export interface StypePayload {
  primary: "bone" | "flesh" | "skin";
  ratios: { bone: number; flesh: number; skin: number };
  label: string;
  narrative: string;
  evidence?: Array<{ feature: string; note: string }>;
}

export interface StylePayload {
  primary_type: string;
  primary_label: string;
  secondary?: Array<{ type: string; label: string; weight: number }>;
  narrative: string;
}

export interface SubzonePayload {
  zones: Array<{
    code: string;
    label: string;
    status: LayerStatus;
    description: string;
  }>;
}

export interface StructPayload {
  layers: Array<{
    code: string;
    label: string;
    status: LayerStatus;
    description: string;
  }>;
}

export interface RadarScores {
  stype: number;
  style: number;
  subzone: number;
  struct: number;
}
