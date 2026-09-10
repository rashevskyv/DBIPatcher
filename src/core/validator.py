import re
import json
from pathlib import Path

class Validator:
    def __init__(self, blocks_config_path=None):
        self.blocks = {}
        
        if blocks_config_path and Path(blocks_config_path).exists():
            with open(blocks_config_path, "r", encoding="utf-8") as f:
                self.blocks = json.load(f)

    def check_placeholders(self, original, translation):
        """Checks if all {…} tags and %x specifiers are preserved exactly."""
        pattern = r"(\{[^}]*\}|%[a-zA-Z])"
        orig_placeholders = re.findall(pattern, original)
        trans_placeholders = re.findall(pattern, translation)
        
        if sorted(orig_placeholders) != sorted(trans_placeholders):
            return f"Placeholder mismatch: expected {orig_placeholders}, found {trans_placeholders}"
        return None

    def check_square_bracket_tags(self, original, translation):
        """Checks if all [content] tags are preserved exactly.
        
        Excludes [[TOKEN]] patterns (handled by check_tokens).
        Matches single-bracket tags like [+], [-1], [NSP], etc.
        """
        # Match [content] but NOT [[content]]
        pattern = r"(?<!\[)\[([^\[\]]+)\](?!\])"
        orig_tags = re.findall(pattern, original)
        trans_tags = re.findall(pattern, translation)
        
        if sorted(orig_tags) != sorted(trans_tags):
            return f"Square bracket tag mismatch: expected {['['+t+']' for t in orig_tags]}, found {['['+t+']' for t in trans_tags]}"
        return None

    def check_tokens(self, original, translation):
        """Checks if internal tokens like [[LF]], [[TAB]], [[ESC]] are preserved."""
        pattern = r"\[\[[A-Z]+\]\]"
        orig_tokens = re.findall(pattern, original)
        trans_tokens = re.findall(pattern, translation)
        
        if sorted(orig_tokens) == sorted(trans_tokens):
            return None

        # Handle legitimate DBI exact ANSI-status asymmetry:
        # DBI lead-control skip strips the initial \x1b (<0x20). An exact lookup
        # does not restore it, so the dictionary translation must carry a leading
        # [[ESC]] while the original lookup key starts bare with "[...m".
        if (
            re.match(r"^\[\d+(?:;\d+)*m", original)
            and translation.startswith("[[ESC]][")
            and len(trans_tokens) == len(orig_tokens) + 1
        ):
            trans_copy = list(trans_tokens)
            if "[[ESC]]" in trans_copy:
                trans_copy.remove("[[ESC]]")
                if sorted(orig_tokens) == sorted(trans_copy):
                    return None

        return f"Token mismatch: expected {orig_tokens}, found {trans_tokens}"


    def check_colon(self, original, translation):
        """Checks if colon presence is preserved (ignoring colons inside format specifiers)."""
        # Strip format specifiers like {:02X}, {:>3}, {:s} before checking
        strip_fmt = lambda s: re.sub(r'\{[^}]*\}', '', s)
        orig_clean = strip_fmt(original)
        trans_clean = strip_fmt(translation)
        
        has_colon_orig = ":" in orig_clean or "：" in orig_clean
        has_colon_trans = ":" in trans_clean or "：" in trans_clean
        
        if has_colon_orig and not has_colon_trans:
            return "Missing colon in translation"
        if not has_colon_orig and has_colon_trans:
            return "Unexpected colon in translation"
        return None

    def check_parentheses_count(self, original, translation):
        """Checks round bracket count: translation must have >= original count.

        Some languages (Korean, Japanese) use grammatical constructions
        like 이(가), を(は) that add legitimate parentheses.
        Translation can have MORE brackets, but not FEWER.
        """
        for char, full_char in [("(", "（"), (")", "）")]:
            orig_count = original.count(char) + original.count(full_char)
            trans_count = translation.count(char) + translation.count(full_char)
            if trans_count < orig_count:
                return f"Missing parenthesis '{char}': expected at least {orig_count}, found {trans_count}"
        return None

    def check_language_code(self, original, translation, lang_code):
        """Checks if 'ru' language code in original is replaced with target language code.

        If original contains 'ru' as a standalone language code, translation must replace it
        with the appropriate target language code (e.g., 'ua', 'en', 'de', etc.).
        """
        if not lang_code or lang_code == "ru":
            return None

        # Check if 'ru' appears as a language code in original
        # Look for patterns like: "ru", " ru ", "ru,", etc.
        import re
        # Match 'ru' as a word boundary (not part of another word like "true", "crush")
        ru_pattern = r'\bru\b'

        if re.search(ru_pattern, original, re.IGNORECASE):
            # Check if translation has the target language code
            lang_pattern = rf'\b{re.escape(lang_code)}\b'
            if not re.search(lang_pattern, translation, re.IGNORECASE):
                return f"Language code 'ru' in original should be replaced with '{lang_code}' in translation"

        return None

    def validate_row(self, original, translation, lang_code="ua"):
        """Runs all checks for a single translation row."""
        if not translation:
            return ["Translation is empty"]

        errors = []

        err = self.check_placeholders(original, translation)
        if err: errors.append(err)

        # We intentionally SKIP check_square_bracket_tags for DBI.
        # In DBI, square brackets are used for translatable statuses like [ОШИБКА], [ОТСУТСТВУЕТ].

        err = self.check_tokens(original, translation)
        if err: errors.append(err)

        err = self.check_colon(original, translation)
        if err: errors.append(err)

        err = self.check_parentheses_count(original, translation)
        if err: errors.append(err)

        err = self.check_language_code(original, translation, lang_code)
        if err: errors.append(err)

        return errors

    def validate_blocks(self, originals: dict[int, str]) -> list[str]:
        """
        Validates that every exact string pattern in blocks.json matches exactly one
        row in the given originals dict (row_idx -> original_value).
        
        Call this AFTER alignment to ensure nothing was broken.
        Returns a list of error strings (empty = all OK).
        """
        errors = []
        
        for block_id, exact_list in self.blocks.items():
            for exact_str in exact_list:
                matches = []
                for row, val in originals.items():
                    if val == exact_str:
                        matches.append((row, val))
                
                if len(matches) == 0:
                    errors.append(
                        f"[{block_id}] String NOT FOUND: {exact_str[:60]}..."
                    )
                elif len(matches) > 1:
                    rows_info = ", ".join(f"row {r}" for r, _ in matches)
                    errors.append(
                        f"[{block_id}] AMBIGUOUS ({len(matches)} matches): "
                        f"{exact_str[:40]}... -> {rows_info}"
                    )
        
        return errors


_validator_instance = None

def validate(original: str, translation: str, lang_code: str = "ua") -> tuple[bool, str]:
    """
    Compatibility wrapper for Validator class.
    Returns (success, error_message or "OK").
    Uses a module-level singleton to avoid repeated instantiation.
    """
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = Validator()
    errs = _validator_instance.validate_row(original, translation, lang_code)
    if errs:
        return False, "; ".join(errs)
    return True, "OK"

