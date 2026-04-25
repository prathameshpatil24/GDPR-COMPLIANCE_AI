# Sample CLI output (marketing without consent)

Illustrative output from `gdpr-check analyze` after a successful run. Wording varies per retrieval and model sampling.

```
Summary
A retailer sends promotional email to users who only accepted account terms and never gave
separate marketing consent; lawful basis and consent conditions are in question.

Severity
HIGH — Direct marketing without valid consent risks multiple GDPR breaches.

┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Article / instrument ┃ Confidence ┃ Source                                   ┃ Explanation                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Art. 6 GDPR          │ 0.88       │ https://gdpr-info.eu/art-6-gdpr/       │ Lawfulness of processing …       │
│ Art. 7 GDPR          │ 0.85       │ https://gdpr-info.eu/art-7-gdpr/       │ Conditions for consent …         │
│ Art. 21 GDPR         │ 0.82       │ https://gdpr-info.eu/art-21-gdpr/      │ Right to object to direct …      │
└──────────────────────┴────────────┴──────────────────────────────────────────┴──────────────────────────────────┘

Recommendations
- Obtain explicit, granular consent for marketing or rely on another lawful basis with documentation.
- Offer a clear opt-out for direct marketing and honour objections without undue delay.

Not grounded (retrieval gap)
- (none, if all expected articles were retrieved)

This output is for informational purposes only and does not constitute legal advice.
```
