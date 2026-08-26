const MEDICINE_AFTER_ARTICLE =
  /(?:^|\s)(?:el|la|los|las)\s+([\p{L}][\p{L}-]*(?:\s+[\p{L}][\p{L}-]*)?\s+\d+(?:[.,]\d+)?\s*(?:mcg|mg|ml|g|%))/iu;
const MEDICINE_WITH_STRENGTH =
  /(?:^|\s)([\p{L}][\p{L}-]*\s+\d+(?:[.,]\d+)?\s*(?:mcg|mg|ml|g|%))/iu;

export function getConsultationTitle(question?: string) {
  const normalized = question?.trim().replace(/^¿/, "").replace(/\?$/, "");

  if (!normalized) {
    return "Nueva consulta";
  }

  const medicine =
    normalized.match(MEDICINE_AFTER_ARTICLE)?.[1] ??
    normalized.match(MEDICINE_WITH_STRENGTH)?.[1];
  if (medicine) {
    return medicine.charAt(0).toUpperCase() + medicine.slice(1);
  }

  const fallback = normalized.split(/\s+/).slice(0, 6).join(" ");
  return fallback.length < normalized.length ? `${fallback}…` : fallback;
}

export function getCitationDocumentType(filename: string) {
  const normalized = filename.toLocaleLowerCase("es");

  if (normalized.includes("inserto")) {
    return "Inserto";
  }
  if (normalized.includes("rotulad")) {
    return "Rotulado";
  }
  return "Ficha técnica";
}
