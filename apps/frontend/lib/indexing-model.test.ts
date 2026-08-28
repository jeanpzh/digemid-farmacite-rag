import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's strip-types test runner needs the explicit extension.
import { getIndexingSummary } from "./indexing-model.ts";

test("summarizes indexed documents for the run status strip", () => {
  const summary = getIndexingSummary([
    { status: "indexed" },
    { status: "indexed" },
    { status: "processing" },
    { status: "queued" },
  ]);

  assert.deepEqual(summary, {
    completed: 2,
    total: 4,
    percent: 50,
  });
});

test("returns a safe empty summary when no documents are available", () => {
  assert.deepEqual(getIndexingSummary([]), {
    completed: 0,
    total: 0,
    percent: 0,
  });
});
