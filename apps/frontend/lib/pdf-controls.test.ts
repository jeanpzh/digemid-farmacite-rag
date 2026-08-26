import assert from "node:assert/strict";
import test from "node:test";

import {
  changePdfScale,
  getAdjacentPdfPage,
} from "./pdf-controls";

test("keeps page navigation inside the loaded PDF", () => {
  assert.equal(getAdjacentPdfPage(1, -1, 4), 1);
  assert.equal(getAdjacentPdfPage(2, 1, 4), 3);
  assert.equal(getAdjacentPdfPage(4, 1, 4), 4);
});

test("keeps zoom between the supported minimum and maximum", () => {
  assert.equal(changePdfScale(1, -10), 0.75);
  assert.equal(changePdfScale(1, 0.25), 1.25);
  assert.equal(changePdfScale(1.75, 0.25), 1.75);
});
