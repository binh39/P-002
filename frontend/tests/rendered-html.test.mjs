import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html", host: "localhost" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the TestGen product shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>TestGen Optimization Lab<\/title>/i);
  assert.match(html, /Move prompts from intuition to evidence\./);
  assert.match(html, /Create experiment/);
  assert.match(html, /Mutation score vs\. cost/);
  assert.match(html, /HUMAN GATE/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/);
});

test("product source connects all required API workflows", async () => {
  const [page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(page, /\/experiments/);
  assert.match(page, /\/candidates\/\$\{best\.id\}\/approve/);
  assert.match(page, /aria-label="Candidate Pareto scatter plot"/);
  assert.match(page, /Regression audit/);
  assert.match(layout, /\/og\.png/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
});
