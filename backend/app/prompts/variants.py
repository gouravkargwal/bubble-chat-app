"""Prompt variant registry for A/B testing different prompt configurations."""

from dataclasses import dataclass, field


@dataclass
class PromptVariant:
    id: str
    description: str
    # Which template components to include (all True by default)
    use_few_shots: bool = True
    use_anti_patterns: bool = True
    use_fork_principle: bool = True
    use_playbooks: bool = True
    use_self_critique: bool = True
    use_voice_dna: bool = False
    use_conversation_history: bool = True
    # Override specific templates (None = use default)
    custom_few_shots: str | None = None
    custom_anti_patterns: str | None = None


class VariantRegistry:
    def __init__(self) -> None:
        self._variants: dict[str, PromptVariant] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(PromptVariant(
            id="default",
            description="Full system — all components enabled",
        ))
        self.register(PromptVariant(
            id="voice_dna_on",
            description="Same as default with Voice DNA block enabled (tests / future use)",
            use_voice_dna=True,
        ))
        self.register(PromptVariant(
            id="minimal",
            description="Base system only — no few-shots, anti-patterns, or self-critique",
            use_few_shots=False,
            use_anti_patterns=False,
            use_fork_principle=False,
            use_playbooks=False,
            use_self_critique=False,
        ))
        self.register(PromptVariant(
            id="no_critique",
            description="Everything except self-critique phase",
            use_self_critique=False,
        ))
        self.register(PromptVariant(
            id="no_examples",
            description="Everything except few-shot examples",
            use_few_shots=False,
        ))

    def register(self, variant: PromptVariant) -> None:
        self._variants[variant.id] = variant

    def get(self, variant_id: str) -> PromptVariant:
        return self._variants.get(variant_id, self._variants["default"])

    def list_all(self) -> list[PromptVariant]:
        return list(self._variants.values())


# Global singleton
registry = VariantRegistry()
