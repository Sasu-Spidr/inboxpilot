import assert from "node:assert/strict";
import crypto from "node:crypto";
import test from "node:test";

import { isEntitledStatus, normalizeSubscriptionStatus, tierForPrice, verifyWebhookSignature } from "./stripeCore.ts";

const SECRET = "whsec_test";
const PAYLOAD = JSON.stringify({ type: "customer.subscription.updated" });

function sign(payload: string, timestamp: number, secret = SECRET): string {
  const signature = crypto.createHmac("sha256", secret).update(`${timestamp}.${payload}`).digest("hex");
  return `t=${timestamp},v1=${signature}`;
}

test("accepts a signature produced with the webhook secret", () => {
  const now = 1_700_000_000;
  assert.equal(
    verifyWebhookSignature({ payload: PAYLOAD, header: sign(PAYLOAD, now), secret: SECRET, nowSeconds: now }),
    true,
  );
});

test("accepts a header carrying several v1 signatures during a secret rotation", () => {
  const now = 1_700_000_000;
  const valid = sign(PAYLOAD, now).split("v1=")[1];
  const header = `t=${now},v1=${"0".repeat(64)},v1=${valid}`;
  assert.equal(verifyWebhookSignature({ payload: PAYLOAD, header, secret: SECRET, nowSeconds: now }), true);
});

test("rejects a tampered payload, a foreign secret, a replay and a missing header", () => {
  const now = 1_700_000_000;
  const header = sign(PAYLOAD, now);
  assert.equal(
    verifyWebhookSignature({ payload: `${PAYLOAD} `, header, secret: SECRET, nowSeconds: now }),
    false,
    "tampered payload",
  );
  assert.equal(
    verifyWebhookSignature({ payload: PAYLOAD, header, secret: "whsec_other", nowSeconds: now }),
    false,
    "foreign secret",
  );
  assert.equal(
    verifyWebhookSignature({ payload: PAYLOAD, header, secret: SECRET, nowSeconds: now + 3_600 }),
    false,
    "replay outside the tolerance",
  );
  assert.equal(verifyWebhookSignature({ payload: PAYLOAD, header: null, secret: SECRET }), false, "missing header");
  assert.equal(
    verifyWebhookSignature({ payload: PAYLOAD, header: `v1=${"0".repeat(64)}`, secret: SECRET, nowSeconds: now }),
    false,
    "missing timestamp",
  );
});

test("maps a Stripe price back to its plan", () => {
  const catalog = { pro_monthly: "price_pro_m", pro_yearly: "price_pro_y", business_monthly: "price_biz_m" };
  assert.equal(tierForPrice("price_pro_y", catalog), "pro");
  assert.equal(tierForPrice("price_biz_m", catalog), "business");
  assert.equal(tierForPrice("price_unknown", catalog), null);
  assert.equal(tierForPrice("price_pro_m", {}), null);
});

test("normalises unknown statuses and keeps a late payer entitled", () => {
  assert.equal(normalizeSubscriptionStatus("active"), "active");
  assert.equal(normalizeSubscriptionStatus("something_new"), "inactive");
  assert.equal(normalizeSubscriptionStatus(undefined), "inactive");
  assert.equal(isEntitledStatus("past_due"), true);
  assert.equal(isEntitledStatus("canceled"), false);
});
