# The Session Launcher — design, explained simply

**Status:** Draft, revision 3.
Revision 2 absorbed the four Codex findings from review pass 1.
Revision 3 absorbs a self-review pass that found the rev-2 fixes had introduced their own cracks — and that those cracks all trace to one root, now surfaced below as the central decision rather than patched over.
Nothing is built yet.

**Belongs to:** Epic #706 Phase 3 (session-model migration), ADR-0012 decisions D1, D3, D6, D7, D8, D11, and obligations O1 and O5.

---

## The one-sentence version

Today Marcus hires a worker for one chore and fires them.
We want workers who clock in once and keep taking chores until the work runs out.

## What changed in this revision, and why it matters

The first draft called the launcher a clean first step: "mostly deleting old code, the lease needs no change."
Review pass 1 (Codex) showed that framing is wrong, and the reason is the single most important thing in this document:

> **The launcher is not a small step. It is the switch that turns four sleeping bugs on at once.**

Every one of those four bugs is harmless *today* for the same reason: today a worker does one chore and is killed, so it cannot linger, cannot come back, cannot outlive anything.
The launcher removes the killing.
The moment workers live all day, four things that "cannot happen" start happening:

1. **Two workers finish the same chore.** Marcus reassigns a chore from a worker it *thinks* died — but under the launcher that worker is still alive and finishes anyway. Both hand in the work. (This is the exact bug the deferred D11 "fence" was written for. We deferred it because it *could not happen under the old model*. The launcher is what makes it possible.)
2. **Rejected work sneaks into `main`.** A worker keeps one workspace all day, so one branch holds many chores. The current merge grabs the *whole branch*, so a chore that was sent back can ride into `main` on the worker's *next* accepted chore. (Filed as #730.)
3. **Workers never go home.** A worker knows to stop today only because the runner kills it. Nothing else says "the board is empty." (Obligation in ADR line 69–84 / the D10 change removes the one signal that exists.)
4. **A worker's memory fills up and never empties.** One all-day worker accumulates context across every chore with no reset, until it slows down or runs out. (Obligation O5.)

So this document is no longer "ship the launcher, then tidy up."
It is: **build the safety pieces the launcher needs before it can run at all.**
*How many* of those pieces come first — in particular whether trustworthy recovery (D3) is a prerequisite or is deferred behind a throwaway measurement run — is the central open decision of this doc, posed in section **6b** and Decision **0**. Read those before treating the two-milestone order below as settled; the milestone split assumes the "defer D3" answer, which I no longer lean toward.

---

## What actually happens today

Marcus is a workshop.
The chores live on a board.

Right now, every time a chore needs doing:

1. Marcus starts a brand-new worker.
2. The worker takes exactly one chore.
3. The worker finishes it.
4. **The worker is killed.**
5. If there is more work, Marcus starts *another* brand-new worker.

That start-and-kill machinery is where four of Marcus's six worst bugs live.
Workers pile up. A watchdog kills healthy ones by mistake. Sometimes it starts workers in an endless loop.

## What we want instead

1. You say: *"run five workers."*
2. Five workers clock in, once.
3. Each one loops: **take a chore → do it → report it → take another.**
4. When the board is empty, they clock out.

Marcus does not start them, does not watch them, and does not kill them.
Marcus tracks each worker at exactly one level: **the lease** — which chore they hold, and when it was last touched.

Several bugs disappear here rather than getting fixed, because the machinery that caused them is gone.
But — per the section above — removing the killing also removes the thing that quietly prevented four *other* bugs. That is the real work.

---

## The pieces

### 1. The launcher — a small program *outside* Marcus

It starts N workers and then gets out of the way.
Deliberately dumb: it does not decide who does what, does not restart the dead, does not watch for trouble.

**Good news:** not built from scratch.
`dev-tools/experiments/runners/run_experiment.py` already starts workers today; the launcher is that file with the start-and-kill loop removed.

### 2. The pull loop — the instructions each worker follows

> Register once. Ask for a chore. Do it, report it, ask again.
> No chore? Wait a bit, ask again. Board drained? Stop.

**Good news:** `prompts/Agent_prompt.md` — the sheet real users copy — already teaches the continuous loop.
The sheet that says "do one chore then exit" is the experiment copy, and it is being deleted.
So the prompt work is mostly *deleting a wrong sheet*.

**But — correcting the first draft:** the "board drained? stop" line in the prompt is a *lie the prompt cannot make true on its own.* See piece 4.

**What a "worker" actually is — the load-bearing clarification.**
A worker is **not** one endless AI conversation that runs all day.
A worker is a **persistent identity and workspace-owner** running a small loop.
The loop is the harness: register once, then for each chore start a *fresh context*, do the chore, report, and reset for the next one.
The identity persists across chores; the conversation does not.
This is what lets the launcher stay dumb (it never reaches inside a chore) *and* keeps a worker's memory from growing without bound (each chore is a clean slate).
It is also why "register once" (piece 3 / O1) and "reset per chore" (O5) do not fight: identity is per-worker, context is per-chore.

### 3. The lease — Marcus's handle on a worker

It says: *this worker holds this chore, last heard from at this time.*

**This is where the first draft was wrong.**
The first draft said "no change needed to what a lease is."
That is only true under the old kill-after-one-chore model.
Under the launcher, the lease has to answer a question it never had to answer before: *when I reassign a chore because a worker went quiet, and the "quiet" worker turns out to be alive and finishes it, who wins?*
Today the answer was "the reassignment always wins, because the quiet worker was killed."
Under the launcher, nobody was killed, so **both can win**, which means neither does — the same chore ships twice, and its code merges twice.

Fixing that is the D3 → D11 work (piece 5).
The lease layer is not "no change." It is the largest deferred change this launcher forces.

### 4. The drain signal — a *server* change, not a prompt line

When the board is empty, workers must be told to go home.
The first draft put this in the instruction sheet. That cannot work, and here is the exact reason, verified in code:

- The only "you may exit" signal today is `should_exit` in `request_next_task` (`src/marcus_mcp/tools/task.py` ~2896–2942).
- It fires **only** when a live *experiment monitor* was started and has since stopped.
- Without that monitor, the same function explicitly tells workers to **retry forever** (~3003–3032).
- **This migration deletes the experiment monitor** (that is the D10 "a run leaves the core" change).

So after the migration, unless we build a replacement, a drained board leaves every worker polling until you kill them by hand.
The replacement is a **board-computed condition** — *no claimable tasks and no live leases* — returned by `request_next_task`, decided by the server, not by a model remembering to call a tool.
This is its own build item with its own test. It is not a prompt edit.

### 5. Trustworthy recovery, then the fence (D3 → D11)

This is the lease change piece 3 pointed at, and it is the reason the launcher cannot simply ship.

- **D3 — split "is it alive?" from "how long may it hold the chore?"** Today those are one dial, so detecting a dead worker is tied to how big its chore is. D3 makes "alive" a simple silence timeout and "how long" a separate budget. This is what makes recovery *trustworthy* — reliable enough that we can stop compensating for false alarms.
- **Delete the re-grant compensation.** Today, when a quiet worker's lease is recovered, its *next report recreates the lease* — Marcus's built-in apology for false recovery. That apology and any fence are contradictory: one says "recovery might be wrong, let them back in," the other says "recovery happened, they're out." Both cannot be true. Once D3 makes recovery reliable, we delete the apology.
- **Then D11 — the fence — enforced where it matters.** Not at the coordinator (the mistake that cost three review rounds in August) but at the *resource*: the DONE write and the merge into `main`. Note #730 below is the same fence seen from the merge side.

Until this piece lands, two live workers *can* finish one chore. The first run handles that by **measuring, not preventing** (see Milestone A).

**Why we cannot just "set a safe timeout" before D3 — the honest limit.**
An earlier version of this doc claimed the first run could make false recovery "rare by construction" with a generous timeout.
That is false, and it is worth being blunt about why, because it is exactly D3's reason to exist.
Before D3 the lease is **one dial** that means both "is the worker alive?" and "how long may it hold the chore?" at once.
Make that dial long and a genuinely-dead worker's chore sits unclaimed for the whole window — which directly breaks the acceptance-run test that a killed worker's chore is picked up promptly.
Make it short and a worker doing focused work for a few quiet minutes trips recovery *while alive* — the collision.
There is **no single value that avoids both.** That is precisely the knot D3 unties by splitting the one dial into two.
So Milestone A does not pretend to avoid the collision. It uses the existing short lease (so reclaim is timely and the kill-test works), **expects collisions, and counts them.** The count is the deliverable.

### 6. Safe merges before session-scoped workspaces (#730 → D1)

**D1** gives each worker one long-lived workspace for its whole shift, instead of a fresh one per chore.
That is where "small, stable, no churn" comes from — but it is also what lets one branch hold many chores, which is what lets rejected work ride into `main` (bug #2 at the top).

So **#730 — merge only the commit range of *this* chore, not the whole branch — must land before D1**, not after.
The first draft listed #730 as "related work." It is a prerequisite for session-scoped workspaces.
Correcting the first draft's other claim: the launcher does **not** require D1. Milestone A keeps per-chore workspaces (which dodges #730 entirely); D1 and #730 move together into Milestone B.

### 6b. The one crack under everything — and the decision it forces

Three separate problems keep surfacing every time this design is reviewed. They are the same problem wearing three coats, and the root is one sentence:

> **Before D3, the lease is not a trustworthy "is this worker alive?" signal — yet the launcher leans on lease-liveness for three different jobs.**

The three coats:

1. **The drain signal leans on it.** Piece 4 defines "done, go home" as *no claimable tasks and no live leases.* But if a head-down worker on the final chore lets its short lease lapse while still working, the chore flips back to claimable and an idle worker grabs it — a collision — instead of the clean wait-then-drain we described. The drain signal is only as reliable as the liveness signal underneath it, which pre-D3 is not reliable.
2. **Teardown of a *killed* worker's workspace has no owner.** Teardown-on-completion never fires for a worker that died mid-chore. The launcher is deliberately dumb (it does not watch or clean up), Marcus tracks only leases, and the dead worker cannot clean up after itself. So its worktree is orphaned — reviving #628 on exactly the kill path the acceptance run exercises.
3. **Recovery salvage fights teardown.** The next worker takes the chore in its *own* fresh workspace (it must, to keep the #730 dodge), so it cannot see the dead worker's partial work or its checkpoint commits. As written, the partial work is discarded *and* orphaned — which also makes the checkpoint duty (D8) buy nothing in Milestone A, since nothing can reach those commits.

**These do not have prose answers. They have a decision, and it is yours:**

- **Option A — D3 is a launcher prerequisite after all.** This is what Codex's review pass 1 said in its first finding, and three rounds of trying to design around it have not held. A real silence-timeout (D3's two dials) makes liveness trustworthy, which fixes coat 1 outright and makes coats 2–3 tractable (a genuinely-dead worker is detected, so *something* can own its cleanup and salvage). Cost: Milestone A gets bigger; the launcher is no longer a near-term step.
- **Option B — keep D3 in Milestone B, and accept all three as *stated* costs of an unsafe measurement run.** Then the doc must say, plainly, that the first run may: prematurely reclaim the final chore (not just mid-run chores); orphan the worktree of any worker killed mid-chore (so "no orphaned worktrees" is dropped from the acceptance criteria, or a one-off manual sweep owns it); and discard a killed worker's partial work on recovery (so the checkpoint duty is deferred out of Milestone A, because it is inert there). None of that is acceptable for real work — which is why Milestone A is throwaway-only.

**My read, after three review rounds:** the recurring failure of the "defer D3" plan is itself the finding. Every attempt to keep D3 in Milestone B has produced a fresh contradiction, because the launcher's core jobs *are* liveness jobs. I now lean **Option A** — bring D3 forward — even though it makes the first step larger, because Option B's honest form is "run something we know is broken in three ways and watch." The counter-argument for B is real (we cannot size D3/D11 without a measured collision rate), but coats 2 and 3 are *not* about the collision rate; they are plain breakage that measurement does not inform.

This is the decision I most need from you, and it supersedes the smaller build-order questions below.

### 7. The two carry-over pieces from the first draft (still true)

- **Non-Claude workers need their instruction files.** The machinery being deleted is the only code that writes `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`. Delete it carelessly and Codex/Gemini workers start blank and silently do nothing. The launcher keeps this one job.
- **The workspace path shape is a cross-repo contract.** Cost tracking (in the separate Cato repo) identifies workers by reading the `worktrees/<worker-id>` path. Rename it and cost tracking stops silently, in both repos. Keep the shape, or change Cato in lockstep.
- **Everyone wakes at once.** Idle workers are all told "wait 30 seconds" — the same 30. Five started together poll in lockstep forever. Add jitter — but only once a real loop exists to test it against.

---

## The build order — two milestones

The findings turn "what order?" from a preference into a safety requirement.
Here is the honest sequence.

### Milestone A — the instrumented first run *(explicitly NOT production-safe)*

The goal of Milestone A is **one real measured run**, not a shippable product.
It answers the two questions we currently guess at: how often does the two-workers collision actually fire, and does a worker's memory actually fill up on a real project?

- [ ] **O1 — survive a restart.** Persist worker registration and rehydrate it on the *lazy* path (the first `request_next_task` after restart), because the startup path never runs in the mode Marcus deploys in. *Its own PR, first.*
- [ ] **The drain signal (piece 4).** Board-computed "no claimable tasks and no live leases," returned by `request_next_task`. Server change, own test. *Required even for a first run — without it the run never ends.*
- [ ] **Per-chore context reset (O5, minimum viable).** The reset happens in the harness loop (piece 2) at the chore boundary it already has: each chore runs in a fresh context, the worker identity persists. Minimum viable = a clean context per chore; smarter compaction *within* a long chore is Milestone B. This is where the finding said "there is nowhere to reset" — the answer is the loop, not the launcher, and the boundary is per-chore, not per-turn, so it does not reintroduce the supervision we deleted.
- [ ] **The launcher.** `run_experiment.py` minus the start-and-kill loop, plus `--sessions N`. Keeps writing the instruction files. Inverts the current "exit after one turn" behaviour so the loop stays alive.
- [ ] **Per-chore workspace: create AND tear down.** Today a fresh workspace per chore is a side effect of the kill machinery we are deleting — and so is its cleanup. Milestone A must therefore *explicitly* create a fresh workspace + branch for each chore (reusing `run_experiment.py`'s existing worktree-creation) **and add teardown when the chore completes.** Without the teardown, long-lived workers reintroduce the #628 worktree explosion — the exact bug the migration exists to kill. Per-chore workspaces (not per-session) are also what let Milestone A dodge #730/D1; that dodge silently fails if a worker reuses one workspace across chores, so this item is load-bearing, not incidental.
- [ ] **One instruction sheet.** Delete the one-chore copy, keep the loop copy, extend the drift-guard test to pin the loop contract. *(The checkpoint duty from D8 is deliberately NOT added here — see 6b coat 3: in Milestone A a recovering worker gets a fresh workspace and cannot reach a dead worker's checkpoint commits, so the duty buys nothing until the salvage path exists in Milestone B. Adding it now would be cargo-culting a rule whose mechanism does not yet exist.)*
- [ ] **Jitter** on the retry interval (now there is a loop to test it against).
- [ ] **Short lease + record-only collision.** Keep the *existing* short lease so a genuinely-dead worker is reclaimed promptly (the acceptance kill-test needs this). Rely on the already-shipped record-only observation (`_observe_epoch_collision`, PR #731) to *count* collisions — it logs a stale completion but does not block it. Expect a nonzero count; that is the measurement, not a failure.

**What Milestone A explicitly does NOT guarantee, and the bounded damage if it happens:** two live workers *can* finish one chore, and Milestone A does not prevent it. Because each chore has its *own* workspace and branch, the worst case is a **double DONE-write and a double-merge of the *same* chore** — messy, possibly a merge conflict, but bounded and observed. It is *not* the "rejected work rides into `main`" case (#730), which per-chore workspaces rule out. Milestone A runs only on throwaway projects, behind the standing "no large experiments until Phase 3 lands" rule, precisely so this bounded mess never touches real work.

### Milestone B — production-safe sessions

Only after Milestone A has run and we have the numbers:

- [ ] **D3 — trustworthy recovery** (silence timeout + budget ceiling), then **delete the re-grant compensation**.
- [ ] **D11 — the fence**, enforced at the DONE write and the merge, sized to the collision rate Milestone A measured.
- [ ] **#730 — commit-range merge**, then **D1 — session-scoped workspaces**, in that order.
- [ ] **O5 — full context compaction** if Milestone A showed it is needed.

---

## The acceptance run (the end of Milestone A)

Start Marcus and three workers on a small project.

- All three take chores and finish them, without Marcus starting anything.
- Kill one worker mid-chore. Its lease expires and another worker picks the chore up.
- **Restart Marcus while all three are working.** They keep going. *(Fails today — this is O1.)*
- The board empties. All three stop on their own. *(Requires the drain signal, piece 4 — not the prompt. **Conditional on 6b:** the clean "wait for the last lease, then all exit" path holds only if liveness is trustworthy. Under Option B's short lease, the final chore can be prematurely reclaimed instead — an accepted Milestone-A degradation, not a bug.)*
- Cost tracking still attributes spend to the right worker. *(Requires the workspace path shape, piece 7.)*
- A completed worker's workspace is torn down; a *killed* worker's workspace is **6b coat 2** — its cleanup owner is the open decision, not a settled acceptance criterion.
- Any two-workers collision is **logged** (not necessarily prevented — that is Milestone B). This run uses the short lease, so a collision is plausible; whatever the count, it is the measurement D3/D11 will be sized against, not a pass/fail.

Note how many of these bullets now carry a "conditional on 6b" caveat. That is the tell: the acceptance run cannot be fully specified until 6b is decided. That is the honest state of this design, not an omission.

---

## Decisions I still need from you

**0. The big one — Option A or Option B in section 6b: is D3 a launcher prerequisite?**
This supersedes everything else here. Three review rounds say the "defer D3" plan keeps cracking because the launcher's core jobs are liveness jobs.
I lean **Option A** (bring D3 forward). If you pick B, the acceptance run and Milestone A shrink to "measure the collision rate on a throwaway project and accept three known breakages," which is a legitimate but narrower goal.

The three smaller choices below only matter once 0 is settled:

**1. When the board is empty, do workers wait or go home?**
Lean **go home** — smaller, and "wait forever" is hard to tell from "stuck."
(Either way, the *signal* is a server change per piece 4; this is only about what the worker does on receiving it.)

**2. If a worker dies, does the launcher start a replacement?**
Lean **no** — a dumb launcher is the whole point; restart logic is what caused the deleted bugs. You notice and restart.

**3. If — and only if — you pick Option B in Decision 0, is the two-milestone split the right risk trade?**
*(If you pick Option A, this question dissolves: D3 comes first and there is no unsafe measurement milestone to weigh.)*
Under Option B, Milestone A gets us a real measured run fast, at the stated cost that it is not production-safe.
The fuller-safety alternative is to fold D3, D11, and #730 into the first launcher and ship nothing until it is fully safe.
The pull toward measuring first is that we cannot size D11's fence without a real collision rate — but note that argument only defends the *collision* coat of 6b, not the orphaned-worktree or discarded-salvage coats, which measurement does not inform. That asymmetry is part of why Decision 0 now leans the other way.

---

## One thing I want to say plainly

The last large piece of this migration took three review rounds to discover its design contradicted itself, because nobody wrote the contract down first.
This document is that contract — and review pass 1 already did its job: it caught that the first draft's "clean first step" framing hid the fact that the launcher is what arms the very bug we deferred.
That correction is this revision.
If anything here is still vague, that vagueness is the risk. Say so, and I make it specific before any code.

---

## Related

- Epic [#706](https://github.com/lwgray/marcus/issues/706) — Phase 3 plan and checklist
- [ADR-0012](../architecture/adr/0012-session-model-migration.md) — D1 (workspaces), D3 (liveness), D6 (fixed worker count), D7 (one project per worker), D8 (checkpoints), D11 (the fence, deferred), obligations O1 (restart) and O5 (context)
- Issue [#730](https://github.com/lwgray/marcus/issues/730) — commit-range merge; **prerequisite for D1**, and the merge-side view of the D11 fence
- PR #731 — lease-ownership hardening; ships the record-only collision observation Milestone A relies on; the D11 amendment explains why the fence was deferred
- PR #732 — `retry_after`, where the jitter question is recorded
