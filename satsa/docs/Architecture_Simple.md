# SAT-SA Architecture: A Simple Guide

**Document Overview:** This document explains the architecture of the Supervisory Analytics Tool for SOC Assessment (SAT-SA) in simple, non-technical language. It is designed to be read as a 2-page executive summary.

---

## PAGE 1: The Big Picture & The Data Journey

### 1. What is SAT-SA?
Think of most cybersecurity tools as security guards—they watch the doors in real-time to catch bad guys. **SAT-SA is not a security guard; it is an auditor.** 
Instead of looking for hackers, SAT-SA looks at how well the security guards (the SOC team) are doing their jobs. It operates entirely offline and reviews past reports to see if the guards are cutting corners, missing blind spots, or faking their performance metrics.

### 2. Step 1: Collecting the Evidence (Data Sources)
Because SAT-SA is highly secure and "air-gapped" (disconnected from the internet), it doesn't connect live to other systems. Instead, audited organizations provide spreadsheets or text files containing two things:
1.  **Asset Inventory:** A list of all their important computers and servers.
2.  **Alert Logs:** A list of all the security alarms that went off over the last month and how the analysts handled them.

*(Note: For demonstrations, we use a "Synthetic Generator" that creates fake data mimicking real-world scenarios).*

### 3. Step 2: The Filing Cabinet (Data Storage)
Once the files are loaded, SAT-SA needs to read them very quickly. It uses two technologies to do this:
*   **Parquet:** It takes massive, clunky spreadsheets and compresses them into a highly efficient format.
*   **DuckDB:** Think of this as a super-fast, intelligent librarian. It allows SAT-SA to search through millions of rows of data in fractions of a second without needing a massive, expensive server farm.

### 4. Step 3: The Detectors (The Brains)
Once the data is organized, SAT-SA runs a series of tests called "Detectors." Unlike traditional tools that look for viruses, our detectors look for human and process failures. They fall into two categories:
*   **Execution Gaps:** Doing things poorly. For example, if a "Critical" alarm goes off and a human analyst closes it 5 seconds later without taking notes, that's a massive red flag.
*   **Negative Space:** Things that are missing. If an organization has 5 "Highly Critical" servers, but those servers haven't produced a single log or alarm in 30 days, SAT-SA flags this "silence" as a broken sensor or a blind spot.

---
*(End of Page 1)*

---

## PAGE 2: Scoring, Security, and Results

### 5. Step 4: Grading the Organizations (The Prioritiser)
Once the detectors find problems, SAT-SA needs to grade the organizations. However, we want to be fair. If a single detector accidentally fires 1,000 times for the same minor issue, we don't want it to unfairly ruin the organization's score.
To solve this, we use a math concept called "Noisy-OR". It ensures that repeated failures of the exact same type don't exponentially hurt the score. The final grade is called the **Attention Index**—a single score that tells supervisors exactly which organization is in the most trouble.

### 6. Step 5: The Smart Sample (Review Optimiser)
Human auditors don't have time to review 10,000 alerts manually. Usually, they just pick 10 at random. 
SAT-SA replaces this with a "Review-Sample Optimiser." It looks at the Attention Index and the severity of the alerts to give the human auditor the **10 most suspicious cases** to review. During testing, this "smart sampling" proved to be almost twice as effective at finding real weaknesses compared to random sampling.

### 7. Step 6: The Dashboard (User Interface)
All of this complex math is hidden behind a simple, easy-to-use web dashboard (built with a tool called Streamlit). When a supervisor opens the dashboard, they see:
*   A ranked list of organizations from worst to best.
*   "Finding Cards" written in plain English explaining exactly *why* an organization was flagged (e.g., "Critical Server X had zero alerts").
*   The optimized list of cases they should manually review today.

### 8. Step 7: The Unbreakable Ledger (Audit Chain)
Because SAT-SA is used to judge performance, audited organizations might be tempted to delete bad reports or alter the findings. 
To prevent this, SAT-SA uses a **Tamper-Evident Audit Chain**. Every time the tool is run, it creates a unique digital fingerprint (a SHA-256 hash) that links to the previous run—just like a blockchain. If anyone tries to secretly modify or delete a past result, the chain breaks, and the dashboard flashes a massive "Tampering Detected" warning.

### Conclusion
By combining lightning-fast data processing, intelligent human-behavior detectors, and unbreakable cryptographic logs, SAT-SA provides supervisors with a foolproof, air-gapped tool to ensure critical organizations are actually secure, rather than just pretending to be.
