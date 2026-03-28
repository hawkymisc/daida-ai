# Talk Script Style Definitions

Choose a speaking style for the speaker notes (talk script) to match the purpose of the presentation.

## casual (default)

**Use for**: Internal lightning talks, study groups, community meetups

**Characteristics**:
- Conversational, informal tone
- Speaks directly to the audience
- Includes natural pauses (...)

**Example**:
```
Hey everyone! So today I want to talk about Claude Code.
...First off, what does traditional development look like? You write code, write tests, open a PR...
It's a lot, right? But with Claude Code, things change dramatically. Like, you won't believe how much faster this gets.
```

## keynote

**Use for**: Conferences, large-scale events

**Characteristics**:
- Polished but not stiff
- Storytelling-driven structure
- Frequent references to numbers and data
- Includes pause directions

**Example**:
```
Today, I'd like to talk about how Claude Code is transforming the development experience.

(pause)

Let me start with a question. How much time does your team spend on code reviews?
According to recent studies, an average of 20% of development time goes to reviews alone. Let me share what we found when we decided to change that.
```

## formal

**Use for**: Corporate presentations, proposals, executive reports

**Characteristics**:
- Professional, measured language with complete sentences
- Data-driven and evidence-based
- Minimal emotional expression
- Structured readout style

**Example**:
```
Good morning. Today I will be presenting on the topic of optimizing development processes through AI assistance.
I would like to begin by outlining three key challenges we currently face.
First, development velocity bottlenecks. Under our current methodology, a single feature requires an average of three days to deliver.
```

## humorous

**Use for**: Internal lightning talks, casual events

**Characteristics**:
- Witty remarks and playful observations
- Self-deprecating humor is welcome
- Fast-paced delivery
- Anticipates audience laughter

**Example**:
```
Hi! So today's talk is about... (clicks slide) ...Claude Code!
Never heard of it? No worries. Give me five minutes and you'll be saying "I can't live without this."
I'm kidding. Well... mostly. Okay, I'm not kidding at all. But let's pretend I am so this feels less like an infomercial.
```

## Usage in SKILL.md

In Step 3 (talk script generation) of SKILL.md, the user selects a speaking style.
Claude (LLM) references the style definitions in this file when generating the script.
