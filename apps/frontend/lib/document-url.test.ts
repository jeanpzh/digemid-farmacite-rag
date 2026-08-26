import assert from "node:assert/strict";
import test from "node:test";

import { getDocumentPdfUrl } from "./document-url";

test("builds the same-origin PDF endpoint for a citation document", () => {
  assert.equal(
    getDocumentPdfUrl("42", "version/abc"),
    "/api/v1/documents/42/pdf?version=version%2Fabc",
  );
});

test("does not build a preview URL for unknown citation identity", () => {
  assert.equal(getDocumentPdfUrl("unknown", "unknown"), null);
});
