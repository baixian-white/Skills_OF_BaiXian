Update a skill file with lessons learned from the current session.
Invoke as: /skill-retro <skill-name>

## Steps

1. **Read the target skill file** at `~/.claude/commands/$ARGUMENTS.md`

2. **Summarize and classify this session's issues** — scan the conversation for:
   - Commands that failed or needed retrying
   - Workarounds that were discovered mid-execution
   - Assumptions in the skill that turned out to be wrong
   - Environment-specific quirks (OS, tool versions, network, etc.)

   For each issue, classify:
   - **Server-level** — affects any project on this server (HIDS behavior, OS/runtime quirks, network). → goes to skill's `## Runtime Notes`
   - **Project-level** — specific to this codebase (startup error, config mismatch, migration issue). → goes to project's `DEPLOY.md ## Known Issues`

3. **Write server-level issues** — append or update `## Runtime Notes` in the skill file:
   ```
   ## Runtime Notes
   <!-- Updated by /skill-retro. Most recent first. -->

   ### YYYY-MM-DD — <context, e.g. server name or project>
   - [UNVERIFIED] **Issue**: what went wrong → **Fix**: what to do instead | verify: `<one command that tests whether issue still exists>`
   ```
   Rules:
   - Tag every new note `[UNVERIFIED]` — verified exactly once on next run, then changed to `[VERIFIED]` or deleted
   - Include a `verify:` hint with a minimal shell command
   - Keep each note to one line; be specific and actionable
   - If a `[VERIFIED]` note already exists for the same issue, update it instead of adding a duplicate
   - Preserve all existing content above this section unchanged

   **Write project-level issues** — append rows to `## Known Issues` in `DEPLOY.md` (located in the project's local directory):
   ```
   | YYYY-MM-DD | <one-line description of the issue> | <what fixed it> |
   ```
   If `DEPLOY.md` has no `## Known Issues` section yet, add it before `## Deployment History`.

4. Confirm what was added.
