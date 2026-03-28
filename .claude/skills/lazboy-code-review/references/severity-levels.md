# Issue Severity Classification

Standardized severity levels for code review findings. Use these consistently across all reviews to set clear expectations and prioritize fixes.

---

## Severity Levels Overview

| Level | Label | PR Impact | Response Time | Icon |
|---|---|---|---|---|
| S0 | **Critical** | **Block merge** | Fix immediately | :red_circle: |
| S1 | **High** | **Block merge** | Fix before merge | :orange_circle: |
| S2 | **Medium** | **Request changes** | Fix in this PR or create follow-up ticket | :yellow_circle: |
| S3 | **Low** | **Approve with comments** | Address at author's discretion | :blue_circle: |
| S4 | **Info** | **No impact** | Optional improvement | :white_circle: |

---

## S0 — Critical

**Definition:** Issues that pose an immediate security risk, can cause data loss or corruption, or will break production systems. These must be resolved before the PR can be merged under any circumstances.

**Response Time:** Fix immediately. The reviewer should notify the author directly (Slack/Teams) in addition to leaving the PR comment.

**When to assign S0:**
- The change introduces a security vulnerability that is exploitable
- Production data could be lost, corrupted, or exposed
- The change will cause a service outage or crash loop
- Credentials, API keys, or secrets are committed to the repository

**Examples:**

| Category | Example |
|---|---|
| Security | SQL injection via string concatenation in a query |
| Security | Hardcoded AWS access key or database password in source code |
| Security | Authentication bypass allowing unauthenticated access to admin endpoints |
| Security | `dangerouslySetInnerHTML` with unsanitized user input (XSS) |
| Data | Migration that drops a column without backing up data |
| Data | Race condition that can cause double-charging a customer |
| Reliability | Infinite loop or recursion without a termination condition |
| Reliability | Unhandled promise rejection that crashes the Node.js process |

**Comment Template:**
```
:red_circle: **CRITICAL (S0)**: [Description of the issue]

**Risk**: [What can go wrong in production]
**Fix**: [Specific remediation steps]

This must be fixed before merge.
```

---

## S1 — High

**Definition:** Issues that will cause significant bugs, degrade performance materially, or violate important architectural or security principles. These should be fixed in the current PR before merging.

**Response Time:** Fix before merge. Author should address within the same business day.

**When to assign S1:**
- Logic errors that will cause incorrect behavior for users
- Missing authorization checks on sensitive operations
- Performance regressions that will be noticeable (N+1 queries on a list page)
- Missing error handling that will cause silent failures
- Breaking changes to a public API without versioning

**Examples:**

| Category | Example |
|---|---|
| Correctness | Off-by-one error that skips the last item in a paginated list |
| Correctness | Async function missing `await`, causing race conditions |
| Security | Missing CSRF protection on a state-changing endpoint |
| Security | Overly permissive CORS (`Access-Control-Allow-Origin: *` in production) |
| Performance | N+1 database queries in a list endpoint serving thousands of records |
| Performance | Loading an entire table into memory instead of using pagination |
| Architecture | Bypassing the service layer to make direct database calls from a controller |
| Error Handling | Catching and swallowing exceptions without logging or re-raising |

**Comment Template:**
```
:orange_circle: **HIGH (S1)**: [Description of the issue]

**Impact**: [How this affects users or the system]
**Suggestion**: [Recommended fix]
```

---

## S2 — Medium

**Definition:** Issues that are genuine problems but have limited blast radius. They should be addressed in this PR if the fix is straightforward. If the fix requires significant rework, create a follow-up ticket and reference it in the PR.

**Response Time:** Fix in this PR (preferred) or create a follow-up ticket with a due date within the current sprint.

**When to assign S2:**
- Missing tests for new business logic
- Moderate performance concerns (unnecessary re-renders, missing memoization)
- Error handling that works but is not robust
- Missing input validation on internal APIs
- Moderate code duplication that increases maintenance burden

**Examples:**

| Category | Example |
|---|---|
| Testing | New API endpoint with no unit or integration tests |
| Testing | Test that only covers the happy path, not error cases |
| Performance | React component re-rendering on every parent render without memoization |
| Performance | Missing database index on a column used in `WHERE` clauses |
| Validation | API endpoint that does not validate request body schema |
| Maintainability | Function with cyclomatic complexity over 15 |
| Maintainability | Copy-pasted logic in three places instead of a shared utility |
| Error Handling | Generic catch-all error handler that returns 500 for all failures |

**Comment Template:**
```
:yellow_circle: **MEDIUM (S2)**: [Description of the issue]

**Why it matters**: [Explanation]
**Suggestion**: [Recommended fix or follow-up]
```

---

## S3 — Low

**Definition:** Minor issues that do not affect functionality or performance but improve code quality, readability, or maintainability. The reviewer approves the PR but leaves these as suggestions.

**Response Time:** Address at the author's discretion. These are suggestions, not requirements.

**When to assign S3:**
- Naming that could be clearer
- Minor structural improvements
- Missing documentation on non-obvious code
- Opportunities to simplify with a language feature
- TODO comments without a ticket reference

**Examples:**

| Category | Example |
|---|---|
| Naming | Variable named `d` that should be `deploymentConfig` |
| Naming | Boolean named `status` that should be `isActive` |
| Structure | Nested ternary that would be clearer as an `if`/`else` |
| Structure | Long function that could be split but still works fine as-is |
| Documentation | Complex regex without a comment explaining what it matches |
| Documentation | Public utility function without a JSDoc/docstring |
| Simplification | Using `.filter().map()` where `.reduce()` or `.flatMap()` is cleaner |
| Simplification | Manual null check where optional chaining (`?.`) would suffice |

**Comment Template:**
```
:blue_circle: **LOW (S3)**: [Description of the suggestion]

**Suggestion**: [Recommended improvement]

_Non-blocking — approve as-is._
```

---

## S4 — Info

**Definition:** Observations, questions, knowledge sharing, or praise. These have no impact on the PR approval decision. Use these to share context, ask clarifying questions, or highlight good patterns.

**Response Time:** No action required. Author may respond or acknowledge.

**When to assign S4:**
- Asking a question to understand a design decision
- Sharing a relevant article, library, or pattern
- Pointing out a future opportunity (not relevant to this PR)
- Complimenting a well-written test or clean implementation
- Noting a minor style preference that is not covered by linting rules

**Examples:**

| Category | Example |
|---|---|
| Question | "Curious: why did you choose a Map here instead of a plain object?" |
| Knowledge | "FYI — the `structuredClone()` API is now available in all supported browsers and could replace the deep-clone utility here in a future PR." |
| Praise | "Nice use of discriminated unions here. This makes the state machine much clearer." |
| Future | "This module is growing — might be worth splitting in a future sprint." |
| Style | "I personally prefer `const` destructuring here, but either way is fine." |

**Comment Template:**
```
:white_circle: **INFO**: [Observation or question]
```

---

## Decision Matrix: When to Block a PR

Use this matrix to decide whether a finding should block the PR from merging.

```
Is there a security vulnerability?
  YES --> S0 Critical. Block.
  NO  --> Continue.

Will this cause data loss or corruption?
  YES --> S0 Critical. Block.
  NO  --> Continue.

Will this cause incorrect behavior for users?
  YES --> Is the fix straightforward (< 30 min)?
            YES --> S1 High. Block, fix now.
            NO  --> S1 High. Block, but discuss scope with author.
  NO  --> Continue.

Is there a meaningful performance regression?
  YES --> Is it on a hot path or user-facing?
            YES --> S1 High. Block.
            NO  --> S2 Medium. Request changes or follow-up ticket.
  NO  --> Continue.

Is test coverage missing for new logic?
  YES --> S2 Medium. Request changes.
  NO  --> Continue.

Is this a readability or style improvement?
  YES --> S3 Low or S4 Info. Approve with comment.
```

---

## Aggregation Rules

When a PR has multiple findings, use the highest severity to determine the overall review action:

| Highest Severity | Review Action |
|---|---|
| Any S0 | **Request changes.** Do not approve under any circumstances. |
| Any S1 | **Request changes.** Author must address before re-review. |
| Multiple S2 (3+) | **Request changes.** Too many medium issues suggest insufficient self-review. |
| 1-2 S2 | **Approve with comments** if fixes are straightforward and author is trusted. |
| Only S3/S4 | **Approve.** Leave comments for consideration. |

---

## Escalation Protocol

| Situation | Action |
|---|---|
| S0 found in code already merged to main | Immediately notify the tech lead and create a hotfix branch |
| Repeated S1 findings from the same author | Schedule a 1:1 to discuss patterns and offer pairing sessions |
| Disagreement on severity between author and reviewer | Involve a third reviewer or the tech lead to arbitrate |
| S0/S1 found during off-hours | Follow the on-call incident process for production-impacting issues |
