import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { effectiveSubscriptionTier, hasSubscriptionFeature, isEntitledStatus, mailboxLimitFor } from "./stripeCore";

const tiers = ["free", "pro", "business"] as const;

describe("subscription entitlements", () => {
  for (const status of ["active", "trialing", "past_due"]) {
    it(`keeps paid rights while the subscription is ${status}`, () => {
      assert.equal(isEntitledStatus(status), true);
      assert.equal(effectiveSubscriptionTier("pro", status), "pro");
      assert.equal(effectiveSubscriptionTier("business", status), "business");
    });
  }

  for (const status of ["canceled", "unpaid", "incomplete", "incomplete_expired", "paused"]) {
    it(`falls back to Free while the subscription is ${status}`, () => {
      assert.equal(isEntitledStatus(status), false);
      for (const tier of tiers) {
        assert.equal(effectiveSubscriptionTier(tier, status), "free");
        assert.equal(mailboxLimitFor(tier, status), 1);
        assert.equal(hasSubscriptionFeature(tier, status, "automatic_actions"), false);
        assert.equal(hasSubscriptionFeature(tier, status, "advanced_rules"), false);
      }
    });
  }

  it("applies the Free, Pro and Business feature grid", () => {
    assert.equal(mailboxLimitFor("free", "active"), 1);
    assert.equal(mailboxLimitFor("pro", "active"), 3);
    assert.equal(mailboxLimitFor("business", "active"), 10);
    assert.equal(hasSubscriptionFeature("free", "active", "automatic_drafts"), false);
    assert.equal(hasSubscriptionFeature("pro", "active", "automatic_drafts"), true);
    assert.equal(hasSubscriptionFeature("pro", "active", "advanced_rules"), false);
    assert.equal(hasSubscriptionFeature("business", "active", "advanced_rules"), true);
    assert.equal(hasSubscriptionFeature("business", "active", "advanced_statistics"), true);
  });
});
