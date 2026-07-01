# Agent Skills

This directory contains predefined **Agent Skills** in the open
[SKILL.md](https://github.com/anthropics/skills) format — each skill is a
folder containing a single `SKILL.md` file with YAML frontmatter followed by
a Markdown body of instructions.

Layout:

```
app/skills/
├── README.md              (this file)
├── code-reviewer/
│   └── SKILL.md
├── devops-troubleshooter/
│   └── SKILL.md
└── secure-coding-advisor/
    └── SKILL.md
```

## How they are used

At application startup, `src.runtime.skills.load_skills()` collects
this directory (plus any extra paths from the
`COPILOT_API_SKILL_DIRECTORIES` env var, `os.pathsep`- or comma-separated)
and passes them to the GitHub Copilot SDK via the `skill_directories`
argument on
`create_session` / `resume_session`. The SDK then loads every `SKILL.md` it
finds and decides — based on each skill's `description` — whether to apply
that skill to a given user turn.

The application itself is **not** a skill registry: it neither lists,
publishes, nor serves skills over an API. Skills live as plain files on disk
and are consumed directly by the Copilot SDK.

## Adding a new skill

1. Create a new folder: `app/skills/my-skill/`.
2. Add a `SKILL.md` file with frontmatter (`name`, `description`) and the
   instructions body. Keep `description` action-oriented so the SDK can
   route to it (e.g. "Use when the user asks to review code for ...").
3. Restart the application; the new skill is picked up automatically.

To disable a shipped skill without removing the file, set
`COPILOT_API_DISABLED_SKILLS=skill-name-1,skill-name-2`.
