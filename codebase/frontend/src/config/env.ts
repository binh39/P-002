import { z } from "zod";

const envSchema = z
  .object({
    VITE_AUTH_MODE: z.enum(["demo", "firebase"]).default("demo"),
    VITE_DATA_MODE: z.enum(["demo", "connected"]).default("demo"),
    VITE_PROJECTS_DATA_MODE: z.enum(["demo", "connected"]).optional(),
    VITE_API_BASE_URL: z.string().min(1).default("/api/v1"),
    VITE_FIREBASE_API_KEY: z.string().optional(),
    VITE_FIREBASE_AUTH_DOMAIN: z.string().optional(),
    VITE_FIREBASE_PROJECT_ID: z.string().optional(),
    VITE_FIREBASE_STORAGE_BUCKET: z.string().optional(),
    VITE_FIREBASE_APP_ID: z.string().optional(),
  })
  .superRefine((value, context) => {
    if (value.VITE_AUTH_MODE !== "firebase") return;

    const required = [
      "VITE_FIREBASE_API_KEY",
      "VITE_FIREBASE_AUTH_DOMAIN",
      "VITE_FIREBASE_PROJECT_ID",
      "VITE_FIREBASE_APP_ID",
    ] as const;
    for (const key of required) {
      if (!value[key]) {
        context.addIssue({
          code: "custom",
          path: [key],
          message: `${key} is required in connected mode`,
        });
      }
    }
  });

const parsed = envSchema.safeParse(import.meta.env);

if (!parsed.success) {
  throw new Error(`Invalid frontend environment: ${parsed.error.message}`);
}

export const env = {
  authMode: parsed.data.VITE_AUTH_MODE,
  dataMode: parsed.data.VITE_DATA_MODE,
  projectsDataMode: parsed.data.VITE_PROJECTS_DATA_MODE ?? parsed.data.VITE_DATA_MODE,
  apiBaseUrl: parsed.data.VITE_API_BASE_URL.replace(/\/$/, ""),
  firebase: {
    apiKey: parsed.data.VITE_FIREBASE_API_KEY ?? "",
    authDomain: parsed.data.VITE_FIREBASE_AUTH_DOMAIN ?? "",
    projectId: parsed.data.VITE_FIREBASE_PROJECT_ID ?? "",
    storageBucket: parsed.data.VITE_FIREBASE_STORAGE_BUCKET,
    appId: parsed.data.VITE_FIREBASE_APP_ID ?? "",
  },
} as const;
