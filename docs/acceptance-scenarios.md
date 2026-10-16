# Acceptance scenarios and worksheets

The [scenario pack](../fixtures/acceptance-scenarios.json) defines fourteen intended checks for the four cumulative book projects. They are specifications, not passing test results. Each names the relevant chapter, synthetic starting state, user action, deterministic storage expectation, model behavior to evaluate, and evidence needed.

Storage-only probe tests cover a small subset of these mechanisms. A scenario remains not run until its complete stated workflow is reproduced. Do not replace a local-model evaluation with a mocked reply or use a database assertion to claim the interface works.

The [worksheets](../templates/memory-worksheets.json) cover preferences, decisions, handoffs, incidents, and procedures. They are blank review aids, not a finalized database or import format. Fill them with synthetic data while learning. The complete application will define and validate its own versioned import contract.

## Evaluating a scenario

Record the scenario ID, exact code commit, fixture version/hash, runtime/model versions and model digest, request context, actual output, outcome, and limitations. Assess store behavior, prompt assembly, interface behavior, and generated content separately. Generated wording need not match one fixed sentence, but it must satisfy the factual and state boundaries of the case.

For model comparisons, keep the underlying question and conditions fixed between with-memory and without-memory runs. Record every attempt and denominator; do not rerun a failure until a convenient answer appears. Add held-out paraphrases separately from the development cases and report them as such.

Screenshots and public reports should contain only the synthetic scenario data. Local user memories, raw private chats, and backups do not belong in this repository.
