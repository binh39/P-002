import { type CSSProperties, useState } from "react";

type BranchScenario = "standard" | "free" | "both";

interface SourceLine {
  number: number;
  code: string;
  covered: boolean;
}

const statementLines: SourceLine[] = [
  { number: 1, code: "def shipping_fee(total):", covered: true },
  { number: 2, code: "    fee = 30", covered: true },
  { number: 3, code: "    if total >= 500:", covered: true },
  { number: 4, code: "        fee = 0", covered: false },
  { number: 5, code: "    return fee", covered: true },
];

const scenarios: Record<
  BranchScenario,
  {
    label: string;
    input: string;
    result: string;
    trueCovered: boolean;
    falseCovered: boolean;
  }
> = {
  standard: {
    label: "Standard order",
    input: "assert shipping_fee(100) == 30",
    result: "30",
    trueCovered: false,
    falseCovered: true,
  },
  free: {
    label: "Free shipping",
    input: "assert shipping_fee(500) == 0",
    result: "0",
    trueCovered: true,
    falseCovered: false,
  },
  both: {
    label: "Both tests",
    input: "assert shipping_fee(100) == 30\nassert shipping_fee(500) == 0",
    result: "30 and 0",
    trueCovered: true,
    falseCovered: true,
  },
};

function Formula({
  symbol,
  numerator,
  denominator,
}: {
  symbol: string;
  numerator: string;
  denominator: string;
}) {
  return (
    <div
      className="coverage-math"
      aria-label={`${symbol} equals ${numerator} divided by ${denominator}`}
    >
      <var>{symbol}</var>
      <span>=</span>
      <span className="math-fraction">
        <span>{numerator}</span>
        <span>{denominator}</span>
      </span>
      <span>× 100%</span>
    </div>
  );
}

function CodeCoverage({ lines, label }: { lines: SourceLine[]; label: string }) {
  return (
    <div className="coverage-code-card">
      <div className="code-card-toolbar">
        <span>shipping.py</span>
        <span className="code-legend">
          <i /> Executed line
        </span>
      </div>
      <pre aria-label={label}>
        {lines.map((line) => (
          <span
            className={line.covered ? "code-line covered" : "code-line missed"}
            key={line.number}
          >
            <b>{line.number}</b>
            <code>{line.code}</code>
            <em aria-label={line.covered ? "Executed" : "Not executed"}>
              {line.covered ? "✓" : "—"}
            </em>
          </span>
        ))}
      </pre>
    </div>
  );
}

function StepLabel({ number, children }: { number: string; children: string }) {
  return (
    <div className="coverage-step-label">
      <span>{number}</span>
      <strong>{children}</strong>
    </div>
  );
}

export default function CoverageGuide() {
  const [scenario, setScenario] = useState<BranchScenario>("standard");
  const active = scenarios[scenario];
  const coveredBranches = Number(active.trueCovered) + Number(active.falseCovered);
  const branchLines: SourceLine[] = [
    { number: 1, code: "def shipping_fee(total):", covered: true },
    { number: 2, code: "    fee = 30", covered: true },
    { number: 3, code: "    if total >= 500:", covered: true },
    { number: 4, code: "        fee = 0", covered: active.trueCovered },
    { number: 5, code: "    return fee", covered: true },
  ];

  return (
    <div className="coverage-guide-page">
      <header className="coverage-guide-hero">
        <div>
          <span className="coverage-guide-eyebrow">Coverage fundamentals</span>
          <h1>Two core test coverage metrics</h1>
          <p>
            Statement coverage measures executed statements. Branch coverage measures whether each
            True/False path has been tested.
          </p>
        </div>
        <div className="coverage-score-preview" aria-label="Coverage score formula">
          <span>PromptOpt evaluation score</span>
          <strong>30% + 70%</strong>
          <div>
            <i className="statement-dot" /> Statement
            <i className="branch-dot" /> Branch
          </div>
        </div>
      </header>

      <section className="coverage-primary-grid" aria-label="Two primary coverage metrics">
        <article className="coverage-primary-card statement-primary-card">
          <div className="coverage-primary-title">
            <span className="coverage-level">C0</span>
            <div>
              <small>Metric one</small>
              <h2>Statement coverage</h2>
            </div>
          </div>
          <div className="metric-definition">
            <span>Definition</span>
            <p>The percentage of executable statements reached by the test suite at least once.</p>
            <strong>Answers: “Which code actually ran?”</strong>
          </div>
          <div className="metric-formula-block">
            <span>Formula</span>
            <Formula
              symbol="SC"
              numerator="Executed statements"
              denominator="Total executable statements"
            />
          </div>
        </article>

        <article className="coverage-primary-card branch-primary-card">
          <div className="coverage-primary-title">
            <span className="coverage-level">C1</span>
            <div>
              <small>Metric two</small>
              <h2>Branch coverage</h2>
            </div>
          </div>
          <div className="metric-definition">
            <span>Definition</span>
            <p>
              The percentage of decision paths such as <code>if</code>/<code>else</code> that the
              tests have taken.
            </p>
            <strong>Answers: “Have both True and False outcomes been tested?”</strong>
          </div>
          <div className="metric-formula-block">
            <span>Formula</span>
            <Formula
              symbol="BC"
              numerator="Executed branches"
              denominator="Total possible branches"
            />
          </div>
        </article>
      </section>

      <section className="coverage-example-section statement-example-section">
        <div className="coverage-section-heading">
          <span>01 · Statement coverage example</span>
          <h2>Every green line is an executed statement</h2>
          <p>
            The test <code>shipping_fee(100)</code> executes 4 of 5 statements. Executed lines are
            highlighted green with a ✓; line 4 stays dark to show the gap.
          </p>
        </div>

        <div className="coverage-example-flow">
          <article className="coverage-example-step test-step">
            <StepLabel number="1">Run the test case</StepLabel>
            <pre className="example-test-code">assert shipping_fee(100) == 30</pre>
            <p>
              Input 100 makes <code>total &gt;= 500</code> evaluate to False.
            </p>
          </article>
          <article className="coverage-example-step code-step">
            <StepLabel number="2">Inspect the executed code</StepLabel>
            <CodeCoverage lines={statementLines} label="Statement coverage example" />
          </article>
          <article className="coverage-example-step result-step">
            <StepLabel number="3">Apply the formula</StepLabel>
            <div className="coverage-result-card">
              <span className="result-label">Statement coverage</span>
              <div
                className="coverage-ring statement-ring"
                style={{ "--coverage": "80%" } as CSSProperties}
              >
                <strong>80%</strong>
                <span>4 / 5 statements</span>
              </div>
              <div className="compact-math">
                <span>SC</span> = <b>4</b> / 5 × 100% = <strong>80%</strong>
              </div>
              <p>
                Add <code>shipping_fee(500)</code> to execute line 4 and reach 100% statement
                coverage.
              </p>
            </div>
          </article>
        </div>
      </section>

      <section className="coverage-example-section branch-example-section">
        <div className="coverage-section-heading">
          <span>02 · Branch coverage example</span>
          <h2>The same code can take a different branch for each input</h2>
          <p>
            Select a test case. The code below highlights every executed line in green and updates
            the corresponding branch coverage.
          </p>
        </div>

        <div className="scenario-tabs" role="group" aria-label="Choose a test case">
          {(
            Object.entries(scenarios) as [BranchScenario, (typeof scenarios)[BranchScenario]][]
          ).map(([id, item]) => (
            <button
              className={scenario === id ? "active" : ""}
              key={id}
              onClick={() => setScenario(id)}
              type="button"
              aria-pressed={scenario === id}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="coverage-example-flow">
          <article className="coverage-example-step test-step">
            <StepLabel number="1">Choose and run a test case</StepLabel>
            <div className="branch-code-test">
              <pre>{active.input}</pre>
            </div>
            <p>Each choice creates a different execution path through the same code.</p>
          </article>
          <article className="coverage-example-step code-step">
            <StepLabel number="2">Track the executed lines</StepLabel>
            <CodeCoverage lines={branchLines} label="Code coverage for the selected test case" />
          </article>
          <article className="coverage-example-step result-step">
            <StepLabel number="3">Count branches and calculate</StepLabel>
            <div className="coverage-result-card branch-result-card">
              <span className="result-label">Branch coverage</span>
              <div
                className="coverage-ring branch-ring"
                style={{ "--coverage": `${coveredBranches * 50}%` } as CSSProperties}
              >
                <strong>{coveredBranches * 50}%</strong>
                <span>{coveredBranches} / 2 branches</span>
              </div>
              <div className="compact-math">
                <span>BC</span> = <b>{coveredBranches}</b> / 2 × 100% ={" "}
                <strong>{coveredBranches * 50}%</strong>
              </div>
              <dl>
                <div>
                  <dt>Test result</dt>
                  <dd>{active.result}</dd>
                </div>
                <div>
                  <dt>True branch</dt>
                  <dd className={active.trueCovered ? "metric-covered" : "metric-missing"}>
                    {active.trueCovered ? "✓ Executed" : "— Not executed"}
                  </dd>
                </div>
                <div>
                  <dt>False branch</dt>
                  <dd className={active.falseCovered ? "metric-covered" : "metric-missing"}>
                    {active.falseCovered ? "✓ Executed" : "— Not executed"}
                  </dd>
                </div>
              </dl>
            </div>
          </article>
        </div>
      </section>

      <section className="coverage-takeaway">
        <div>
          <span>Remember</span>
          <h2>100% statement coverage does not guarantee 100% branch coverage.</h2>
          <p>
            A test can execute an <code>if</code> line while checking only one outcome. Good tests
            cover the main behavior, edge cases, and error paths.
          </p>
        </div>
        <div className="score-equation" aria-label="Project evaluation score formula">
          <span>Evaluation score</span>
          <strong>Score = 0.3 × SC + 0.7 × BC</strong>
          <small>
            Branch coverage has more weight because it reflects execution-path diversity.
          </small>
        </div>
      </section>
    </div>
  );
}
