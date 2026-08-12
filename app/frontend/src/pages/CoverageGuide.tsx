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
    label: "Đơn thường",
    input: "assert shipping_fee(100) == 30",
    result: "30",
    trueCovered: false,
    falseCovered: true,
  },
  free: {
    label: "Miễn phí",
    input: "assert shipping_fee(500) == 0",
    result: "0",
    trueCovered: true,
    falseCovered: false,
  },
  both: {
    label: "Cả hai test",
    input: "assert shipping_fee(100) == 30\nassert shipping_fee(500) == 0",
    result: "30 và 0",
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
    <div className="coverage-math" aria-label={`${symbol} bằng ${numerator} chia ${denominator}`}>
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
          <i /> Dòng đã chạy
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
            <em aria-label={line.covered ? "Đã chạy" : "Chưa chạy"}>{line.covered ? "✓" : "—"}</em>
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
          <h1>Hai thước đo cốt lõi của test coverage</h1>
          <p>
            Statement coverage đo những câu lệnh đã chạy. Branch coverage đo những hướng xử lý
            True/False đã được kiểm thử.
          </p>
        </div>
        <div className="coverage-score-preview" aria-label="Công thức điểm coverage">
          <span>Điểm đánh giá của PromptOpt</span>
          <strong>40% + 60%</strong>
          <div>
            <i className="statement-dot" /> Statement
            <i className="branch-dot" /> Branch
          </div>
        </div>
      </header>

      <section className="coverage-primary-grid" aria-label="Hai metric coverage chính">
        <article className="coverage-primary-card statement-primary-card">
          <div className="coverage-primary-title">
            <span className="coverage-level">C0</span>
            <div>
              <small>Metric thứ nhất</small>
              <h2>Statement coverage</h2>
            </div>
          </div>
          <div className="metric-definition">
            <span>Định nghĩa</span>
            <p>Phần trăm câu lệnh thực thi được mà bộ test đã chạy qua ít nhất một lần.</p>
            <strong>Trả lời: “Code nào đã thực sự được chạy?”</strong>
          </div>
          <div className="metric-formula-block">
            <span>Công thức</span>
            <Formula
              symbol="SC"
              numerator="Số statement đã chạy"
              denominator="Tổng statement thực thi được"
            />
          </div>
        </article>

        <article className="coverage-primary-card branch-primary-card">
          <div className="coverage-primary-title">
            <span className="coverage-level">C1</span>
            <div>
              <small>Metric thứ hai</small>
              <h2>Branch coverage</h2>
            </div>
          </div>
          <div className="metric-definition">
            <span>Định nghĩa</span>
            <p>
              Phần trăm các hướng rẽ của quyết định như <code>if</code>/<code>else</code> đã được đi
              qua.
            </p>
            <strong>Trả lời: “Mọi kết quả True và False đã được thử chưa?”</strong>
          </div>
          <div className="metric-formula-block">
            <span>Công thức</span>
            <Formula
              symbol="BC"
              numerator="Số branch đã đi qua"
              denominator="Tổng branch có thể đi"
            />
          </div>
        </article>
      </section>

      <section className="coverage-example-section statement-example-section">
        <div className="coverage-section-heading">
          <span>01 · Ví dụ Statement coverage</span>
          <h2>Mỗi dòng màu xanh là một statement đã chạy</h2>
          <p>
            Test <code>shipping_fee(100)</code> chạy 4 trên 5 statement. Toàn bộ dòng đã chạy được
            bôi xanh và đánh dấu ✓; dòng 4 chưa chạy được giữ màu tối để nhìn ra khoảng trống.
          </p>
        </div>

        <div className="coverage-example-flow">
          <article className="coverage-example-step test-step">
            <StepLabel number="1">Chạy test case</StepLabel>
            <pre className="example-test-code">assert shipping_fee(100) == 30</pre>
            <p>
              Input 100 làm điều kiện <code>total &gt;= 500</code> nhận giá trị False.
            </p>
          </article>
          <article className="coverage-example-step code-step">
            <StepLabel number="2">Quan sát code được thực thi</StepLabel>
            <CodeCoverage lines={statementLines} label="Ví dụ statement coverage" />
          </article>
          <article className="coverage-example-step result-step">
            <StepLabel number="3">Áp dụng công thức</StepLabel>
            <div className="coverage-result-card">
              <span className="result-label">Statement coverage</span>
              <div
                className="coverage-ring statement-ring"
                style={{ "--coverage": "80%" } as CSSProperties}
              >
                <strong>80%</strong>
                <span>4 / 5 statement</span>
              </div>
              <div className="compact-math">
                <span>SC</span> = <b>4</b> / 5 × 100% = <strong>80%</strong>
              </div>
              <p>
                Thêm test <code>shipping_fee(500)</code> để chạy dòng 4 và đạt 100% statement
                coverage.
              </p>
            </div>
          </article>
        </div>
      </section>

      <section className="coverage-example-section branch-example-section">
        <div className="coverage-section-heading">
          <span>02 · Ví dụ Branch coverage</span>
          <h2>Cùng một đoạn code, mỗi input có thể đi theo một nhánh khác</h2>
          <p>
            Chọn test case. Code bên dưới sẽ tô xanh toàn bộ những dòng thực sự được chạy và cập
            nhật tỷ lệ branch coverage tương ứng.
          </p>
        </div>

        <div className="scenario-tabs" role="group" aria-label="Chọn test case">
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
            <StepLabel number="1">Chọn và chạy test case</StepLabel>
            <div className="branch-code-test">
              <pre>{active.input}</pre>
            </div>
            <p>Mỗi lựa chọn tạo ra một đường thực thi khác nhau trong cùng đoạn code.</p>
          </article>
          <article className="coverage-example-step code-step">
            <StepLabel number="2">Theo dõi các dòng được thực thi</StepLabel>
            <CodeCoverage lines={branchLines} label="Code coverage theo test case đã chọn" />
          </article>
          <article className="coverage-example-step result-step">
            <StepLabel number="3">Đếm số nhánh và tính kết quả</StepLabel>
            <div className="coverage-result-card branch-result-card">
              <span className="result-label">Branch coverage</span>
              <div
                className="coverage-ring branch-ring"
                style={{ "--coverage": `${coveredBranches * 50}%` } as CSSProperties}
              >
                <strong>{coveredBranches * 50}%</strong>
                <span>{coveredBranches} / 2 branch</span>
              </div>
              <div className="compact-math">
                <span>BC</span> = <b>{coveredBranches}</b> / 2 × 100% ={" "}
                <strong>{coveredBranches * 50}%</strong>
              </div>
              <dl>
                <div>
                  <dt>Kết quả test</dt>
                  <dd>{active.result}</dd>
                </div>
                <div>
                  <dt>Nhánh True</dt>
                  <dd className={active.trueCovered ? "metric-covered" : "metric-missing"}>
                    {active.trueCovered ? "✓ Đã chạy" : "— Chưa chạy"}
                  </dd>
                </div>
                <div>
                  <dt>Nhánh False</dt>
                  <dd className={active.falseCovered ? "metric-covered" : "metric-missing"}>
                    {active.falseCovered ? "✓ Đã chạy" : "— Chưa chạy"}
                  </dd>
                </div>
              </dl>
            </div>
          </article>
        </div>
      </section>

      <section className="coverage-takeaway">
        <div>
          <span>Ghi nhớ</span>
          <h2>100% statement coverage chưa chắc là 100% branch coverage.</h2>
          <p>
            Một test có thể chạy qua dòng <code>if</code> nhưng chỉ kiểm tra một kết quả. Test tốt
            cần đi qua cả hành vi chính, trường hợp biên và đường lỗi.
          </p>
        </div>
        <div className="score-equation" aria-label="Công thức điểm đánh giá của dự án">
          <span>Evaluation score</span>
          <strong>Score = 0.4 × SC + 0.6 × BC</strong>
          <small>Branch được ưu tiên vì phản ánh độ đa dạng của các đường thực thi.</small>
        </div>
      </section>
    </div>
  );
}
