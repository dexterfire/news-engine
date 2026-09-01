# OPUS-MT + CTranslate2 for translation

We translate Story text to Russian with OPUS-MT models served through CTranslate2 (INT8, CPU inference, batching), per ТЗ §13. This is a deterministic, local, no-LLM translation path that preserves gaming terminology via the Terminology engine. The trade-off is model download and CPU inference cost versus an LLM-based translation; we accept it because translation is a high-volume pipeline stage where a local model keeps the LLM out of the critical path (ТЗ §1: LLM is fallback, not a runtime dependency).
