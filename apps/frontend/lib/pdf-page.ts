export function getExplicitPdfProp<T>(pdf: T | undefined) {
  return pdf === undefined ? {} : { pdf };
}
