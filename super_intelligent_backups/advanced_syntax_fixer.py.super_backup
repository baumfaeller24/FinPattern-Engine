#!/usr/bin/env python3
"""
Advanced Syntax Fixer für AI-Indicator-Optimizer
Intelligente Lösung komplexer Syntax-Probleme mit AST-Analyse

Features:
- AST-basierte Syntax-Analyse und -Reparatur
- Intelligente Indentation-Korrektur
- Komplexe Try-Except-Block-Vervollständigung
- Import-Statement-Reparatur
- Bracket/Parentheses-Matching
- Function/Class-Definition-Fixes
- Context-aware Code-Reparatur
"""

import ast
import re
import os
import json
import logging
import traceback
import tokenize
import io
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import shutil
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('advanced_syntax_fixes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SyntaxAnalyzer:
    """AST-basierte Syntax-Analyse"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_syntax_errors(self, content: str) -> List[Dict[str, Any]]:
        """Analysiere Syntax-Fehler mit detaillierter Diagnose"""
        errors = []
        
        try:
            ast.parse(content)
            return []  # Keine Syntax-Fehler
        except SyntaxError as e:
            error_info = {
                "type": "SyntaxError",
                "message": str(e),
                "line": e.lineno,
                "column": e.offset,
                "text": e.text,
                "filename": e.filename
            }
            
            # Klassifiziere Fehler-Typ
            error_info["category"] = self._classify_syntax_error(e)
            error_info["suggested_fix"] = self._suggest_fix(e, content)
            
            errors.append(error_info)
            
        except Exception as e:
            errors.append({
                "type": "ParseError",
                "message": str(e),
                "category": "unknown",
                "suggested_fix": None
            })
        
        return errors
    
    def _classify_syntax_error(self, error: SyntaxError) -> str:
        """Klassifiziere Syntax-Fehler-Typ"""
        msg = str(error).lower()
        
        if "unindent does not match" in msg:
            return "indentation_mismatch"
        elif "expected an indented block" in msg:
            return "missing_indentation"
        elif "unexpected indent" in msg:
            return "unexpected_indentation"
        elif "expected 'except' or 'finally'" in msg:
            return "incomplete_try_block"
        elif "invalid syntax" in msg and error.text and ":" in error.text:
            return "missing_colon"
        elif "unexpected eof" in msg:
            return "unexpected_eof"
        elif "unmatched" in msg or "closing parenthesis" in msg:
            return "unmatched_brackets"
        elif "invalid character" in msg:
            return "invalid_character"
        else:
            return "unknown_syntax_error"
    
    def _suggest_fix(self, error: SyntaxError, content: str) -> Optional[str]:
        """Schlage Fix für Syntax-Fehler vor"""
        category = self._classify_syntax_error(error)
        
        if category == "indentation_mismatch":
            return "Fix indentation levels to match Python requirements"
        elif category == "missing_indentation":
            return "Add proper indentation after colon"
        elif category == "incomplete_try_block":
            return "Add missing except or finally block"
        elif category == "unmatched_brackets":
            return "Balance parentheses, brackets, or braces"
        elif category == "missing_colon":
            return "Add missing colon after control statement"
        else:
            return "Manual review required"


class IndentationFixer:
    """Intelligente Indentation-Korrektur"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def fix_indentation(self, content: str) -> Tuple[str, List[str]]:
        """Korrigiere Indentation-Probleme intelligent"""
        lines = content.split('\n')
        fixed_lines = []
        fixes_applied = []
        
        # Analyse der aktuellen Indentation
        indent_stack = [0]  # Stack für Indentation-Level
        
        for i, line in enumerate(lines):
            if not line.strip():
                fixed_lines.append(line)
                continue
            
            # Bestimme erwartete Indentation
            expected_indent = self._calculate_expected_indent(
                line, fixed_lines, indent_stack
            )
            
            current_indent = len(line) - len(line.lstrip())
            
            if current_indent != expected_indent:
                # Korrigiere Indentation
                fixed_line = ' ' * expected_indent + line.lstrip()
                fixed_lines.append(fixed_line)
                fixes_applied.append(f"Line {i+1}: Fixed indentation from {current_indent} to {expected_indent}")
            else:
                fixed_lines.append(line)
            
            # Update Indentation-Stack
            self._update_indent_stack(line, indent_stack, expected_indent)
        
        return '\n'.join(fixed_lines), fixes_applied
    
    def _calculate_expected_indent(self, line: str, previous_lines: List[str], 
                                 indent_stack: List[int]) -> int:
        """Berechne erwartete Indentation für Zeile"""
        stripped = line.strip()
        
        # Spezielle Fälle
        if stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'with ', 'try:')):
            return indent_stack[-1]
        elif stripped.startswith(('except ', 'finally:', 'elif ', 'else:')):
            return indent_stack[-2] if len(indent_stack) > 1 else 0
        elif stripped.startswith(('return ', 'break', 'continue', 'pass', 'raise ')):
            return indent_stack[-1] + 4
        else:
            # Standard-Indentation basierend auf vorheriger Zeile
            if previous_lines:
                prev_line = previous_lines[-1].strip()
                if prev_line.endswith(':'):
                    return indent_stack[-1] + 4
            
            return indent_stack[-1] + 4 if indent_stack[-1] > 0 else indent_stack[-1]
    
    def _update_indent_stack(self, line: str, indent_stack: List[int], current_indent: int):
        """Update Indentation-Stack basierend auf aktueller Zeile"""
        stripped = line.strip()
        
        if stripped.endswith(':'):
            # Neue Indentation-Ebene
            indent_stack.append(current_indent + 4)
        elif stripped.startswith(('except ', 'finally:', 'elif ', 'else:')):
            # Gleiche Ebene wie try/if
            if len(indent_stack) > 1:
                indent_stack.pop()
        elif current_indent < indent_stack[-1]:
            # Reduzierte Indentation
            while len(indent_stack) > 1 and indent_stack[-1] > current_indent:
                indent_stack.pop()


class TryExceptFixer:
    """Intelligente Try-Except-Block-Vervollständigung"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def fix_try_blocks(self, content: str) -> Tuple[str, List[str]]:
        """Vervollständige unvollständige Try-Blocks"""
        lines = content.split('\n')
        fixed_lines = []
        fixes_applied = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if stripped.startswith('try:'):
                # Finde Try-Block-Ende
                try_indent = len(line) - len(line.lstrip())
                block_lines, block_end, has_except = self._extract_try_block(lines, i)
                
                if not has_except:
                    # Füge except-Block hinzu
                    except_block = [
                        ' ' * try_indent + 'except Exception as e:',
                        ' ' * (try_indent + 4) + 'logger.error(f"Error: {e}")',
                        ' ' * (try_indent + 4) + 'pass'
                    ]
                    
                    fixed_lines.extend(block_lines)
                    fixed_lines.extend(except_block)
                    fixes_applied.append(f"Added except block after line {i+1}")
                    
                    i = block_end
                else:
                    fixed_lines.extend(block_lines)
                    i = block_end
            else:
                fixed_lines.append(line)
                i += 1
        
        return '\n'.join(fixed_lines), fixes_applied
    
    def _extract_try_block(self, lines: List[str], start_idx: int) -> Tuple[List[str], int, bool]:
        """Extrahiere Try-Block und prüfe auf except/finally"""
        block_lines = [lines[start_idx]]  # try: Zeile
        try_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
        has_except = False
        
        i = start_idx + 1
        while i < len(lines):
            line = lines[i]
            
            if not line.strip():
                block_lines.append(line)
                i += 1
                continue
            
            current_indent = len(line) - len(line.lstrip())
            stripped = line.strip()
            
            # Prüfe auf except/finally auf gleicher Ebene wie try
            if current_indent == try_indent and (stripped.startswith('except ') or 
                                               stripped.startswith('finally:')):
                has_except = True
                block_lines.append(line)
                
                # Füge except/finally-Body hinzu
                i += 1
                while i < len(lines) and (not lines[i].strip() or 
                                        len(lines[i]) - len(lines[i].lstrip()) > try_indent):
                    block_lines.append(lines[i])
                    i += 1
                break
            
            # Prüfe auf Ende des Try-Blocks
            elif current_indent <= try_indent and stripped and not stripped.startswith(('except ', 'finally:')):
                break
            else:
                block_lines.append(line)
                i += 1
        
        return block_lines, i, has_except


class BracketMatcher:
    """Intelligente Bracket/Parentheses-Matching"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.bracket_pairs = {'(': ')', '[': ']', '{': '}'}
    
    def fix_unmatched_brackets(self, content: str) -> Tuple[str, List[str]]:
        """Korrigiere unmatched brackets"""
        fixes_applied = []
        
        try:
            # Tokenize um Strings zu ignorieren
            tokens = list(tokenize.generate_tokens(io.StringIO(content).readline))
            
            bracket_stack = []
            bracket_positions = []
            
            for token in tokens:
                if token.type == tokenize.OP:
                    if token.string in self.bracket_pairs:
                        bracket_stack.append((token.string, token.start))
                        bracket_positions.append(token.start)
                    elif token.string in self.bracket_pairs.values():
                        if bracket_stack:
                            open_bracket, pos = bracket_stack.pop()
                            if self.bracket_pairs[open_bracket] != token.string:
                                # Mismatch gefunden
                                fixes_applied.append(f"Bracket mismatch at line {token.start[0]}")
                        else:
                            # Closing bracket ohne opening
                            fixes_applied.append(f"Unmatched closing bracket at line {token.start[0]}")
            
            # Unmatched opening brackets
            for bracket, pos in bracket_stack:
                fixes_applied.append(f"Unmatched opening bracket '{bracket}' at line {pos[0]}")
                # Füge closing bracket am Ende hinzu
                content += self.bracket_pairs[bracket]
            
        except Exception as e:
            self.logger.warning(f"Bracket matching failed: {e}")
        
        return content, fixes_applied


class AdvancedSyntaxFixer:
    """
    Advanced Syntax Fixer mit intelligenter AST-basierter Reparatur
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.syntax_analyzer = SyntaxAnalyzer()
        self.indentation_fixer = IndentationFixer()
        self.try_except_fixer = TryExceptFixer()
        self.bracket_matcher = BracketMatcher()
        
        self.backup_dir = Path("advanced_syntax_backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        self.fixes_applied = []
        self.failed_fixes = []
    
    def fix_file_advanced(self, file_path: str, max_iterations: int = 5) -> Dict[str, Any]:
        """Erweiterte Syntax-Reparatur mit mehreren Iterationen"""
        
        try:
            # Backup erstellen
            backup_path = self.backup_dir / f"{Path(file_path).name}.advanced_backup"
            shutil.copy2(file_path, backup_path)
            
            # Datei lesen
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            all_fixes_applied = []
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                self.logger.info(f"🔄 Iteration {iteration} for {file_path}")
                
                # Analysiere aktuelle Syntax-Fehler
                errors = self.syntax_analyzer.analyze_syntax_errors(content)
                
                if not errors:
                    self.logger.info(f"✅ No syntax errors found in iteration {iteration}")
                    break
                
                iteration_fixes = []
                old_content = content
                
                # Wende verschiedene Fixes an
                for error in errors:
                    if error["category"] == "indentation_mismatch":
                        content, fixes = self.indentation_fixer.fix_indentation(content)
                        iteration_fixes.extend(fixes)
                    
                    elif error["category"] == "incomplete_try_block":
                        content, fixes = self.try_except_fixer.fix_try_blocks(content)
                        iteration_fixes.extend(fixes)
                    
                    elif error["category"] == "unmatched_brackets":
                        content, fixes = self.bracket_matcher.fix_unmatched_brackets(content)
                        iteration_fixes.extend(fixes)
                    
                    elif error["category"] == "missing_indentation":
                        content = self._fix_missing_indentation(content, error)
                        iteration_fixes.append(f"Fixed missing indentation at line {error.get('line', 'unknown')}")
                    
                    elif error["category"] == "missing_colon":
                        content = self._fix_missing_colon(content, error)
                        iteration_fixes.append(f"Added missing colon at line {error.get('line', 'unknown')}")
                
                # Zusätzliche generische Fixes
                content, generic_fixes = self._apply_generic_fixes(content)
                iteration_fixes.extend(generic_fixes)
                
                all_fixes_applied.extend(iteration_fixes)
                
                # Prüfe ob Fortschritt gemacht wurde
                if content == old_content:
                    self.logger.warning(f"No progress in iteration {iteration}, stopping")
                    break
                
                self.logger.info(f"Applied {len(iteration_fixes)} fixes in iteration {iteration}")
            
            # Final syntax check
            final_errors = self.syntax_analyzer.analyze_syntax_errors(content)
            syntax_valid = len(final_errors) == 0
            
            # Schreibe zurück wenn Änderungen
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.fixes_applied.append({
                    "file": file_path,
                    "type": "advanced_syntax",
                    "iterations": iteration,
                    "fixes": all_fixes_applied,
                    "backup": str(backup_path)
                })
            
            return {
                "file": file_path,
                "success": True,
                "syntax_valid": syntax_valid,
                "iterations": iteration,
                "fixes_applied": all_fixes_applied,
                "remaining_errors": final_errors,
                "backup_created": str(backup_path)
            }
            
        except Exception as e:
            self.logger.error(f"Advanced syntax fixing failed for {file_path}: {e}")
            return {
                "file": file_path,
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _fix_missing_indentation(self, content: str, error: Dict[str, Any]) -> str:
        """Fix missing indentation nach Colon"""
        lines = content.split('\n')
        
        if error.get('line') and error['line'] <= len(lines):
            line_idx = error['line'] - 1
            
            # Prüfe ob nächste Zeile Indentation braucht
            if line_idx + 1 < len(lines):
                current_line = lines[line_idx]
                next_line = lines[line_idx + 1]
                
                if current_line.strip().endswith(':') and next_line.strip() and not next_line.startswith(' '):
                    # Füge Indentation hinzu
                    current_indent = len(current_line) - len(current_line.lstrip())
                    lines[line_idx + 1] = ' ' * (current_indent + 4) + next_line.strip()
        
        return '\n'.join(lines)
    
    def _fix_missing_colon(self, content: str, error: Dict[str, Any]) -> str:
        """Fix missing colon nach Control-Statements"""
        lines = content.split('\n')
        
        if error.get('line') and error['line'] <= len(lines):
            line_idx = error['line'] - 1
            line = lines[line_idx]
            
            # Prüfe auf Control-Statements ohne Colon
            control_keywords = ['if ', 'elif ', 'else', 'for ', 'while ', 'def ', 'class ', 'try', 'except ', 'finally', 'with ']
            
            for keyword in control_keywords:
                if keyword in line and not line.strip().endswith(':'):
                    lines[line_idx] = line.rstrip() + ':'
                    break
        
        return '\n'.join(lines)
    
    def _apply_generic_fixes(self, content: str) -> Tuple[str, List[str]]:
        """Wende generische Syntax-Fixes an"""
        fixes_applied = []
        
        # Fix common patterns
        patterns = [
            # Fix function definitions without colon
            (r'^(\s*def\s+\w+\s*\([^)]*\))\s*$', r'\1:', "Added missing colon to function definition"),
            
            # Fix class definitions without colon
            (r'^(\s*class\s+\w+(?:\([^)]*\))?)\s*$', r'\1:', "Added missing colon to class definition"),
            
            # Fix if statements without colon
            (r'^(\s*if\s+.+)\s*$', r'\1:', "Added missing colon to if statement"),
            
            # Fix for loops without colon
            (r'^(\s*for\s+.+\s+in\s+.+)\s*$', r'\1:', "Added missing colon to for loop"),
            
            # Fix while loops without colon
            (r'^(\s*while\s+.+)\s*$', r'\1:', "Added missing colon to while loop"),
            
            # Fix try statements without colon
            (r'^(\s*try)\s*$', r'\1:', "Added missing colon to try statement"),
            
            # Fix except statements without colon
            (r'^(\s*except(?:\s+\w+)?(?:\s+as\s+\w+)?)\s*$', r'\1:', "Added missing colon to except statement"),
            
            # Fix finally statements without colon
            (r'^(\s*finally)\s*$', r'\1:', "Added missing colon to finally statement"),
            
            # Fix with statements without colon
            (r'^(\s*with\s+.+)\s*$', r'\1:', "Added missing colon to with statement"),
        ]
        
        for pattern, replacement, description in patterns:
            old_content = content
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            if content != old_content:
                fixes_applied.append(description)
        
        return content, fixes_applied
    
    def run_advanced_fixes(self, target_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Führe erweiterte Syntax-Fixes auf Ziel-Dateien aus"""
        
        if target_files is None:
            # Standard problematische Dateien
            target_files = [
                "ai_indicator_optimizer/ai/pine_script_validator.py",
                "ai_indicator_optimizer/ai/indicator_code_builder.py", 
                "ai_indicator_optimizer/testing/backtesting_framework.py",
                "ai_indicator_optimizer/library/synthetic_pattern_generator.py",
                "strategies/ai_strategies/ai_pattern_strategy.py"
            ]
        
        start_time = datetime.now()
        results = []
        
        self.logger.info(f"🚀 Starting advanced syntax fixes on {len(target_files)} files")
        
        for file_path in target_files:
            if Path(file_path).exists():
                self.logger.info(f"🔧 Processing: {file_path}")
                result = self.fix_file_advanced(file_path)
                results.append(result)
                
                if result["success"] and result["syntax_valid"]:
                    self.logger.info(f"✅ Successfully fixed: {file_path}")
                elif result["success"]:
                    self.logger.warning(f"⚠️ Partially fixed: {file_path} (some errors remain)")
                else:
                    self.logger.error(f"❌ Failed to fix: {file_path}")
            else:
                self.logger.warning(f"⚠️ File not found: {file_path}")
                results.append({
                    "file": file_path,
                    "success": False,
                    "error": "File not found"
                })
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Zusammenfassung
        successful_fixes = [r for r in results if r["success"] and r.get("syntax_valid", False)]
        partial_fixes = [r for r in results if r["success"] and not r.get("syntax_valid", False)]
        failed_fixes = [r for r in results if not r["success"]]
        
        summary = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_files": len(target_files),
            "successful_fixes": len(successful_fixes),
            "partial_fixes": len(partial_fixes),
            "failed_fixes": len(failed_fixes),
            "results": results,
            "fixes_applied": self.fixes_applied
        }
        
        # Save results
        with open("advanced_syntax_fixes_results.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"✅ Advanced syntax fixing completed in {duration:.2f}s")
        self.logger.info(f"📊 Success: {len(successful_fixes)}, Partial: {len(partial_fixes)}, Failed: {len(failed_fixes)}")
        
        return summary


def main():
    """Hauptfunktion für erweiterte Syntax-Fixes"""
    print("🧠 Starting Advanced Syntax Fixing...")
    print("⚡ Intelligent AST-based syntax repair")
    print("🔄 Multi-iteration fixing with progress tracking")
    
    fixer = AdvancedSyntaxFixer()
    
    try:
        results = fixer.run_advanced_fixes()
        
        print("✅ Advanced syntax fixing completed!")
        print(f"📊 Results saved to: advanced_syntax_fixes_results.json")
        
        # Print detailed summary
        print(f"\n🎯 Detailed Summary:")
        print(f"   Total Files: {results['total_files']}")
        print(f"   Successful Fixes: {results['successful_fixes']}")
        print(f"   Partial Fixes: {results['partial_fixes']}")
        print(f"   Failed Fixes: {results['failed_fixes']}")
        print(f"   Duration: {results['duration_seconds']:.2f} seconds")
        
        # Show file-by-file results
        print(f"\n📋 File Results:")
        for result in results['results']:
            if result['success'] and result.get('syntax_valid', False):
                print(f"   ✅ {result['file']}: FULLY FIXED ({result.get('iterations', 0)} iterations)")
            elif result['success']:
                remaining = len(result.get('remaining_errors', []))
                print(f"   ⚠️ {result['file']}: PARTIALLY FIXED ({remaining} errors remain)")
            else:
                print(f"   ❌ {result['file']}: FAILED - {result.get('error', 'Unknown error')}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Advanced syntax fixing interrupted by user")
    except Exception as e:
        print(f"\n❌ Advanced syntax fixing failed: {e}")
        logger.error(f"Advanced syntax fixing failed: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()