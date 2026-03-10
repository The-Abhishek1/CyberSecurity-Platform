class TokenCounter:
    def count(self, text: str) -> int:
        # Simple approximation - in production use proper tokenizer
        return len(text.split()) * 2
