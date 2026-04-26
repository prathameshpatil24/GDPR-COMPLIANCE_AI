# Phase 0.1 – Problem Statement

## 1. Background and Context

The General Data Protection Regulation (GDPR), enforced since May 2018, is the most significant data protection law in the modern digital economy. It applies to any organisation processing the personal data of individuals residing in the European Union, regardless of where the organisation itself is located.

GDPR is not a single rulebook. It is a layered legal system composed of:

* 99 articles and 173 recitals of the core Regulation (EU) 2016/679
* National implementation laws such as the German Bundesdatenschutzgesetz (BDSG)
* Sector-specific supplementary laws such as the Telekommunikation-Digitale-Dienste-Datenschutz-Gesetz (TTDSG / TDDDG)
* Binding guidelines issued by the European Data Protection Board (EDPB)
* National guidance from supervisory authorities (BfDI, BayLDA, LfDI BW, etc.)
* A growing body of enforcement decisions and court rulings

For any real-world scenario, determining which specific article has been violated requires reasoning across multiple layers of this system simultaneously. This is a non-trivial legal and engineering problem.

---

## 2. The Core Problem

Founders, developers, data protection officers (DPOs), privacy-curious engineers, and compliance-focused teams face a recurring difficulty:

* Given a natural-language description of a situation, which GDPR article has been violated?
* Which sub-clause specifically applies?
* Are there German-specific overlays (BDSG, TTDSG) that change the answer?
* Are there enforcement precedents where similar violations resulted in fines?

In practice, this leads to:

* Hours spent searching through the GDPR text for relevant articles
* Inconsistent interpretations across team members
* Expensive consultations with data protection lawyers for every medium-complexity question
* Fear of non-compliance leading to conservative, over-engineered implementations
* Fear of over-interpretation leading to gaps that surface only during DPA investigations

The result is that organisations either over-invest in legal overhead or under-invest in compliance, both of which are costly.

---

## 3. Why Existing Approaches Are Insufficient

### 3.1 Generic Large Language Models

General-purpose large language models can answer basic GDPR questions but fail at precise legal reasoning in several critical ways:

* They hallucinate article numbers, sometimes citing articles that do not exist or do not apply
* They rarely distinguish sub-clauses such as Article 6(1)(a) versus Article 6(1)(b)
* They miss German-specific overlays such as BDSG §26 for employment contexts
* They cannot cite enforcement precedents or anchor violations to real fines
* They have no concept of retrieval grounding — every answer is ungrounded generation

For a domain where the difference between Article 6(1)(a) and Article 6(1)(b) can determine whether a processing activity is legal or illegal, these failure modes are unacceptable.

### 3.2 Commercial Compliance Platforms

Enterprise compliance suites such as OneTrust, Securiti, and TrustArc offer automated compliance features, but:

* They are priced for enterprise budgets, not individuals or SMEs
* They focus on audit workflows, not scenario-based reasoning
* They are opaque systems that do not help the user learn the underlying reasoning
* They are overkill for quick, targeted violation analysis

### 3.3 Manual Research

Manually reading through GDPR text, EDPB guidelines, and DPA decisions is:

* Slow
* Error-prone
* Dependent on prior legal experience
* Not reproducible across team members
* Difficult to keep current as new enforcement decisions are published

---

## 4. The Need for a Specialised Violation-Detection System

There is a clear gap between generic LLM chatbots and expensive enterprise compliance suites. A dedicated system is needed that:

* Accepts free-text scenarios in natural language
* Identifies violated articles with precise sub-clause citations
* Includes German-market specialisation (BDSG, TTDSG)
* Anchors violations to real enforcement decisions
* Produces grounded, non-hallucinated citations
* Operates at low cost and with fast response times
* Is transparent in its reasoning process

Such a system enables:

* Founders and developers to self-assess common compliance scenarios
* DPOs and legal teams to accelerate initial triage of incoming questions
* Students and researchers to learn GDPR through real examples
* Teams to reduce legal consultation costs for routine questions

---

## 5. GDPR AI – Problem Scope

GDPR AI is designed to address this gap by focusing on accurate, grounded, scenario-based violation detection rather than generic privacy chat.

The platform aims to:

* Accept English-language scenarios describing real-world situations
* Produce structured reports identifying violated articles, sub-clauses, and short explanations
* Combine European GDPR with German national law (BDSG, TTDSG) and guidance (EDPB, DSK)
* Anchor violations to enforcement decisions from GDPRhub and the Enforcement Tracker
* Guarantee strict grounding through retrieval-augmented generation
* Provide a low-cost, local-first alternative to enterprise compliance platforms

GDPR AI explicitly does **not** aim to replace qualified data protection lawyers or provide legally binding advice. Instead, it focuses on building the reasoning layer required to accelerate and democratise routine GDPR analysis.

---

## 6. Target Users

The system is designed for:

* Founders and engineers building products that process personal data in the EU
* Junior DPOs and compliance analysts needing fast triage for incoming questions
* Students and researchers studying GDPR and data protection law
* Privacy-curious engineers and technical product managers
* Small and medium enterprises (SMEs) without dedicated legal departments

The initial version is scoped as a closed personal tool, with the architecture designed to support external users in later versions.

---

## 7. Why This Problem Matters

Accurate, accessible, grounded GDPR interpretation is foundational to:

* Compliance in modern data-driven products
* Reducing legal costs for early-stage teams
* Building trust with end users whose data is processed
* Demonstrating the value of domain-specific retrieval-augmented generation over generic chatbots

By solving this problem correctly, individuals and organisations can:

* Reduce compliance-driven technical debt
* Make earlier, better-informed design decisions
* Spend legal budget on the genuinely complex cases
* Treat GDPR as an engineering concern, not an afterthought

GDPR AI positions itself as a **specialised reasoning tool** rather than a generic privacy chatbot or an enterprise compliance suite.

---

## 8. Summary

The absence of a low-cost, accurate, grounded, scenario-based GDPR violation-detection system forces users to choose between unreliable generic chatbots, expensive enterprise suites, or slow manual research. None of these options is satisfactory for the majority of common compliance questions.

GDPR AI exists to demonstrate how such a system can be:

* Thoughtfully designed
* Retrieval-grounded
* German-market aware
* Transparent and extensible
* Built with low operational cost

---

## v2 Problem Extension

### v1 vs v2 question

* **v1** answers: *Which GDPR articles were violated in this scenario?*
* **v2** answers: *I am building a system that does X — what do I need to do to be GDPR compliant?*

### Market gap

Enterprise compliance platforms (for example OneTrust, Vanta, Sprinto) typically cost on the order of **USD 10k–100k+ per year** and are built for compliance teams, audit workflows, and vendor programmes. There is little that is **affordable and structured** for **indie developers**, **startup founders**, or **small agencies** who must go from near-zero GDPR literacy to a **defensible posture** without a full-time DPO or enterprise contract.

Industry experience suggests organisations spend roughly **USD 25k+ per year** on compliance tooling and advisory for smaller setups, and **USD 2M+ per year** at enterprise scale, depending on sector and footprint. A three-person startup often handles privacy **after hours** with search engines and blog posts. v2 targets that gap: **preventive**, **document-producing** guidance grounded in the same corpus as v1, running **locally**.

### EU AI Act and stacked risk

The **EU AI Act** applies from **August 2026**. Where personal data processing intersects regulated AI practices, a single technical or governance failure can create **overlapping exposure** under GDPR and the AI Act. That makes **up-front compliance assessment** — not only post-incident violation analysis — more urgent for teams shipping data-driven and ML-heavy products.