---
name: Adaptive cognitive orchestration
description: Keep application-level planning on demand without conflating it with provider reasoning settings.
---

The Muse Wonder model should decide whether to invoke the app's cognitive planning or deep-analysis tools. Simple greetings and direct one-step responses should skip those app-level calls. Preserve the model provider's reasoning effort setting unless the user specifically asks to change it.

**Why:** The user corrected a change that conflated provider reasoning parameters with the application's cognitive orchestration. They want simple messages to avoid extra cognitive work while retaining the provider reasoning configuration.

**How to apply:** For latency changes, let the main model select the app's cognitive tools as needed, and keep API-level reasoning settings untouched unless requested separately.
