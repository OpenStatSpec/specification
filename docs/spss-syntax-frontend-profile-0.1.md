# OpenStatSpec SPSS-like Syntax Frontend Profile 0.1

## Status and boundary

This optional frontend profile maps a deliberately small SPSS-like command
language to OpenStatSpec Transformation Plan 0.1. Its contract identifier is
`openstatspec-spss-syntax-frontend-v0.1`. It does not claim full IBM SPSS
Statistics syntax compatibility and MUST reject every command or form not
defined here.

An invocation supplies the exact source text, one input alias, and an ordered
input schema conforming to
[`../transformation/spss-syntax-frontend-0.1.schema.json`](../transformation/spss-syntax-frontend-0.1.schema.json).
Keywords are ASCII case-insensitive. Variable resolution is case-insensitive,
must yield exactly one input or previously created variable, and the canonical
plan stores its exact catalog spelling. Commands terminate with a period.
Single- and double-quoted strings are supported; a doubled matching quote is
the escaped quote. A leading `*` comment statement and the `COMMENT` command
are recognized only to produce `unsupported_spss_command`; inline
`/* ... */` produces `spss_syntax_error`. Macros, includes, locale-dependent
numbers, and dynamic command generation are outside v0.1.

## Supported commands

`RECODE source... (selectors = result) ... [INTO target...].` supports an
ordered source variable list. When `INTO` is present it MUST contain the same
number of targets as sources. Targets MUST be fresh, case-insensitively unique,
must not collide with any pre-command variable, and are paired positionally
with sources. The command lowers to one ordered `recode` operation per pair.
Every pair reads the pre-command state: no pair can observe a target created by
another pair in the same command.

A selector is a comma-separated typed literal list, an inclusive numeric
`lower THRU upper` range, or `SYSMIS`. A result is a typed literal, `SYSMIS`,
or `COPY`. `ELSE = result` is permitted once and must be the final clause.

With `INTO`, each plan operation uses `target_mode=create`; without it each
source is also its target and the mode is `replace`. An omitted `ELSE` lowers
to explicit `system_missing` for create and explicit `copy` for replace. An
explicit `ELSE` lowers to the plan's `unmatched` field and is not retained as a
rule. Because the v0.1 subset has no `STRING` declaration, a create operation
whose determined output type is string MUST fail with
`string_target_requires_declaration`.

`VARIABLE LABELS variable 'label' [variable 'label' ...].` lowers each pair to
one ordered `set_variable_label` operation.

`VALUE LABELS variable... value 'label' [value 'label' ...]
[/ variable... value 'label' ...].` supports ordered variable lists and slash
groups. Each group lowers to one ordered `replace_value_labels` operation per
variable, preserving group and variable source order. Every operation in the
command resolves against the pre-command schema and replaces the complete
value-label set of only its target variable. Numeric codes target numeric
variables; quoted string codes target string variables. Duplicate typed codes
are invalid.

Commands lower in source order. A later command may refer to a variable created
by an earlier `RECODE ... INTO` command. The frontend performs no data mutation,
SQL execution, branch operation, or Dolt commit.

## Failure contract

The frontend MUST produce no partial plan after any error. Stable diagnostics
are `spss_syntax_error`, `unsupported_spss_command`, `unknown_variable`,
`duplicate_else`, `else_not_last`, `mixed_result_types`, `type_mismatch`,
`system_missing_for_string`, `string_target_requires_declaration`,
`reserved_target_name`, and
`duplicate_value_label`. Diagnostics identify a source span but MUST NOT include
credentials or unrelated data values.

The exact source hash is SHA-256 of UTF-8 source after CRLF and CR are converted
to LF. Formatting, keyword case, or quoting differences therefore change the
source hash even when they lower to the same plan hash.

Machine-readable frontend cases are in
[`../conformance/spss-syntax-frontend-0.1.json`](../conformance/spss-syntax-frontend-0.1.json).
