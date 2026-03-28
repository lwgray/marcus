---
name: Coordination Incident Report
about: Report a multi-agent coordination failure or conflict during a Marcus experiment
title: '[INCIDENT] '
labels: incident, multi-agent, coordination
assignees: ''
---

## Overview

A brief summary of the coordination incident (1-2 sentences).

## Experiment Setup

- **Project:** [project name and description]
- **Number of Agents:** [e.g., 2]
- **Branch Strategy:** [e.g., all on main, separate branches]
- **Task Provider:** [e.g., Planka, GitHub, Linear]
- **Agent Roles:**
  - Agent 1: [role and assigned tasks]
  - Agent 2: [role and assigned tasks]

## What Each Agent Did

### Agent 1
Describe what Agent 1 built or modified, including specific files and approaches.

### Agent 2
Describe what Agent 2 built or modified, including specific files and approaches.

## The Conflict

Describe the incompatibility or coordination failure. What broke and why?

## Root Cause

What underlying issue caused the conflict? (e.g., missing conventions, shared file modification, no integration testing)

## Impact

- **Severity:** [Critical / High / Medium / Low]
- **What broke:** [e.g., application fails to load in browser]
- **Detection method:** [e.g., manual testing, agent notification, CI]
- **Time to detect:** [e.g., detected during experiment, discovered afterward]

## Contributing Factors

List the factors that contributed to this incident:

- [ ] Missing design specification (module system, conventions, etc.)
- [ ] No file ownership rules
- [ ] No branch isolation
- [ ] No integration validation
- [ ] Agent modified another agent's code
- [ ] Agent ignored conflict notification
- [ ] No runtime verification in target environment
- [ ] Worker prompt prioritized speed over correctness
- [ ] Other: ___

## Resolution

How was (or should) the conflict be resolved?

## Recommendations

What changes to Marcus, worker prompts, or experiment setup would prevent this?

1.
2.
3.

## Logs / Evidence

<details>
<summary>Relevant agent output or logs (click to expand)</summary>

```
Paste logs here
```

</details>

## Checklist

- [ ] I have identified which agents were involved
- [ ] I have described what each agent did
- [ ] I have identified the root cause
- [ ] I have proposed recommendations to prevent recurrence
