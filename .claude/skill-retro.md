Update a skill file with lessons learned from the current session.
Invoke as: /skill-retro <skill-name>

## Steps

1. **Read the target skill file** at `~/.claude/commands/$ARGUMENTS.md`

2. **Summarize this session's issues** — scan the conversation for:
   - Commands that failed or needed retrying
   - Workarounds that were discovered mid-execution
   - Assumptions in the skill that turned out to be wrong
   - Environment-specific quirks (OS, tool versions, network, etc.)

3. **Update the skill file** — append or update a `## Runtime Notes` section at the bottom:
   ```
   ## Runtime Notes
   <!-- Updated by /skill-retro. Most recent first. -->

   ### YYYY-MM-DD — <context, e.g. server name or project>
   - [UNVERIFIED] **Issue**: what went wrong → **Fix**: what to do instead | verify: `<one command that tests whether issue still exists>`
   ```
   Rules:
   - Tag every new note `[UNVERIFIED]` — the skill will verify it exactly once on next run, then change to `[VERIFIED]` or delete it
   - Include a `verify:` hint with a minimal shell command that can confirm the issue still exists
   - Keep each note to one line; be specific and actionable
   - If a `[VERIFIED]` note already exists for the same issue, update it instead of adding a duplicate
   - Preserve all existing content above this section unchanged

4. Confirm what was added.
