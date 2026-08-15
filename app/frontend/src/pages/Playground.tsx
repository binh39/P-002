import { useState } from "react";

import { IC } from "../components/Icons";

const card = {
  background: "#fff",
  borderRadius: 14,
  border: "1px solid #E8EBF5",
  boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
} as const;

const PROMPT_INIT = `You are an expert Python test engineer. Your goal is to generate comprehensive unit tests for the provided Python source code.

Guidelines:
- Use pytest as the testing framework
- Achieve maximum branch and statement coverage
- Mock external dependencies appropriately
- Include edge cases and boundary conditions

Generate tests that cover all code paths including error handling and edge cases.`;

const SOURCE_CODE = `# payment_service.py
from decimal import Decimal
from typing import Optional
import stripe
from .models import Transaction, PaymentMethod

class PaymentService:
    def __init__(self, api_key: str):
        self.client = stripe.Stripe(api_key)

    def process_payment(
        self,
        amount: Decimal,
        currency: str,
        payment_method_id: str,
        metadata: Optional[dict] = None
    ) -> Transaction:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if currency not in ["USD", "EUR", "GBP"]:
            raise ValueError(f"Unsupported currency: {currency}")

        try:
            charge = self.client.charges.create(
                amount=int(amount * 100),
                currency=currency.lower(),
                payment_method=payment_method_id,
                metadata=metadata or {},
            )
            return Transaction(
                id=charge.id,
                amount=amount,
                status="completed"
            )
        except stripe.StripeError as e:
            return Transaction(
                id=None,
                amount=amount,
                status="failed",
                error=str(e)
            )`;

const EXISTING_TESTS = `# test_payment_service.py (existing)
import pytest
from decimal import Decimal

def test_process_payment_success():
    service = PaymentService("sk_test_key")
    txn = service.process_payment(
        Decimal("99.99"), "USD", "pm_test_123"
    )
    assert txn.status == "completed"

def test_invalid_amount():
    service = PaymentService("sk_test_key")
    with pytest.raises(ValueError):
        service.process_payment(Decimal("-10"), "USD", "pm_test")
`;

const GENERATED_TESTS = `# Generated tests — EXP-047 · gpt-4o
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
import stripe

from payment_service import PaymentService
from models import Transaction


@pytest.fixture
def service():
    return PaymentService("sk_test_abc123")


@pytest.fixture
def mock_stripe():
    with patch("payment_service.stripe") as mock:
        yield mock


class TestProcessPayment:
    def test_valid_usd_payment(self, service, mock_stripe):
        mock_stripe.charges.create.return_value = MagicMock(id="ch_001")
        txn = service.process_payment(
            Decimal("50.00"), "USD", "pm_test_001"
        )
        assert txn.status == "completed"
        assert txn.amount == Decimal("50.00")

    def test_valid_eur_payment(self, service, mock_stripe):
        mock_stripe.charges.create.return_value = MagicMock(id="ch_002")
        txn = service.process_payment(
            Decimal("25.00"), "EUR", "pm_test_002"
        )
        assert txn.status == "completed"

    def test_valid_gbp_payment(self, service, mock_stripe):
        mock_stripe.charges.create.return_value = MagicMock(id="ch_003")
        txn = service.process_payment(
            Decimal("75.00"), "GBP", "pm_test_003"
        )
        assert txn.status == "completed"

    def test_zero_amount_raises(self, service):
        with pytest.raises(ValueError, match="Amount must be positive"):
            service.process_payment(Decimal("0"), "USD", "pm_test")

    def test_negative_amount_raises(self, service):
        with pytest.raises(ValueError, match="Amount must be positive"):
            service.process_payment(Decimal("-50.00"), "USD", "pm_test")

    def test_unsupported_currency_raises(self, service):
        with pytest.raises(ValueError, match="Unsupported currency: JPY"):
            service.process_payment(Decimal("100"), "JPY", "pm_test")

    def test_stripe_error_returns_failed(self, service, mock_stripe):
        mock_stripe.charges.create.side_effect = stripe.StripeError("Card declined")
        txn = service.process_payment(Decimal("50"), "USD", "pm_test")
        assert txn.status == "failed"
        assert txn.id is None
        assert "Card declined" in txn.error

    def test_metadata_passed_correctly(self, service, mock_stripe):
        mock_stripe.charges.create.return_value = MagicMock(id="ch_004")
        metadata = {"order_id": "ORD-123", "customer": "usr_456"}
        service.process_payment(Decimal("30"), "USD", "pm_test", metadata)
        call_kwargs = mock_stripe.charges.create.call_args[1]
        assert call_kwargs["metadata"] == metadata

    def test_empty_metadata_defaults_to_empty_dict(self, service, mock_stripe):
        mock_stripe.charges.create.return_value = MagicMock(id="ch_005")
        service.process_payment(Decimal("10"), "USD", "pm_test")
        call_kwargs = mock_stripe.charges.create.call_args[1]
        assert call_kwargs["metadata"] == {}
`;

const metrics = [
  {
    label: "Branch",
    value: "87.3%",
    change: "+12.1%",
    positive: true,
    color: "#4F6EF7",
  },

  {
    label: "Statement",
    value: "93.1%",
    change: "+8.4%",
    positive: true,
    color: "#8B5CF6",
  },

  { label: "Tokens", value: "2,847", change: null, color: "#F59E0B" },

  { label: "Cost", value: "$0.043", change: null, color: "#10B981" },

  { label: "Latency", value: "1.84s", change: null, color: "#6B7280" },
];

export default function Playground() {
  const [prompt, setPrompt] = useState(PROMPT_INIT);

  const [activeTab, setActiveTab] = useState<"source" | "tests">("source");

  const [running, setRunning] = useState(false);

  const [ran, setRan] = useState(true);

  const handleRun = () => {
    setRunning(true);

    setTimeout(() => {
      setRunning(false);
      setRan(true);
    }, 1800);
  };

  return (
    <div
      style={{
        padding: "24px 28px",
        height: "calc(100vh - 56px)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 18,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 20,
              fontWeight: 700,
              color: "#0F1117",
              margin: 0,
              letterSpacing: "-0.02em",
            }}
          >
            Prompt Playground
          </h1>
          <p style={{ color: "#9CA3AF", fontSize: 13, margin: "3px 0 0" }}>
            Experiment interactively · EXP-047 · GPT-4o
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={() => {
              void navigator.clipboard.writeText(prompt);
              window.alert("Prompt cloned to clipboard.");
            }}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 16px",

              background: "#fff",
              border: "1px solid #E8EBF5",
              borderRadius: 8,

              fontSize: 13,
              fontWeight: 500,
              color: "#6B7280",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <IC.Copy /> Clone
          </button>
          <button
            onClick={handleRun}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 7,
              padding: "8px 18px",

              background: running ? "#9BA8F5" : "linear-gradient(135deg, #4F6EF7, #7C3AED)",

              color: "#fff",
              border: "none",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,

              cursor: running ? "not-allowed" : "pointer",
              fontFamily: "inherit",
            }}
          >
            {running ? (
              <>
                <IC.RefreshCw /> Running...
              </>
            ) : (
              <>
                <IC.Play /> Run Tests
              </>
            )}
          </button>
        </div>
      </div>

      {/* 3-column grid */}
      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 14,
          minHeight: 0,
        }}
      >
        {/* Col 1: Prompt editor */}
        <div
          style={{
            ...card,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid #F0F1F5",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span style={{ fontSize: 13, fontWeight: 600, color: "#0F1117" }}>Prompt Editor</span>
            <span
              style={{
                fontSize: 11,
                color: "#9CA3AF",
                background: "#F0F1F5",
                padding: "2px 7px",
                borderRadius: 5,
              }}
            >
              {prompt.split(" ").length} words
            </span>
          </div>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            style={{
              flex: 1,
              width: "100%",
              padding: "16px 18px",

              border: "none",
              outline: "none",
              resize: "none",

              fontFamily: "JetBrains Mono, monospace",
              fontSize: 12,

              lineHeight: 1.7,
              color: "#374151",
              background: "transparent",
            }}
          />
          <div
            style={{
              padding: "10px 18px",
              borderTop: "1px solid #F0F1F5",
              background: "#FAFBFF",
              display: "flex",
              gap: 10,
            }}
          >
            <select
              style={{
                flex: 1,
                padding: "6px 10px",
                border: "1px solid #E8EBF5",
                borderRadius: 7,
                fontSize: 12,
                fontFamily: "inherit",
                background: "#fff",
                color: "#374151",
              }}
            >
              <option>gpt-4o</option>
              <option>claude-sonnet-4-6</option>
              <option>gpt-4o-mini</option>
            </select>
            <select
              style={{
                padding: "6px 10px",
                border: "1px solid #E8EBF5",
                borderRadius: 7,
                fontSize: 12,
                fontFamily: "inherit",
                background: "#fff",
                color: "#374151",
              }}
            >
              <option>T: 0.7</option>
              <option>T: 0.5</option>
              <option>T: 1.0</option>
            </select>
          </div>
        </div>

        {/* Col 2: Source code + existing tests */}
        <div
          style={{
            ...card,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "10px 18px",
              borderBottom: "1px solid #F0F1F5",
              display: "flex",
              gap: 0,
            }}
          >
            {(["source", "tests"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  padding: "5px 14px",
                  borderRadius: 7,
                  fontSize: 12.5,
                  fontWeight: 500,

                  background: activeTab === tab ? "#EEF2FF" : "transparent",

                  color: activeTab === tab ? "#4F6EF7" : "#6B7280",

                  border: "none",
                  cursor: "pointer",
                  fontFamily: "inherit",
                }}
              >
                {tab === "source" ? "Source Code" : "Existing Tests"}
              </button>
            ))}
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "14px 18px" }}>
            <pre
              style={{
                margin: 0,
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 11.5,
                lineHeight: 1.7,
                color: "#374151",
                whiteSpace: "pre-wrap",
              }}
            >
              {activeTab === "source" ? SOURCE_CODE : EXISTING_TESTS}
            </pre>
          </div>
          <div
            style={{
              padding: "8px 18px",
              borderTop: "1px solid #F0F1F5",
              background: "#FAFBFF",
              display: "flex",
              gap: 10,
              alignItems: "center",
            }}
          >
            <span style={{ fontSize: 11.5, color: "#9CA3AF" }}>payment_service.py</span>
            <span
              style={{
                fontSize: 11,
                background: "#EEF2FF",
                color: "#4F6EF7",
                padding: "2px 7px",
                borderRadius: 5,
              }}
            >
              {activeTab === "source" ? "38 lines" : "14 lines"}
            </span>
          </div>
        </div>

        {/* Col 3: Results */}
        <div
          style={{
            ...card,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid #F0F1F5",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span style={{ fontSize: 13, fontWeight: 600, color: "#0F1117" }}>Generated Tests</span>
            {ran && (
              <span
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  fontSize: 11.5,
                  color: "#10B981",
                  fontWeight: 500,
                }}
              >
                <IC.Check /> 9 tests generated
              </span>
            )}
          </div>

          {/* Metrics strip */}
          {ran && (
            <div
              style={{
                padding: "10px 14px",
                borderBottom: "1px solid #F0F1F5",
                background: "#FAFBFF",
                display: "flex",
                gap: 6,
                flexWrap: "wrap",
              }}
            >
              {metrics.map(({ label, value, change, positive, color }) => (
                <div
                  key={label}
                  style={{
                    flex: 1,
                    minWidth: 60,
                    background: "#fff",
                    border: "1px solid #E8EBF5",

                    borderRadius: 8,
                    padding: "7px 10px",
                    textAlign: "center",
                  }}
                >
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 700,
                      color,
                      lineHeight: 1,
                    }}
                  >
                    {value}
                  </div>
                  <div style={{ fontSize: 10, color: "#9CA3AF", marginTop: 3 }}>{label}</div>
                  {change && (
                    <div
                      style={{
                        fontSize: 10,
                        color: positive ? "#10B981" : "#EF4444",
                        fontWeight: 500,
                        marginTop: 2,
                      }}
                    >
                      {change}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div style={{ flex: 1, overflow: "auto", padding: "14px 18px" }}>
            {ran ? (
              <pre
                style={{
                  margin: 0,
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 11,
                  lineHeight: 1.7,
                  color: "#374151",
                  whiteSpace: "pre-wrap",
                }}
              >
                {GENERATED_TESTS}
              </pre>
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "#9CA3AF",
                }}
              >
                <IC.Play />
                <p style={{ marginTop: 12, fontSize: 13 }}>Run a prompt to see generated tests</p>
              </div>
            )}
          </div>

          {ran && (
            <div
              style={{
                padding: "10px 18px",
                borderTop: "1px solid #F0F1F5",
                background: "#FAFBFF",
                display: "flex",
                gap: 8,
              }}
            >
              <button
                onClick={() => void navigator.clipboard.writeText(GENERATED_TESTS)}
                style={{
                  flex: 1,
                  padding: "7px 0",
                  background: "#fff",
                  border: "1px solid #E8EBF5",

                  borderRadius: 7,
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  color: "#374151",

                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 5,
                }}
              >
                <IC.Copy /> Copy
              </button>
              <button
                onClick={() => window.alert("Generated tests approved and sent to review.")}
                style={{
                  flex: 1,
                  padding: "7px 0",
                  background: "linear-gradient(135deg, #4F6EF7, #7C3AED)",
                  border: "none",

                  borderRadius: 7,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  color: "#fff",

                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 5,
                }}
              >
                <IC.Check /> Approve
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
