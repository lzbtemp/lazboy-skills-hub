---
name: lazboy-code-review
description: "Perform thorough code reviews following La-Z-Boy engineering standards. Covers code quality, security vulnerabilities, performance issues, testing gaps, and architectural concerns. Use when reviewing pull requests or auditing existing code."
version: "1.0.0"
category: Full Stack
tags: [fullstack, code-review, quality, standards]
---

# La-Z-Boy Code Review Skill

Systematic code review process for La-Z-Boy engineering teams.

**Reference files — load when needed:**
- `references/review-checklist.md` — comprehensive review checklist
- `references/severity-levels.md` — issue severity classification

**Scripts — run when needed:**
- `scripts/review_pr.py` — automated pre-review checks on a PR
- `scripts/complexity_report.py` — generate cyclomatic complexity report

---

## 1. Review Priorities (in order)

1. **Security** — vulnerabilities, credential exposure, injection risks
2. **Correctness** — logic errors, edge cases, race conditions
3. **Performance** — N+1 queries, unnecessary re-renders, memory leaks
4. **Maintainability** — readability, naming, complexity
5. **Testing** — coverage gaps, test quality
6. **Style** — formatting, conventions (lowest priority, automate this)

## 2. Security Checks

- [ ] No hardcoded secrets, API keys, or passwords
- [ ] SQL queries use parameterized statements
- [ ] User input is validated and sanitized
- [ ] Authentication/authorization checks on all endpoints
- [ ] No `eval()`, `dangerouslySetInnerHTML`, or `exec()` with user data
- [ ] Dependencies have no known CVEs (`npm audit` / `pip audit`)

## 3. Performance Checks

### Frontend
- [ ] No unnecessary re-renders (check useEffect dependencies)
- [ ] Large lists use virtualization
- [ ] Images are optimized and lazy-loaded
- [ ] Bundle size impact is reasonable

### Backend
- [ ] Database queries are optimized (no N+1)
- [ ] Appropriate caching is in place
- [ ] Async operations don't block the event loop
- [ ] Pagination is used for list endpoints

## 4. Code Quality Metrics

| Metric | Target | Action |
|---|---|---|
| Cyclomatic complexity | < 10 per function | Refactor |
| Function length | < 50 lines | Extract functions |
| File length | < 300 lines | Split module |
| Nesting depth | < 4 levels | Early returns |
| Test coverage | > 80% | Add tests |

## 5. Review Comment Templates

### Blocker
> 🔴 **BLOCKER**: This SQL query is vulnerable to injection. Use parameterized queries instead of string formatting.

### Suggestion
> 💡 **SUGGESTION**: Consider using `useMemo` here — this computation runs on every render and the input array could be large.

### Nitpick
> 📝 **NIT**: Variable name `d` is unclear. Consider `deploymentConfig` for readability.

## 6. Review Response Times

- **Critical/Hotfix PRs**: Review within 2 hours
- **Feature PRs**: Review within 1 business day
- **Refactoring PRs**: Review within 2 business days
- **Documentation PRs**: Review within 3 business days
