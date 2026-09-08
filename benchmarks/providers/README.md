# benchmarks/providers

Provider implementations for benchmarking 15 frontier and open-weight LLMs (Gemini, OpenAI, Claude, DeepSeek, Qwen, Llama, Mistral, Kimi, GLM, Cohere) against local document parsing.

---

## Files and Modules

| File | Purpose | Key Classes / Functions |
|---|---|---|
| ase.py | Abstract base provider class with live call and offline dry-run simulation logic. | BaseLLMProvider |
| __init__.py | Provider matrix registry exporting all 15 benchmark provider instances. | PROVIDERS |
| gemini/ | Google Gemini Flash & Pro benchmark providers. | GeminiFlashProvider, GeminiProProvider |
| openai/ | OpenAI GPT-4o & GPT-4o-mini benchmark providers. | OpenAIGPT4oProvider, OpenAIGPT4oMiniProvider |
| nthropic/ | Anthropic Claude 3.5 Sonnet & Claude 3 Opus providers. | ClaudeSonnetProvider, ClaudeOpusProvider |
| deepseek/ | DeepSeek V3 & R1 benchmark providers. | DeepSeekV3Provider, DeepSeekR1Provider |
| qwen/ | Qwen 2.5 72B benchmark provider. | Qwen25Provider |
| meta/ | Meta Llama 3.3 70B benchmark provider. | Llama33Provider |
| mistral/ | Mistral Large benchmark provider. | MistralLargeProvider |
| kimi/ | Moonshot Kimi k1.5 benchmark provider. | KimiK15Provider |
| glm/ | Zhipu GLM-4 9B benchmark provider. | GLM4Provider |
| cohere/ | Cohere Command R+ benchmark provider. | CommandRPlusProvider |
