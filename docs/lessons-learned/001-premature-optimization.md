# Lesson Learned: Premature Optimization

## What Happened

1. Started with simple JSON storage
2. Discussed theoretical scaling concerns
3. Spent effort migrating to SQLite (schema, tests, etc.)
4. Concept evolved significantly during brainstorming
5. SQLite schema became baggage - harder to pivot

## The Mistake

Optimized for scale before proving the concept.

We didn't know the model would evolve from:
- "threads + conclusions"
- → "efforts + conclusions"
- → "self-evolving artifact schemas with reference-weighted expiration"

Each pivot would have required schema migrations, test updates, etc.

## The Lesson

**Prove the concept first. Optimize when you know what you're optimizing FOR.**

- Simple JSON files are easier to inspect, modify, debug
- Schema changes are trivial (just change the structure)
- No migrations, no SQL changes
- Can look at the data directly in any editor

## When to Optimize

- When the model is stable
- When you hit actual (not theoretical) scaling issues
- When the cost of NOT optimizing is real

## Applied

Reverted to simple JSON storage. SQLite can come back when:
1. The artifact/schema model is proven and stable
2. We have actual data showing performance problems
