# RupeeRadar — Project Context

## Overview

**RupeeRadar** is an AI-powered personal finance assistant that helps working professionals understand where their money is going by analyzing bank statement data.

The goal is an end-to-end solution that converts raw financial transaction data into meaningful personal finance insights.

## Problem

Working professionals often make hundreds of monthly transactions across UPI, cards, bank transfers, subscriptions, EMIs, rent, shopping, food delivery, travel, and investments. Bank statements contain all this information, but transaction descriptions are messy, inconsistent, and hard to categorize manually.

## User Questions to Answer

The solution should help users answer:

- What are my biggest spending categories?
- How much did I spend this month?
- Which transactions are recurring subscriptions or EMIs?
- What was my biggest transaction?
- What are the top insights from my spending behavior?

## Core Requirements

1. **Input** — Accept bank statement data as input.
2. **Extraction & cleaning** — Extract or clean transactions into a structured format.
3. **Categorization** — Group transactions into meaningful categories:
   - Food
   - Travel
   - Shopping
   - Bills
   - EMI
   - Subscriptions
   - Salary
   - Rent
   - Investments
   - Other
4. **Recurring detection** — Identify recurring transactions (subscriptions, EMIs, rent, SIPs, insurance payments).
5. **Metrics** — Calculate key financial metrics:
   - Total income
   - Total spend
   - Savings
   - Top categories
   - Biggest transactions
6. **Insights** — Generate clear, human-readable spending insights using actual transaction amounts.
7. **Presentation** — Present results through a simple UI, dashboard, or downloadable report.

## Expected Deliverables (Prototype)

A working prototype that demonstrates:

- Cleaned transaction data
- Categorized expenses
- Recurring payment detection
- Spend summary dashboard
- At least three personalized financial insights
- A final report or visual summary that can be shared

## Evaluation Criteria

Submissions are evaluated on:

| Area | Focus |
|------|--------|
| Accuracy | Transaction cleaning and categorization |
| Insights | Quality of financial insights |
| Robustness | Handling real-world messy transaction descriptions |
| UX | Simplicity and usefulness of the user experience |
| Completeness | End-to-end workflow |
| Privacy | Conscious handling of sensitive financial data |

## Constraints & Approach

- **Prioritize a working end-to-end prototype** over perfect support for every bank format.
- Technology stack and implementation approach are flexible.
- Final deliverable: a **deployed or locally runnable application** that takes raw bank statement data and produces a clear personal finance summary.

## Suggested Pipeline

```
Bank statement upload
    → Parse & extract transactions
    → Clean & normalize descriptions
    → Categorize (rules and/or AI)
    → Detect recurring payments
    → Compute metrics & insights
    → Dashboard / report
```

## Privacy Considerations

Financial data is sensitive. The application should:

- Minimize data retention where possible
- Avoid sending raw statements to third parties without clear user consent
- Handle uploads securely (local processing preferred when feasible)

## Project Status

Early stage — problem statement defined; implementation not yet started.
