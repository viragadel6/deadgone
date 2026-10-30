---
name: Adaptive cognitive orchestration
description: Keep application-level planning on demand without conflating it with provider reasoning settings.
---

The configured Muse Spark model should decide whether to invoke the app's cognitive planning or deep-analysis tools. Simple greetings and direct one-step responses should skip those app-level calls. Preserve the model provider's reasoning effort setting unless the user specifically asks to change it.

**Why:** The user wants simple messages to avoid extra app-level cognitive work while keeping provider reasoning separate. They selected Muse Spark as the app's main model.

**How to apply:** Let the configured main model choose app-level cognitive tools as needed. Keep API-level reasoning settings independent and change them only when requested.
