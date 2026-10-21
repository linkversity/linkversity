---
title: "How to Connect Agents to Linkversity"
description: "Your AI assistant can search Linkversity, read your collections and save links in your account. Two minutes to set up: one MCP endpoint, one consent screen, and a skill file your agent can load."
keywords: "MCP, Model Context Protocol, AI agents, ChatGPT, Claude, Cursor, link management, automation, skills"
date: "2026-10-21"
author: "The Linkversity Team"
---

# How to Connect Agents to Linkversity

Your chat assistant can already write emails and summarise PDFs. It still cannot answer "what's in my Web foundations collection?" or "save this to Backend" because it has no idea your collections exist.

That is the gap this closes. Linkversity speaks MCP, the open protocol ChatGPT, Claude, Cursor and most modern agents already understand. Two minutes of setup, and your assistant can search public collections, read yours, and file links where you tell it to.

## Step 1: Add the MCP server

In your agent's settings, add a **streamable-HTTP** server with this URL:

`https://linkversity.lol/mcp`

Or, if the client wants JSON config:

```json
{
  "mcpServers": {
    "linkversity": {
      "type": "streamable-http",
      "url": "https://linkversity.lol/mcp"
    }
  }
}
```

Some clients offer a "connect" button or ask you to paste a URL instead of filling a form. Same endpoint, same result.

## Step 2: Connect your account

Public search works with no sign-in at all. The first time you reach for a personal tool (anything with *my* in its name), your client opens Linkversity's consent screen. Approve it once and your agent gets two scopes:

- **collections:read**: search, list, open
- **collections:write**: save links, create collections

A read-only token that tries to write gets a clean `403`. Nothing fails silently.

## Where the token comes from

You never mint one by hand. Your client registers itself (`POST /oauth/register`), sends you to the consent screen (`/oauth/authorize`), then swaps the approval code at `/oauth/token` for a Bearer token that lasts 7 days, plus a 90-day refresh token it rotates on every use. You never see either string.

Scripts can run the same PKCE dance, and everything is described in the discovery document at `/.well-known/oauth-authorization-server`. Nothing to paste into a settings page.

## Step 3: Just ask

Natural language is the whole interface now:

> Find public collections about systems design, then save this article to my Backend collection.

One sentence, three tools: search public collections, list yours, save a link by name. Your agent handles the plumbing because the server tells it which tools exist and what each one does.

More prompts that work today:

- "What did I save in my Machine learning path last month?"
- "Add this URL to the Design systems collection, under Articles."
- "Make me a collection called Weekend projects, with a section for ideas."

## Give your agent the skill

Connecting the server is half of it. The other half is your agent knowing *which* tool to reach for and when. That is what the [Linkversity skill](/agents/skill) is: one markdown file your agent loads, containing the endpoint, all seven tools with their scopes, the save-by-name workflow, and the guardrails below.

Point your agent's skill loader at `https://linkversity.lol/agents/skill`, or drop the markdown into its skills folder as `SKILL.md`. Agents that load it stop guessing.

## What your agent can't do

Worth knowing before you hand it the keys:

- **It can't write to other people's collections.** The API enforces ownership on every call. A confident prompt cannot route around that.
- **It can't invent collection IDs.** The skill tells it to search or list first, so names are the interface.
- **Saves are idempotent.** The same URL twice returns the existing link, not a duplicate.
- **Private stays private.** Metadata of a private collection is visible; its links are not.

## Ideas worth stealing

- **The Friday inbox.** "Show me everything I saved this week, then file or drop each one." Your agent does the sorting, you make the calls.
- **Research with receipts.** "Find three well-regarded intros to Raft consensus and put them in my Distributed systems path." Public search does the finding; you keep the curation.
- **Notes to links.** Paste a wall of your own notes; your agent pulls out the URLs and files them under the titles you actually gave them.

## Start here

Everything above lives on one page: [linkversity.lol/agents](/agents) with the endpoint, the config, and the skill. No account yet? [Make one](/register) first; the consent screen needs somewhere to send the token.

Your collections were always the good part. Now they answer when spoken to.
