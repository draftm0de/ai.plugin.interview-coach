# Technical and coding interview contract

Activate when a vacancy/CV implies developer, engineer, architect, DevOps or other technical duties; ask candidate to choose the language/level only when evidence does not establish it.

## Types and levels

- Junior: syntax, data structures, debugging, basic testing.
- Mid: feature implementation, APIs, databases, code review, test design.
- Senior: tradeoffs, reliability, performance, security, design, mentoring.
- Staff/Lead: architecture, cross-team decisions, incidents, migration and technical leadership.

Choose from coding, debugging, code review, system design, SQL/data modeling, testing, security, CI/CD, and operational incident exercises. Tailor technologies to the vacancy and verified CV; clearly distinguish experience from an unfamiliar skill being tested.

## Coding exercise

1. State task, inputs/outputs, constraints, language/runtime, timebox, and evaluation rubric.
2. Do not leak the reference solution before candidate attempts it.
3. Prefer executable test cases with normal, edge and invalid inputs. Run in an authorized sandbox only.
4. Never execute untrusted candidate code on a host with secrets, unrestricted network or sensitive filesystem access. If no safe runner exists, perform static review and explicitly label it *not executed*.
5. Evaluate correctness, tests, complexity, security, maintainability and explanation separately. Avoid treating a confident LLM judgment as a passing test.
6. For architecture questions, evaluate assumptions, tradeoffs, operations and failure handling rather than claiming a single universally correct design.

Record task, submitted code/answer, test command and actual test output in the private run. Do not save candidate submissions to the public skill repository.
