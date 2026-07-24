# Contributing to OpenStatSpec

OpenStatSpec is a working draft. Contributions that make its source-faithful SPSS-to-relational contract clearer, testable, or implementable are welcome.

## Useful first contributions

- Propose a clarification when a mapping rule is ambiguous or incomplete. Describe the source behavior, the intended relational representation, and any fidelity risk.
- Add a small, lawful fixture that demonstrates a real SPSS dictionary or value edge case, along with the expected wide table and metadata outcome.
- Draft a dialect profile that states identifier, column, binary64, text, and row/value-size capabilities, plus the required preflight behavior.
- Report or contribute adapter support, including what source features it preserves and any machine-readable fidelity events it emits.
- Improve documentation, examples, or terminology when it helps an implementer apply the existing scope correctly.

## Scope guardrails

The standard preserves the source package's native rectangular dataset: one source dataset is one dedicated wide table, each case is a row, and each variable is a physical column. Metadata exists to preserve source semantics and exportability.

Do not propose a second data model as part of this contract. In particular, long-form cells, EAV/JSON value storage, automatic reshaping, splitting a source table, automatic harmonization, inferred respondent keys, and question/study/wave entities are outside scope.

If a relational target cannot faithfully represent a source dataset within its declared limits, the correct outcome is an atomic, machine-readable capability failure—not a silent transformation.

## How to propose a change

1. Check the relevant profile, schema outline, and example first.
2. Keep the proposal small and name the affected source behavior.
3. Explain the expected mapping and whether it changes conformance, fixtures, or a dialect capability declaration.
4. Include a minimal example or test fixture when practical.

There is no formal governance process in this draft yet. Clear, evidence-based proposals that preserve the strict scope are the best starting point.
