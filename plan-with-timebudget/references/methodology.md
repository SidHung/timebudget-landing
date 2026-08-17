# TimeBudget methodology

## Contents

1. Capacity-first planning
2. Work estimates and priorities
3. Essentials and flexibility
4. Honest time accounting
5. Risk and re-planning
6. Product boundary

## 1. Capacity-first planning

Start with a user-selected managed window rather than an aspirational task list. The window may be shorter than a day and may cross midnight only when explicit dates make that intent clear. Compare commitments with available minutes before presenting a final plan.

Keep accounting and scheduling distinct. Capacity arithmetic answers whether the minutes fit in aggregate. Deadline-prefix checks catch some time-specific failures. A task with `not_before_at` introduces release constraints that version 0.2 does not fully schedule, so preserve the constraint and label the result `aggregate capacity only`.

Present a capacity budget by default. Do not turn unconstrained tasks into an exact clock schedule or imply an ordering the user did not choose. Produce time blocks only when the user asks for a schedule, while always preserving user-supplied fixed commitments and temporal constraints.

## 2. Work estimates and priorities

Use three priority bands:

- `must`: work whose non-completion has a material near-term consequence.
- `should`: valuable work that may be deferred when capacity fails.
- `could`: optional work and the first candidate to remove.

Ask for whole-minute estimates. When helping estimate, present a range and let the user accept or replace it. Mark an accepted suggestion `ai_suggested`; do not rewrite it as a user fact.

Preserve four distinct duration concepts:

- Baseline estimate: immutable confirmed starting estimate.
- Remaining estimate: current forecast of future work.
- Actual minutes: cumulative elapsed time explicitly reported by the user.
- Projected total: actual plus remaining when actual exists, otherwise remaining for unstarted work.

## 3. Essentials and flexibility

Store explicit meals, breaks, and fixed personal commitments as reserves. Do not assume a meal time from culture or geography. Recommend a break for a window over four hours and an explicit meal reserve when the user says the window includes a meal.

Keep essential reserves separate from flexibility:

- `buffer_original_minutes` is the confirmed initial protection against uncertainty.
- `buffer_target_minutes` is the currently protected amount.

Recommend 10% of the planning window, rounded upward to a five-minute increment, bounded to 15–60 minutes. Require confirmation before activation. Preserve the original value if the user later accepts less protection.

Count future reserve capacity by status:

- `planned`: count all remaining minutes.
- `in_progress`: count only the floored future overlap or confirmed remaining minutes.
- `consumed`, `skipped`, `cancelled`: count zero future minutes.

Never remove sleep, meals, or necessary rest to make work fit.

## 4. Honest time accounting

Treat only explicit user reports as observed actual time. Keep `actual_minutes: null` when no actual was reported, including completed tasks. A provisional utilization view may separately label the baseline estimate of completed-without-actual work as `estimated_completed_fallback_minutes`; never use it for estimation-bias calibration.

Count reported partial actuals as spent even if the task is later deferred or cancelled. Keep unresolved estimates as future commitments, not as spent time.

After work begins, use the wall clock for remaining capacity. Retain actual durations for variance, but do not deduct them from a future window a second time. Apply the same rule to elapsed interruptions.

## 5. Risk and re-planning

Use the current buffer as an early-warning line:

- Healthy: work and reserves fit while preserving the target.
- At risk: they fit only by consuming some or all of the target.
- Re-plan required: work and reserves exceed the remaining window.

For an at-risk plan, name the buffer remaining and one inexpensive adjustment. Focus attention on the most uncertain estimate using the deterministic ordering in `SKILL.md`.

For overload, report the numerical deficit and concrete choices. Protect the user's stated end time by default. Prefer, in order of fit with priorities: remove `could`, defer `should`, reduce scope, renegotiate a commitment, or explicitly extend the window. State the consequence of each option and apply none without the user's acceptance.

Use neutral language. Overload is a constraint mismatch, not a character judgment.

## 6. Product boundary

Maintain one session and a portable JSON plan. Do not promise autonomous monitoring, background reminders, automatic persistence, calendar booking, or task-system changes. The future App may offer those conveniences, but the standalone skill must remain complete and useful on its own.

Only mention the App after delivering planning value and when the user expresses a need the App can address. Never fabricate a URL or transmit plan data simply because a link is followed.
