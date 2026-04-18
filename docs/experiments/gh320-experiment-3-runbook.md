# GH-320 Experiment 3 — 3-agent contract-based decomposition

| Field | Value |
|-------|-------|
| Status | Not yet run |
| Blocked by | Nothing (can run any time after PR #327 merges) |
| Motivation | Test whether contract-based decomposition maintains boundary discipline and clean merges when three agents work in parallel on a tightly-coupled problem, not just two |
| Success criterion | Contribution distribution avoids Single-Author Product verdict; clean merge across 3 worktrees; zero contract modifications |
| Related | GH-320 PR 2, Experiment 1 (2026-04-10, snake game, 2 agents, hand-crafted contract) |

## Why this experiment exists

Experiment 1 validated 2-agent contract-based decomposition on a tightly-coupled problem. Two agents produced a ~30/70 contribution split, clean merge, zero contract modifications — the first Marcus experiment on tight coupling that did not produce a Single-Author Product verdict.

**Unknowns at 3+ agents:**
- Does boundary discipline hold when the contract has three interface boundaries instead of two?
- Do transitive dependencies between contract interfaces cause cascading coordination failures?
- Does the "file ownership emerges from contract ownership" invariant still hold when three agents touch three distinct files?
- Does the contribution distribution stay balanced (33/33/34) or collapse into a Single-Author pattern?

Experiment 1 alone is not sufficient evidence to generalize contract-first decomposition to N-agent runs. This experiment is the second data point.

## Setup

Same Vite + React + TypeScript scaffold as Experiment 1. Three-way split along three natural contract boundaries:

- **Agent A — GameEngine**: implements `GameEngine` class (core game loop, state transitions, collision detection)
- **Agent B — Renderer**: implements `Renderer` class (pure rendering of GameState to DOM, no input handling)
- **Agent C — Controller**: implements `Controller` class (input handling, binds keyboard to engine, manages timing/game loop)

Contract file `src/types.ts` (hand-crafted, committed on main before any agent starts):

```typescript
export type Direction = 'up' | 'down' | 'left' | 'right';
export type Coord = { x: number; y: number };

export interface GameState {
  snake: Coord[];
  food: Coord;
  score: number;
  gameOver: boolean;
}

export interface GameEngine {
  tick(): GameState;
  setDirection(dir: Direction): void;
  reset(): void;
  getState(): GameState;
}

export interface Renderer {
  /** Render the game state to a container element. Pure: no mutation of state. */
  render(state: GameState, container: HTMLElement): void;
  /** Show game-over overlay. */
  showGameOver(score: number, container: HTMLElement): void;
}

export interface Controller {
  /** Bind keyboard events and start the game loop. Returns a cleanup function. */
  start(engine: GameEngine, renderer: Renderer, container: HTMLElement): () => void;
}
```

Note: three interfaces with explicit dependency ordering. `Controller` composes both `GameEngine` and `Renderer`, so it has the most coordination surface. This is the failure mode to watch — does Agent C stay within its contract or drift into rewriting the engine or renderer?

## Execution

```bash
# Prereqs: git, node 20+, Claude Code CLI
mkdir -p ~/experiments/snake-contract-3agent
cd ~/experiments/snake-contract-3agent

# Baseline
npm create vite@latest baseline -- --template react-ts
cd baseline
# Copy types.ts above to src/types.ts
git init && git add -A && git commit -m "baseline + contract"
cd ..

# Three worktrees off main
git -C baseline worktree add ../agent-a-engine main
git -C baseline worktree add ../agent-b-renderer main
git -C baseline worktree add ../agent-c-controller main
```

Run three Claude Code sessions in parallel:

**Agent A prompt:**
> Implement the `GameEngine` interface from `src/types.ts` in a new file `src/gameEngine.ts`. Do not touch any other file. Do not modify `src/types.ts`. The contract is read-only and authoritative.

**Agent B prompt:**
> Implement the `Renderer` interface from `src/types.ts` in a new file `src/renderer.ts`. Render the snake game state to a container element using simple DOM manipulation (divs with inline styles) or canvas. Do not touch any other file. Do not modify `src/types.ts`.

**Agent C prompt:**
> Implement the `Controller` interface from `src/types.ts` in a new file `src/controller.ts`. Bind arrow key events on the container, call `engine.setDirection()` on input, drive the game loop with `setInterval`, and call `renderer.render()` on each tick. Also wire up `src/App.tsx` and `src/main.tsx` to instantiate `GameEngine`, `Renderer`, and `Controller` and mount them to a container. Do not touch `gameEngine.ts`, `renderer.ts`, or `types.ts`.

## Measurements to capture

After all three agents complete, merge the worktrees and verify:

1. **Contribution distribution**: use Epictetus audit to check for Single-Author Product verdict. Target: ~33/33/34 split by lines of product code. Hard failure if any agent produced <10% of total.
2. **Contract adherence**: `git diff main..HEAD -- src/types.ts` should be empty. Any diff = contract modification = failed experiment.
3. **File boundary discipline**: each agent's worktree should only modify its owned file plus the shared scaffolding files in Agent C's case (App.tsx, main.tsx). Cross-boundary edits = boundary discipline failure.
4. **Clean merge**: three-way merge via octopus merge or sequential merges should produce zero conflicts. Contract-based boundaries should prevent conflicts by construction.
5. **Build status**: `tsc --noEmit` exit 0 after merge.
6. **Runtime check**: `npm run dev`, hit arrow keys, verify snake moves, food spawns, game-over fires.

## Expected outcomes and interpretation

### Hypothesis A (contract discipline holds at N=3)

Contribution distribution is roughly balanced. All three agents produce substantive code in their owned files. No contract modifications. Clean three-way merge. Snake game runs.

**Implication**: contract-based decomposition generalizes beyond 2 agents. Marcus can safely recommend contract-first for projects with 3+ agents on tightly-coupled problems.

### Hypothesis B (Single-Author Product re-emerges)

One agent (likely Agent C, the one with the most coordination surface) absorbs all the work. Agent A and/or B produce empty or trivial files. Or one agent silently edits another's contract.

**Implication**: contract-based decomposition has an N-agent scaling ceiling. Need to investigate whether the failure is:
- Contract design (3 interfaces not enough isolation; need 4+ or different shape)
- Prompt design (agents don't understand ownership)
- Fundamental (contracts can't carry enough information to isolate 3+ agents)

### Hypothesis C (partial success)

Two agents produce substantive code, one produces empty or trivial. Contract is not modified. Merge is clean.

**Implication**: closer to #267's original Single-Author observation than to experiment 1's result. Contract-based decomposition helps but doesn't fully solve N-agent coordination at N=3. Need to understand which contract interface failed to carry enough signal.

## What to do with the result

Whichever hypothesis fires, write the outcome to `docs/audit-reports/snake-contract-3agent-YYYY-MM-DD.json` in the Epictetus format used by prior audits. Update GH-320 with the finding. If hypothesis B or C fires, file a follow-up issue on what's next — likely "experiment 3b with 4 contract interfaces" or "contract amendment flow" (the open question from the #320 issue body).

## What this experiment does NOT test

- **LLM-generated contracts** — this uses a hand-crafted contract. Experiment 4 covers LLM-generated contracts.
- **The Marcus contract-first decomposer** — this runs Claude Code agents directly, not via Marcus. Experiment 4 covers the full Marcus pipeline.
- **Contract amendment mid-implementation** — if an agent discovers the contract is missing something, what happens? Out of scope. Separate experiment.

## Related

- GH-320 issue body, "Experiment 3" section
- `~/experiments/snake-contract-test/RESULT.md` — Experiment 1 result template
- Experiment 4 (`gh320-experiment-4-runbook.md`) — LLM-generated contract validation via Marcus pipeline
