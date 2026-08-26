export const MIN_PDF_SCALE = 0.75;
export const MAX_PDF_SCALE = 1.75;

export function getAdjacentPdfPage(
  currentPage: number,
  offset: number,
  totalPages: number,
) {
  return Math.min(Math.max(currentPage + offset, 1), Math.max(totalPages, 1));
}

export function changePdfScale(currentScale: number, delta: number) {
  const nextScale = currentScale + delta;
  return Math.min(
    Math.max(Number(nextScale.toFixed(2)), MIN_PDF_SCALE),
    MAX_PDF_SCALE,
  );
}
