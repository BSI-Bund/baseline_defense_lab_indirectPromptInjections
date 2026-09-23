<!--
SPDX-FileCopyrightText: 2026 Bundesamt für Sicherheit in der Informationstechnik (BSI) SPDX-License-Identifier: EUPL-1.2 -->
# Security policy

## Scope — please read first

Baseline-Defense-Lab is a **teaching and testing environment**, not a product. By design it has **no authentication**, it deliberately parses attacker-supplied PDF documents, and it is meant to run locally on the loopback interface. See [README.md](README.md) for the full list of documented limits.

The following are therefore **not** vulnerabilities in this project and do not need to be reported:

- missing authentication, authorization, rate limiting or multi-tenancy;
- the fact that the demonstrated defenses can be bypassed — that is the subject of the lab and is documented openly;
- findings that only apply when the stack is exposed beyond loopback, contrary to the documented intended use.

What we do want to hear about: memory-safety or denial-of-service issues in the document parsing path, unintended data exfiltration beyond what the lab demonstrates, dependency vulnerabilities that reach the delivered artefact, and mistakes in the licence or attribution metadata.

## Reporting a vulnerability

Please do **not** open a public issue for a security report.

- **E-mail:** <referat-t25@bsi.bund.de>

Please include: the affected version or commit, reproduction steps, expected and observed behaviour, and your assessment of the impact.

**No response time is promised.** This project is not actively maintained (see below), so we cannot commit to an acknowledgement or assessment deadline. Reports are read, and we would rather say this plainly than state a deadline we would not keep.

## How we handle reports

We follow the principles of Coordinated Vulnerability Disclosure: please give us the opportunity to assess a report before disclosing it publicly. If a fix is published, we will credit you on request.

Because the project is not actively maintained, a report may result in a documented advisory rather than a code change. We will say which it is.

## Reporting licence or attribution problems

If you believe a passage in this repository reproduces third-party material without proper attribution, please report it through the same channel. We treat such reports with the same priority as security reports.

## Maintenance and support

**This project is not actively maintained.** It is published as a reference and teaching artefact, not as a supported product. Concretely:

- **No security updates are to be expected.** Dependency vulnerabilities will not routinely be fixed. At the time of publication the Angular version in use is outside upstream support and carries known advisories — see [README.md](README.md).
- **No response times are promised** for reports, issues or change requests.
- **Do not deploy this as a service.** The intended use is local, on the loopback interface, for learning and experimentation.

If you want to build on it, fork it and take over maintenance yourself. The EUPL permits that expressly; nothing here suggests the BSI will maintain your fork.
