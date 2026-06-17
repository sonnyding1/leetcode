# README

This notes system is a repository of my understanding of LeetCode problems. This document describes the structure of the files within this directory, and how the collected data are intended to be used.

## Files

### `<id>.md`

Each Markdown file describes the process of solving a specific LeetCode problem, and may include things like thought process, partial solutions, pseudocode, etc. The Markdown file should aim to contain only my current understanding of the problem, not my past understandings, and should be brief.

The Markdown file should contain YAML frontmatter with `name`, `id`, and `difficulty`.

### `events.yaml`

Append-only timeline of every problem's difficulty rating, with UTC timestamps. Each entry contains `id`, `name`, `difficulty`, and `timestamp`. A problem's difficulty history is visible by scanning consecutive entries with the same `id`.

Auto-populated by `scripts/log_event.py` on nvim save (BufWritePost autocommand).

### `.state.yaml`

Internal file that tracks the last-known difficulty for each problem by ID. Used by `log_event.py` to detect changes. Format: `id: difficulty` per line.

### `scripts/log_event.py`

Zero-dependency Python script that parses frontmatter from a `.md` file, compares against `.state.yaml`, and appends events to `events.yaml`.

## Difficulty

- 0: Trivial, 100% confidence in solving the problem, and confident that I will continue to be able to solve the problem even without any practice in the future. An example is Two Sum.
- 1: Easy, know exactly how to break down the problem into which steps, then carry through the steps. May have a little concern on implementation details, may need to review the problem once in a year or so.
- 2: Comfortable, know basically how to do the problem, but can have some fuzzy spots, and can sometiems get caught in the implementation details. Need to review relatively frequently, to try to promote into difficulty 1 and 0.
- 3: Fun, have majority of the intuition down, but still have small portions of unknowns that bring difficulties. Have not very high confidence in implementation. Overall have a good shot of solving the question.
- 4: Challenging, have some intuition on how to solve the problem, but probably not enough to be able to solve the problem.
- 5: Out of bound, don't even have intuition on how to solve the problem, likely lacking some key concepts to be able to tackle the problem.

## LLM Usage

For LLM reading this, you may use the Markdown files to guide the user on a problem they have tackled before, because now you have an understanding of their level of understanding of specific problems.
