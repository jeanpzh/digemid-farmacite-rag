import assert from "node:assert/strict";
import test from "node:test";

import { getExplicitPdfProp } from "./pdf-page";

test("omits the explicit pdf prop when the Page should use Document context", () => {
  assert.deepEqual(getExplicitPdfProp(undefined), {});
});

test("passes a cached PDF document explicitly", () => {
  const document = { id: "cached-pdf" };

  assert.deepEqual(getExplicitPdfProp(document), { pdf: document });
});
