import assert from "node:assert/strict";
import test from "node:test";

import {
  getFigureTitlePrefix,
  sanitizeFigureFilename,
  splitLabelByLastDot,
} from "../../../../docs/eval-dashboard/assets/js/utils/text.js";

test("text helpers preserve plot-title and filename sanitization behavior", () => {
  assert.deepEqual(
    {
      titlePrefix: getFigureTitlePrefix("Accuracy (mean ± std) (4 grouped evals per cell)"),
      sanitizedFilename: sanitizeFigureFilename('  bad<>:"/\\|?* name.  '),
      splitLabel: splitLabelByLastDot("metric.section.score"),
    },
    {
      titlePrefix: "Accuracy",
      sanitizedFilename: "bad - name",
      splitLabel: "score",
    }
  );
});
