# Student Modeling, Knowledge Tracing & Personalized Learning — Research Map

This is a **research map**, not just a list of papers. For this project, focus on a relatively small set of “anchor” sources and then follow their references/citations outward.

## The research stack I would use

### 1. Start here: the KT bible

**Pardos et al. / Knowledge Tracing: A Survey — ACM Computing Surveys**

This should be your first serious read.

It gives you the evolution from classical BKT through PFA/LKT and deep KT, and discusses knowledge-state representations, question–skill relationships, forgetting, datasets, and evaluation. It also explicitly discusses GKT and graph-based relational structure.

**Use it for:** understanding the entire KT landscape before choosing BKT/LKT/ReKT/GKT.

[Knowledge Tracing: A Survey](https://doi.org/10.1145/3569576)

---

# 2. Classical foundation: BKT

### Corbett & Anderson — *Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge*

This is the foundational BKT work.

Learn:

```text
P(L0)  initial knowledge
P(T)   learning
P(S)   slip
P(G)   guess
```

and, more importantly, understand **what assumptions BKT makes about learning**.

For your implementation, don't just copy a BKT formula. Understand when its assumptions break.

---

# 3. PFA — probably the first model you should actually benchmark

### Pavlik, Cen & Koedinger — *Performance Factors Analysis* (2009)

PFA was explicitly developed as an alternative to traditional KT and addresses issues such as multiple skills contributing to actions and the relationship between practice history and performance.

This is highly relevant to a JEE project because:

```text
skill
+ prior successes
+ prior failures
+ practice history
→ probability of success
```

is a natural fit for sparse student data.

[Performance Factors Analysis paper](https://digitalcommons.memphis.edu/facpubs/8350/)

---

# 4. LKT — very important for your future benchmark

### Pavlik, Eglington & Harrell — *Logistic Knowledge Tracing: A Constrained Framework for Learner Modeling* (IEEE TLT, 2021)

This is one I'd keep bookmarked.

LKT isn't one fixed model. It's a framework for constructing logistic learner models from different features.

They tested **12 learner models across six learning datasets** and found that no single model was best everywhere. They also emphasize modeling recent learning and student differences.

That's a very important lesson:

> Don't decide beforehand that “BKT is best.”

Build a benchmark.

```text
Recent accuracy
       vs
BKT
       vs
PFA
       vs
LKT
       vs
deep KT
```

Then let held-out student interactions decide.

[LKT paper](https://doi.org/10.1109/TLT.2021.3128569)

---

# 5. Deep Knowledge Tracing — DKT

### Piech et al. — *Deep Knowledge Tracing* (NeurIPS 2015)

This is the paper that kicked off the modern deep-KT era.

It uses recurrent neural networks to model student interaction sequences and showed that neural models could outperform contemporary approaches on several datasets.

Don't implement this immediately.

Read it to understand the transition:

```text
explicit model of mastery
       ↓
learned latent representation
```

That's the conceptual jump.

[Deep Knowledge Tracing](https://proceedings.neurips.cc/paper_files/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html)

---

# 6. ReKT — one of the more relevant modern models

### Shen et al. — *Revisiting Knowledge Tracing: A Simple and Powerful Model* (ACM MM 2024)

This is worth reading **after** you understand BKT/PFA/LKT/DKT.

The interesting part is that ReKT explicitly considers student knowledge at multiple levels:

```text
Question
   ↓
Concept
   ↓
Domain
```

rather than blindly throwing everything into a giant sequence model.

There is also actual code, including a ReKT implementation in pyKT.

[ReKT implementation](https://github.com/lilstrawberry/ReKT)

---

# 7. GKT — important because of your concept graph

### Nakagawa et al. — *Graph-based Knowledge Tracing*

This is especially relevant to the concept-graph idea.

Instead of treating skills as isolated:

```text
Friction
Torque
Energy
```

you represent dependencies:

```text
Vectors
  ↓
Force decomposition
  ↓
Newton's laws
  ↓
Friction
```

GKT incorporates a graph of knowledge components and uses message passing to model how knowledge states interact.

This is exactly why the concept graph isn't just a visualization.

Eventually it could become **part of the learner model itself**.

---

# 8. Don't manually code all of these — use EduStudio

This is one of the strongest practical resources.

### EduStudio — Unified Library for Student Cognitive Modeling

EduStudio combines:

**Cognitive Diagnosis + Knowledge Tracing**

and provides standardized workflows for data preparation, models, training, evaluation and logging.

This is particularly useful because the eventual comparison isn't just:

> “I implemented BKT.”

You want:

```text
BKT
PFA
LKT
DKT
ReKT
GKT
...
```

without writing everything from zero.

[EduStudio GitHub](https://github.com/HFUT-LEC/EduStudio)

---

# 9. pyKT — another must-have implementation resource

### pyKT

This is a benchmark toolkit containing standardized preprocessing and implementations for many deep KT models over multiple datasets.

For this project:

**EduStudio → broader cognitive modeling**

**pyKT → KT experimentation**

I'd probably use both as references, but don't blindly mix their preprocessing/evaluation assumptions. KT experiments are surprisingly sensitive to how sequences are constructed and split.

[pyKT GitHub](https://github.com/pykt-team/pykt-toolkit)

---

# 10. The next layer: personalized learning

Once you understand KT, read this survey:

### *A comprehensive exploration of personalized learning in smart education: from student modeling to personalized recommendations* (2026)

This is particularly valuable because it explicitly organizes personalized learning around:

```text
Student modeling
       +
Personalized recommendation
```

and covers both cognitive and non-cognitive student characteristics.

That gives you the bridge from:

> **“estimate the student”**

 to

> **“do something about that estimate.”**

[2026 personalized-learning survey](https://journal.hep.com.cn/fcs/EN/10.1007/s11704-026-50579-1)

---

# 11. The REALLY important next step: intervention selection

Now we leave ordinary KT.

### Contextual Bandits / RL for adaptive curriculum

A strong concrete paper is:

**Belfer, Kochmar & Serban — *Raising Student Completion Rates with Adaptive Curriculum and Contextual Bandits***

They use student trajectories to select learning activities, then continue adapting online. They also report a randomized controlled trial where their approach improved completion and engagement.

This is conceptually close to what a future engine could do:

```text
student state
      ↓
candidate actions
      ↓
choose action
      ↓
observe outcome
      ↓
update policy
```

[Adaptive Curriculum + Contextual Bandits](https://arxiv.org/abs/2207.14003)

And for a broad overview, the 2025 systematic review of RL in education covers **89 papers** from 2000–2024.

[RL in Education systematic review](https://doi.org/10.1007/s40593-025-00494-6)

---

# 12. This is where StudentSim becomes important

### **StudentSim: Training LLM-based Student Simulators — Microsoft Research, 2026**

This is currently the most directly relevant source for the **simulation** part of the idea.

The paper identifies a fundamental problem:

> Evidence about which guidance works for which individual student is sparse, expensive and slow to collect.

Their StudentSim framework uses sparse per-student data and specializes a pooled model to individual students, with two key evaluation dimensions:

```text
Behavioral Fidelity
"Does it behave like this student?"

Guidance Responsiveness
"Does its behavior change appropriately
 when a tutor guides it?"
```

They evaluate on chess, second-language writing and mathematics and report stronger results than their comparison models, including GPT-5.4.

[StudentSim paper](https://arxiv.org/abs/2609.01591)

[StudentSim code](https://github.com/microsoft/StudentSim)

---

# 13. Then study the broader LLM student-simulation literature

Don't treat StudentSim as the beginning and end of the field.

There is now a growing literature around **LLM-based student simulators**, including work looking at learner profiles, instructional responses, cognitive development and educational-agent interactions.

A recent review is useful as a citation tree: once you open it, follow the papers that are specifically about **student simulation**, rather than general “LLM in education.”

This area is particularly valuable because it exposes the unresolved question:

> **Does an LLM merely produce convincing student-like dialogue, or does it actually reproduce the behavioral distribution of a real student?**

That distinction matters enormously.

---

# 14. Causal personalization — this is the rabbit hole to keep an eye on

This may eventually be more scientifically interesting than simply adding another KT architecture.

Suppose:

```text
Student A → intervention X → +10%
Student B → intervention X → -2%
```

A conventional recommendation model might learn:

> X correlates with high performance.

But the actual question is:

> **Who benefits from X because of X?**

That's a causal inference problem.

There's active research on **individualized/heterogeneous treatment effects in education**. One large analysis developed methods to estimate individualized treatment effects from educational trials and showed why average treatment effects can conceal substantial individual differences.

And there is very recent work explicitly applying causal targeting ideas to personalized learning-path recommendations. Interestingly, that work finds that learned CATE targeting isn't automatically superior to simple baselines, which is an excellent reminder not to assume the fancy method wins.

This is research to follow, but **not implement yet**.

---

# 15. One especially important lesson from all this

Don't frame the research question as:

> **“Which knowledge tracing algorithm is best?”**

That's too narrow.

A much more interesting research question is:

> **Can longitudinal student interaction data be used to build a personalized state model that selects interventions and learns which interventions improve that individual student's future performance?**

Then the algorithms become components:

```text
                 YOUR RESEARCH
                      │
          ┌───────────┴───────────┐
          ↓                       ↓
     Student state          Student behavior
          │                       │
    BKT/PFA/LKT/KT          error patterns
          │                       │
          └───────────┬───────────┘
                      ↓
                Intervention
                      │
          ┌───────────┴───────────┐
          ↓                       ↓
     recommendation          simulation
                              StudentSim
          │                       │
          └───────────┬───────────┘
                      ↓
                Real outcome
                      ↓
             update the model
```

That is a **much more coherent research program**.

---

# My recommended reading order

Don't read 30 papers randomly.

I'd go:

**① KT Survey → ② BKT → ③ PFA → ④ LKT → ⑤ DKT → ⑥ ReKT/GKT → ⑦ EduStudio/pyKT → ⑧ Personalized Learning survey → ⑨ Contextual Bandits/RL → ⑩ StudentSim → ⑪ Causal personalization**

That progression follows the actual conceptual evolution:

**model knowledge → model dynamics → understand behavior → recommend → optimize interventions → simulate → establish causality.**

And one more thing: **don't start implementing ReKT/GKT just because they're newer.** The sister's data will initially be tiny. Establish a clean event schema, collect longitudinal interactions, and benchmark simple models honestly. The fact that current KT tooling emphasizes standardized datasets and controlled prediction scenarios is itself a clue that evaluation discipline matters as much as model architecture.

For an eventual Aakash data request, the papers above also tell us exactly what to ask for: **student × question/skill × timestamp × outcome**, plus timing/context whenever possible. Without that longitudinal interaction structure, you can build analytics, but you're severely limiting what student-modeling research you can do.
