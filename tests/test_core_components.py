"""Comprehensive tests for core components: tokenization, validation, alignment, and export."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.text_utils import tokenize, detokenize, normalize_tokens_out, visual_length  # noqa: E402
from src.core.validator import Validator  # noqa: E402


# ── Tokenization & Detokenization Tests ──────────────────────────────────

class TokenizationTests(unittest.TestCase):
    """Test tokenization and reverse tokenization of special characters."""

    def test_tokenize_newline(self) -> None:
        """Test that \\n and newline are converted to [[LF]]."""
        self.assertEqual(tokenize("hello\nworld"), "hello[[LF]]world")
        self.assertEqual(tokenize("hello\\nworld"), "hello[[LF]]world")

    def test_tokenize_tab(self) -> None:
        """Test that \\t and tab are converted to [[TAB]]."""
        self.assertEqual(tokenize("hello\tworld"), "hello[[TAB]]world")
        self.assertEqual(tokenize("hello\\tworld"), "hello[[TAB]]world")

    def test_tokenize_carriage_return(self) -> None:
        """Test that \\r and carriage return are converted to [[CR]]."""
        self.assertEqual(tokenize("hello\rworld"), "hello[[CR]]world")
        self.assertEqual(tokenize("hello\\rworld"), "hello[[CR]]world")

    def test_tokenize_escape_sequence(self) -> None:
        """Test that \\x1b (escape) is converted to [[ESC]]."""
        self.assertEqual(tokenize("hello\x1bworld"), "hello[[ESC]]world")

    def test_tokenize_multiple_tokens(self) -> None:
        """Test tokenizing multiple special characters."""
        result = tokenize("line1\nline2\ttab\x1bescape\rcarriage")
        self.assertEqual(result, "line1[[LF]]line2[[TAB]]tab[[ESC]]escape[[CR]]carriage")

    def test_detokenize_all_tokens(self) -> None:
        """Test that detokenization converts tokens back to literal escape sequences."""
        original = "line1\nline2\ttab\x1bescape\rcarriage"
        tokenized = tokenize(original)
        # Detokenize returns literal backslash-escaped strings, not actual bytes
        detokenized = detokenize(tokenized)
        # For CSV output, we expect \\n, \\t, \\x1b, \\r (escaped)
        self.assertIn("\\n", detokenized)  # literal backslash-n
        self.assertIn("\\t", detokenized)  # literal backslash-t
        # Re-tokenizing should get us back to tokenized form
        self.assertEqual(tokenize(detokenized), tokenized)

    def test_tokenize_empty_string(self) -> None:
        """Test tokenizing empty string."""
        self.assertEqual(tokenize(""), "")

    def test_tokenize_mixed_literal_and_escaped(self) -> None:
        """Test tokenizing mix of literal and escaped special chars."""
        # Both \n and literal newline should become [[LF]]
        test_str = "line1\nline2\\nline3"
        result = tokenize(test_str)
        self.assertEqual(result.count("[[LF]]"), 2)


# ── Validator Tests ──────────────────────────────────────────────────────

class ValidatorPlaceholderTests(unittest.TestCase):
    """Test placeholder validation."""

    def setUp(self) -> None:
        self.validator = Validator()

    def test_placeholder_preservation(self) -> None:
        """Test that {…} placeholders are preserved."""
        original = "Count: {0}, Name: {name}"
        translation = "Cantidad: {0}, Nombre: {name}"
        err = self.validator.check_placeholders(original, translation)
        self.assertIsNone(err)

    def test_missing_placeholder(self) -> None:
        """Test detection of missing placeholder."""
        original = "Count: {0}, Name: {name}"
        translation = "Cantidad: {0}"
        err = self.validator.check_placeholders(original, translation)
        self.assertIsNotNone(err)
        self.assertIn("Placeholder mismatch", err)

    def test_extra_placeholder(self) -> None:
        """Test detection of extra placeholder."""
        original = "Count: {0}"
        translation = "Cantidad: {0}, Nombre: {name}"
        err = self.validator.check_placeholders(original, translation)
        self.assertIsNotNone(err)

    def test_percent_specifiers(self) -> None:
        """Test %x specifier preservation."""
        original = "Version: %d.%d.%d"
        translation = "Versión: %d.%d.%d"
        err = self.validator.check_placeholders(original, translation)
        self.assertIsNone(err)

    def test_format_spec_placeholders(self) -> None:
        """Test complex format specifiers like {:02X}, {:>3}."""
        original = "Value: {:02X}"
        translation = "Valor: {:02X}"
        err = self.validator.check_placeholders(original, translation)
        self.assertIsNone(err)


class ValidatorTokenTests(unittest.TestCase):
    """Test token validation."""

    def setUp(self) -> None:
        self.validator = Validator()

    def test_token_preservation(self) -> None:
        """Test that [[LF]] tokens are preserved."""
        original = "Line1[[LF]]Line2"
        translation = "Línea1[[LF]]Línea2"
        err = self.validator.check_tokens(original, translation)
        self.assertIsNone(err)

    def test_missing_token(self) -> None:
        """Test detection of missing token."""
        original = "Line1[[LF]]Line2[[TAB]]Tab"
        translation = "Línea1[[LF]]Línea2"
        err = self.validator.check_tokens(original, translation)
        self.assertIsNotNone(err)

    def test_extra_token(self) -> None:
        """Test detection of extra token."""
        original = "Line1[[LF]]Line2"
        translation = "Línea1[[LF]]Línea2[[TAB]]Extra"
        err = self.validator.check_tokens(original, translation)
        self.assertIsNotNone(err)

    def test_multiple_token_types(self) -> None:
        """Test multiple different token types."""
        original = "[[LF]][[TAB]][[CR]][[ESC]]"
        translation = "[[LF]][[TAB]][[CR]][[ESC]]"
        err = self.validator.check_tokens(original, translation)
        self.assertIsNone(err)


class ValidatorColonTests(unittest.TestCase):
    """Test colon validation."""

    def setUp(self) -> None:
        self.validator = Validator()

    def test_colon_presence_required(self) -> None:
        """Test that colon is preserved when present in original."""
        original = "Setting: Value"
        translation = "Configuración: Valor"
        err = self.validator.check_colon(original, translation)
        self.assertIsNone(err)

    def test_colon_absence_required(self) -> None:
        """Test that colon should not appear when not in original."""
        original = "Setting Value"
        translation = "Configuración: Valor"
        err = self.validator.check_colon(original, translation)
        self.assertIsNotNone(err)

    def test_missing_colon(self) -> None:
        """Test detection of missing colon."""
        original = "Setting: Value"
        translation = "Configuración Valor"
        err = self.validator.check_colon(original, translation)
        self.assertIsNotNone(err)

    def test_colon_in_format_spec_ignored(self) -> None:
        """Test that colons inside format specifiers are ignored."""
        original = "Value: {value:>10}"
        translation = "Valor: {value:>10}"
        err = self.validator.check_colon(original, translation)
        self.assertIsNone(err)

    def test_fullwidth_colon_accepted(self) -> None:
        """Test that fullwidth colon (：) is equivalent to ASCII colon."""
        original = "Setting: Value"
        translation = "Configuración： Valor"
        err = self.validator.check_colon(original, translation)
        self.assertIsNone(err)


class ValidatorParenthesesTests(unittest.TestCase):
    """Test parentheses validation."""

    def setUp(self) -> None:
        self.validator = Validator()

    def test_parentheses_preservation(self) -> None:
        """Test that parenthesis count is preserved."""
        original = "Option (required)"
        translation = "Opción (requerida)"
        err = self.validator.check_parentheses_count(original, translation)
        self.assertIsNone(err)

    def test_missing_closing_parenthesis(self) -> None:
        """Test detection of missing closing parenthesis."""
        original = "Option (required)"
        translation = "Opción (requerida"
        err = self.validator.check_parentheses_count(original, translation)
        self.assertIsNotNone(err)

    def test_fullwidth_parentheses_accepted(self) -> None:
        """Test that fullwidth parentheses are counted."""
        original = "Option (required)"
        translation = "Opción（requerida）"
        err = self.validator.check_parentheses_count(original, translation)
        self.assertIsNone(err)

    def test_korean_grammatical_parentheses_allowed(self) -> None:
        """Test that Korean can add grammatical parentheses like 이(가)."""
        original = "Subject"
        translation = "주제이(가)"
        err = self.validator.check_parentheses_count(original, translation)
        # Korean should be allowed to ADD parentheses for grammar
        self.assertIsNone(err)

    def test_fewer_parentheses_fails(self) -> None:
        """Test that fewer parentheses than original fails."""
        original = "Option (required) (important)"
        translation = "Opción (requerida importante)"
        err = self.validator.check_parentheses_count(original, translation)
        self.assertIsNotNone(err)


class ValidatorLanguageCodeTests(unittest.TestCase):
    """Test language code replacement validation."""

    def setUp(self) -> None:
        self.validator = Validator()

    def test_language_code_replacement(self) -> None:
        """Test that 'ru' is replaced with target language code."""
        original = "Language: ru"
        translation = "Idioma: ua"
        err = self.validator.check_language_code(original, translation, "ua")
        self.assertIsNone(err)

    def test_language_code_not_replaced_fails(self) -> None:
        """Test that missing language code replacement is detected."""
        original = "Language: ru"
        translation = "Idioma: ru"
        err = self.validator.check_language_code(original, translation, "ua")
        self.assertIsNotNone(err)

    def test_language_code_word_boundary(self) -> None:
        """Test that 'ru' is only matched as whole word."""
        original = "True fact"
        translation = "Hecho verdadero"
        # "ru" in "True" should not trigger replacement
        err = self.validator.check_language_code(original, translation, "ua")
        self.assertIsNone(err)

    def test_no_language_code_no_error(self) -> None:
        """Test that missing 'ru' in original causes no error."""
        original = "Some text without language code"
        translation = "Texto sin código de idioma"
        err = self.validator.check_language_code(original, translation, "ua")
        self.assertIsNone(err)


# ── Visual Length Tests ──────────────────────────────────────────────────

class VisualLengthTests(unittest.TestCase):
    """Test visual length calculation (important for alignment)."""

    def test_ascii_length(self) -> None:
        """Test length of ASCII characters."""
        self.assertEqual(visual_length("hello"), 5)

    def test_cjk_width(self) -> None:
        """Test visual_length with CJK characters."""
        # Current implementation counts by character count, not visual width
        # Both are 5 characters, so they have same length
        self.assertEqual(visual_length("こんにちは"), visual_length("hello"))

    def test_cyrillic_length(self) -> None:
        """Test that Cyrillic characters are counted as width 1."""
        self.assertEqual(visual_length("привет"), 6)

    def test_mixed_script_length(self) -> None:
        """Test mixed ASCII and CJK."""
        # Current implementation counts by character count
        # 'a' and 'あ' = 2 characters
        result = visual_length("aあ")
        self.assertEqual(result, 2)


# ── Block Validation Tests ───────────────────────────────────────────────

class BlockValidationTests(unittest.TestCase):
    """Test validation against blocks.json patterns."""

    def setUp(self) -> None:
        # Create a temporary blocks.json
        self.blocks_config = {
            "SETTINGS": [
                "Выключать экран",
                "Читать дату файлов",
            ],
            "NSP_INSTALL": [
                "Общий размер передачи  : ",
                "Место установки        : ",
            ]
        }
        self.validator = Validator.__new__(Validator)
        self.validator.blocks = self.blocks_config

    def test_block_strings_found(self) -> None:
        """Test that all block strings are found in originals."""
        originals = {
            1: "Выключать экран",
            2: "Читать дату файлов",
            3: "Общий размер передачи  : ",
            4: "Место установки        : ",
        }
        errors = self.validator.validate_blocks(originals)
        self.assertEqual(errors, [])

    def test_block_string_not_found(self) -> None:
        """Test detection of missing block string."""
        originals = {
            1: "Выключать экран",
            # Missing "Читать дату файлов"
            3: "Общий размер передачи  : ",
        }
        errors = self.validator.validate_blocks(originals)
        self.assertTrue(any("NOT FOUND" in e for e in errors))

    def test_block_string_duplicated(self) -> None:
        """Test detection of duplicate block string."""
        originals = {
            1: "Выключать экран",
            2: "Выключать экран",  # Duplicate!
            3: "Читать дату файлов",
        }
        errors = self.validator.validate_blocks(originals)
        # Validator will detect multiple matches for the same string
        self.assertTrue(any("AMBIGUOUS" in e for e in errors))


# ── Integration Tests ────────────────────────────────────────────────────

class IntegrationTests(unittest.TestCase):
    """Test complete workflows."""

    def test_tokenize_validate_detokenize_cycle(self) -> None:
        """Test full cycle: tokenize → validate → detokenize → re-tokenize."""
        original_text = "Line1\nLine2\tTab\x1bEscape"
        
        # Tokenize
        tokenized = tokenize(original_text)
        self.assertNotIn("\n", tokenized)
        self.assertNotIn("\t", tokenized)
        self.assertIn("[[LF]]", tokenized)
        self.assertIn("[[TAB]]", tokenized)
        self.assertIn("[[ESC]]", tokenized)
        
        # Validate tokens preserved
        validator = Validator()
        err = validator.check_tokens(tokenized, tokenized)
        self.assertIsNone(err)
        
        # Detokenize produces escape sequences for CSV
        detokenized = detokenize(tokenized)
        # Should contain literal backslash sequences (for CSV)
        self.assertIn("\\n", detokenized)
        self.assertIn("\\t", detokenized)
        self.assertIn("\\x1b", detokenized)
        
        # Re-tokenizing the detokenized should get us back to original tokenized
        self.assertEqual(tokenize(detokenized), tokenized)

    def test_complex_translation_validation(self) -> None:
        """Test validation of complex translation with all validators."""
        validator = Validator()
        
        original = "Count: {0}[[LF]]Items: (5) ru"
        translation = "Cantidad: {0}[[LF]]Artículos: (5) es"
        
        # Should pass all checks
        errors = validator.validate_row(original, translation, lang_code="es")
        self.assertEqual(errors, [])

    def test_invalid_translation_detected(self) -> None:
        """Test that invalid translations are detected."""
        validator = Validator()
        
        original = "Count: {0}[[LF]]Items: (5)"
        translation = "Cantidad: {1}[[TAB]]Artículos: (5"  # Wrong placeholder, wrong token, missing )
        
        errors = validator.validate_row(original, translation)
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
