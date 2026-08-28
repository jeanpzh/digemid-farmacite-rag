export type IndexingStatus = "indexed" | "processing" | "queued" | "error";

export type IndexingSummaryInput = {
  status: IndexingStatus;
};

export function getIndexingSummary(documents: IndexingSummaryInput[]) {
  const completed = documents.filter(
    (document) => document.status === "indexed",
  ).length;
  const total = documents.length;

  return {
    completed,
    total,
    percent: total === 0 ? 0 : Math.round((completed / total) * 100),
  };
}
