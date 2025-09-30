I want you to create detailed technical documentation that explains what actually happens inside Marcus when [SPECIFIC WORKFLOW/OPERATION] occurs. This documentation is for developers and system architects who need to understand the internal complexity and system coordination.

Requirements:

1. **Assume Zero Knowledge**: Explain every technical term, system name, and concept as if the reader has never seen Marcus before. Don't use jargon without defining it.

2. **Explain WHY Things Exist**: For every system, data structure, or process step, explain WHY it's necessary and what problem it solves. Don't just describe WHAT happens.

3. **Show Real Examples**: Use concrete examples with actual data structures, code snippets, and realistic scenarios rather than abstract descriptions.

4. **Reveal the Complexity**: Show how many systems are involved, what decisions are being made, and what intelligence is being applied. Make it clear this isn't simple CRUD operations.

5. **Use This Structure**:
   - **Overview**: Single sentence of what this workflow accomplishes
   - **Complete Flow**: Visual representation of all stages and systems involved
   - **Stage-by-Stage Breakdown**: For each major stage:
     - What happens (detailed explanation)
     - What systems are involved (with doc references like `21-agent-coordination.md`)
     - What intelligence is applied (AI decisions, learning, pattern matching)
     - What data is created/modified (with example JSON/code)
     - Why this stage exists (what problem it solves)
   - **Data Persistence**: What gets stored where and why
   - **System State Changes**: How this operation affects other Marcus systems
   - **Why This Complexity Matters**: Comparison of with/without Marcus

6. **Read the Relevant Documentation**: Before writing, read the Marcus system docs to understand:
   - Which systems are actually involved
   - What the data structures look like
   - What the configuration options and constraints are
   - How systems coordinate with each other

7. **Focus on Coordination**: Emphasize how multiple systems work together, not just individual system functionality.

The goal is to make readers think: "Wow, there's a lot of sophisticated engineering happening behind this simple operation."

Target workflow: [INSERT SPECIFIC WORKFLOW HERE]

Relevant Marcus system docs to read: [LIST RELEVANT DOCS FROM /docs/systems/]
