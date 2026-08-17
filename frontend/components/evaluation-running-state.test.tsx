import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { EvaluationRunningState } from "./evaluation-running-state";

describe("EvaluationRunningState", () => {
  it("explains the real indeterminate benchmark work without fake progress", () => {
    const html = renderToStaticMarkup(<EvaluationRunningState />);

    expect(html).toContain("Running evaluation benchmark…");
    expect(html).toContain("Running 5 benchmark cases through the full TraceLens");
    expect(html).toContain("typically takes around 3–4 minutes");
    expect(html).toContain("What&#x27;s happening?");
    expect(html).toContain("activity-rail running");
    expect(html).not.toMatch(/\d+%/);
  });
});
