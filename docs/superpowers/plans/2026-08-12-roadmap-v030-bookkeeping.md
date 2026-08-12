# Specification Roadmap v0.3.0 Bookkeeping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the specification roadmap reflect the already-published immutable `v0.3.0` release.

**Architecture:** This is documentation-only bookkeeping in `ROADMAP.md`. It changes no normative contract, schema, fixture, package, or release artifact.

**Tech Stack:** Markdown, repository validator, GitHub pull request workflow.

## Global Constraints

- The current public immutable specification release is `v0.3.0`.
- The release tag targets commit `cd8f198c68b849eb8ed018a894670a0904c2181d`.
- Python and PHP stable-pin work remains downstream and unchecked.
- Do not rewrite historical release notes or normative specification content.

---

### Task 1: Correct the roadmap release state

**Files:**
- Modify: `ROADMAP.md:24-28`
- Modify: `ROADMAP.md:84-116`

- [ ] **Step 1: Update the current public release**

Change the section 4 release bullet to say that `v0.3.0` is the current public immutable specification release.

- [ ] **Step 2: Mark the completed v0.3.0 gates**

Keep item 1 as completed and mark items 2 and 3 completed. State that the exact release commit was `cd8f198c68b849eb8ed018a894670a0904c2181d`, tag-context CI passed, and the immutable GitHub release was published. Keep items 4 and 5 unchecked because adapter stable-pin work is still pending.

- [ ] **Step 3: Validate and inspect the diff**

Run:

```bash
git diff --check
python tools/validate_repository.py
```

Expected: both commands exit successfully and the diff contains only the intended roadmap bookkeeping.

- [ ] **Step 4: Commit the roadmap update**

```bash
git add ROADMAP.md
git commit -m "docs: mark specification v0.3.0 released"
```

### Task 2: Review and publish the roadmap PR

- [ ] **Step 1: Run the local review loop**

Review the Markdown diff against `origin/main`; fix any actionable finding and rerun validation.

- [ ] **Step 2: Push and open the PR**

Push `agent/roadmap-v030-complete`, open a PR targeting `main`, mark it ready, and add `@codex review`.

- [ ] **Step 3: Iterate until GitHub review and CI are clean**

Fix actionable review findings and failing checks, push each correction, and recheck the PR.
