# Dynamic Multi-Agent Meta-Learner (DMAML) System Protocol

The autonomous operational framework for AETHER task execution, reasoning, and self-optimization.

---

## Operational Pipeline

### Phase 1: Meta-Architect Decomposition & Role Assignment
1. Ingest high-level user objectives.
2. Decompose into atomic, non-redundant dependency sub-tasks.
3. Query `data/memory/continuous_learning_ledger.json` for prior heuristics, failure modes, and exemplars.
4. Dynamically synthesize specialized worker agents with explicit objectives, scope boundaries, and permissions.

### Phase 2: Hierarchical Specialist Execution
1. Instantiate worker agents in dependency order.
2. Execute independent tasks in parallel; stream downstream artifacts sequentially.
3. Maintain intermediate reasoning scratchpads (`[Agent_ID - Thought]`, `[Action]`, `[Artifact]`).

### Phase 3: Critic Evaluation & Reflexion
1. Pass all candidate artifacts to the Critic & Validation Layer.
2. Evaluate against Completeness, Soundness & Accuracy, Cohesion, and Constraint Adherence.
3. **Threshold**: Score >= 95% to proceed; < 95% triggers a targeted Reflexion Loop (up to 3 attempts).

### Phase 4: Layer-Based Learning & Context Extraction
1. Extract architectural insights, negative constraints, and anti-patterns.
2. Append new heuristics to `continuous_learning_ledger.json`.
3. Synthesize the final, production-grade deliverable for the user.
