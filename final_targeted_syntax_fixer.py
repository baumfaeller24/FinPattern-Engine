#!/usr/bin/env python3
"""
Final Targeted Syntax Fixer - Präzise Reparatur spezifischer Probleme
Behebt die Over-Indentation-Probleme der vorherigen Fixer

Features:
- Präzise Indentation-Korrektur
- Docstring-Schutz
- Import-Statement-Bereinigung
- Minimal-invasive Reparatur
"""

import re
import os
import json
import logging
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinalTargetedSyntaxFixer:
    """Finale präzise Syntax-Reparatur"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.backup_dir = Path("final_targeted_backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.fixes_applied = []
    
    def fix_file_targeted(self, file_path: str) -> Dict[str, Any]:
        """Präzise Syntax-Reparatur für spezifische Probleme"""
        
        try:
            # Backup erstellen
            backup_path = self.backup_dir / f"{Path(file_path).name}.final_backup"
            shutil.copy2(file_path, backup_path)
            
            # Datei lesen
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            self.logger.info(f"🎯 Final targeted fixing: {file_path}")
            
            content = original_content
            fixes_applied = []
            
            # Fix 1: Bereinige fehlplatzierte Import-Statements in Docstrings
            content, import_fixes = self._fix_misplaced_imports(content)
            fixes_applied.extend(import_fixes)
            
            # Fix 2: Korrigiere Over-Indentation
            content, indent_fixes = self._fix_over_indentation(content)
            fixes_applied.extend(indent_fixes)
            
            # Fix 3: Bereinige Docstring-Probleme
            content, docstring_fixes = self._fix_docstring_issues(content)
            fixes_applied.extend(docstring_fixes)
            
            # Fix 4: Normalisiere Top-Level-Code
            content, toplevel_fixes = self._normalize_toplevel_code(content)
            fixes_applied.extend(toplevel_fixes)
            
            # Syntax-Validierung
            try:
                compile(content, file_path, 'exec')
                syntax_valid = True
                self.logger.info(f"✅ Perfect syntax achieved for {file_path}")
            except SyntaxError as e:
                syntax_valid = False
                self.logger.warning(f"⚠️ Syntax still invalid for {file_path}: {e}")
            
            # Schreibe zurück
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.fixes_applied.append({
                    "file": file_path,
                    "fixes": fixes_applied,
                    "backup": str(backup_path)
                })
            
            return {
                "file": file_path,
                "success": True,
                "syntax_valid": syntax_valid,
                "fixes_applied": fixes_applied,
                "backup_created": str(backup_path)
            }
            
        except Exception as e:
            self.logger.error(f"Final targeted fixing failed for {file_path}: {e}")
            return {
                "file": file_path,
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _fix_misplaced_imports(self, content: str) -> Tuple[str, List[str]]:
        """Bereinige fehlplatzierte Import-Statements"""
        fixes_applied = []
        lines = content.split('\n')
        fixed_lines = []
        
        in_docstring = False
        docstring_delimiter = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Erkenne Docstring-Grenzen
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    in_docstring = True
                    docstring_delimiter = '"""' if '"""' in line else "'''"
                elif docstring_delimiter in line:
                    in_docstring = False
                    docstring_delimiter = None
            
            # Entferne Import-Statements aus Docstrings
            if in_docstring and stripped.startswith(('from ', 'import ')):
                fixes_applied.append(f"Removed misplaced import from docstring at line {i+1}")
                continue
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines), fixes_applied
    
    def _fix_over_indentation(self, content: str) -> Tuple[str, List[str]]:
        """Korrigiere Over-Indentation-Probleme"""
        fixes_applied = []
        lines = content.split('\n')
        fixed_lines = []
        
        # Erkenne das Indentation-Pattern
        first_code_line_indent = None
        in_docstring = False
        
        for i, line in enumerate(lines):
            if not line.strip():
                fixed_lines.append(line)
                continue
            
            stripped = line.strip()
            current_indent = len(line) - len(line.lstrip())
            
            # Erkenne Docstring-Grenzen
            if '"""' in line or "'''" in line:
                in_docstring = not in_docstring
                fixed_lines.append(line)
                continue
            
            # Skip Docstring-Inhalt
            if in_docstring:
                fixed_lines.append(line)
                continue
            
            # Erkenne erste echte Code-Zeile nach Docstring
            if (first_code_line_indent is None and 
                not stripped.startswith('#') and 
                stripped not in ['"""', "'''"]):
                
                # Wenn die erste Code-Zeile eingerückt ist, aber ein Top-Level-Statement ist
                if (current_indent > 0 and 
                    (stripped.startswith(('import ', 'from ', 'class ', 'def ', '@')) or
                     stripped in ['if __name__ == "__main__":'])):
                    first_code_line_indent = current_indent
                    self.logger.info(f"Detected over-indentation pattern: {first_code_line_indent} spaces")
            
            # Korrigiere Over-Indentation
            if first_code_line_indent and current_indent >= first_code_line_indent:
                # Reduziere Indentation um das Over-Indentation-Level
                new_indent = max(0, current_indent - first_code_line_indent)
                fixed_line = ' ' * new_indent + stripped
                fixed_lines.append(fixed_line)
                
                if current_indent != new_indent:
                    fixes_applied.append(f"Line {i+1}: Fixed over-indentation {current_indent} → {new_indent}")
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines), fixes_applied
    
    def _fix_docstring_issues(self, content: str) -> Tuple[str, List[str]]:
        """Bereinige Docstring-Probleme"""
        fixes_applied = []
        
        # Fix: Entferne doppelte Docstring-Delimiter
        content = re.sub(r'"""[\s\n]*"""', '"""', content)
        if '"""' in content:
            fixes_applied.append("Fixed duplicate docstring delimiters")
        
        return content, fixes_applied
    
    def _normalize_toplevel_code(self, content: str) -> Tuple[str, List[str]]:
        """Normalisiere Top-Level-Code-Struktur"""
        fixes_applied = []
        lines = content.split('\n')
        fixed_lines = []
        
        # Sammle alle Import-Statements
        imports = []
        other_lines = []
        
        in_docstring = False
        docstring_lines = []
        shebang_and_encoding = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Shebang und Encoding
            if i < 3 and (line.startswith('#!') or 'coding:' in line or 'encoding:' in line):
                shebang_and_encoding.append(line)
                continue
            
            # Docstring-Erkennung
            if '"""' in line and not in_docstring:
                in_docstring = True
                docstring_lines.append(line)
                continue
            elif '"""' in line and in_docstring:
                in_docstring = False
                docstring_lines.append(line)
                continue
            elif in_docstring:
                docstring_lines.append(line)
                continue
            
            # Import-Statements sammeln
            if stripped.startswith(('import ', 'from ')) and not in_docstring:
                imports.append(line.lstrip())  # Entferne führende Spaces
                continue
            
            # Andere Zeilen
            other_lines.append(line)
        
        # Rekonstruiere Datei-Struktur
        if shebang_and_encoding:
            fixed_lines.extend(shebang_and_encoding)
        
        if docstring_lines:
            fixed_lines.extend(docstring_lines)
        
        if imports:
            if fixed_lines and fixed_lines[-1].strip():
                fixed_lines.append('')  # Leerzeile vor Imports
            fixed_lines.extend(sorted(set(imports)))  # Dedupliziere und sortiere
            fixes_applied.append(f"Normalized {len(imports)} import statements")
        
        if other_lines:
            if fixed_lines and fixed_lines[-1].strip():
                fixed_lines.append('')  # Leerzeile vor Code
            fixed_lines.extend(other_lines)
        
        return '\n'.join(fixed_lines), fixes_applied
    
    def run_final_targeted_fixes(self, target_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Führe finale gezielte Syntax-Fixes aus"""
        
        if target_files is None:
            target_files = [
                "ai_indicator_optimizer/ai/pine_script_validator.py",
                "ai_indicator_optimizer/ai/indicator_code_builder.py", 
                "ai_indicator_optimizer/testing/backtesting_framework.py",
                "ai_indicator_optimizer/library/synthetic_pattern_generator.py",
                "strategies/ai_strategies/ai_pattern_strategy.py"
            ]
        
        start_time = datetime.now()
        results = []
        
        self.logger.info(f"🎯 Starting final targeted syntax fixes on {len(target_files)} files")
        
        for file_path in target_files:
            if Path(file_path).exists():
                result = self.fix_file_targeted(file_path)
                results.append(result)
                
                if result["success"] and result["syntax_valid"]:
                    self.logger.info(f"✅ PERFECTLY FIXED: {file_path}")
                elif result["success"]:
                    self.logger.warning(f"⚠️ PARTIALLY FIXED: {file_path}")
                else:
                    self.logger.error(f"❌ FAILED: {file_path}")
            else:
                results.append({
                    "file": file_path,
                    "success": False,
                    "error": "File not found"
                })
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Statistiken
        perfect_fixes = [r for r in results if r["success"] and r.get("syntax_valid", False)]
        partial_fixes = [r for r in results if r["success"] and not r.get("syntax_valid", False)]
        failed_fixes = [r for r in results if not r["success"]]
        
        summary = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_files": len(target_files),
            "perfect_fixes": len(perfect_fixes),
            "partial_fixes": len(partial_fixes),
            "failed_fixes": len(failed_fixes),
            "results": results,
            "fixes_applied": self.fixes_applied
        }
        
        # Save results
        with open("final_targeted_syntax_fixes_results.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"✅ Final targeted syntax fixing completed in {duration:.2f}s")
        self.logger.info(f"📊 Perfect: {len(perfect_fixes)}, Partial: {len(partial_fixes)}, Failed: {len(failed_fixes)}")
        
        return summary


def main():
    """Hauptfunktion für finale gezielte Syntax-Fixes"""
    print("🎯 Starting Final Targeted Syntax Fixing...")
    print("⚡ Precise over-indentation repair")
    print("🔧 Minimal-invasive corrections")
    
    fixer = FinalTargetedSyntaxFixer()
    
    try:
        results = fixer.run_final_targeted_fixes()
        
        print("✅ Final targeted syntax fixing completed!")
        print(f"📊 Results saved to: final_targeted_syntax_fixes_results.json")
        
        # Zusammenfassung
        print(f"\n🎯 Final Targeted Fix Summary:")
        print(f"   Total Files: {results['total_files']}")
        print(f"   Perfect Fixes: {results['perfect_fixes']}")
        print(f"   Partial Fixes: {results['partial_fixes']}")
        print(f"   Failed Fixes: {results['failed_fixes']}")
        print(f"   Duration: {results['duration_seconds']:.2f} seconds")
        
        # Datei-spezifische Ergebnisse
        print(f"\n📋 File Results:")
        for result in results['results']:
            if result['success'] and result.get('syntax_valid', False):
                fixes_count = len(result.get('fixes_applied', []))
                print(f"   ✅ {result['file']}: PERFECT ({fixes_count} fixes)")
            elif result['success']:
                fixes_count = len(result.get('fixes_applied', []))
                print(f"   ⚠️ {result['file']}: PARTIAL ({fixes_count} fixes)")
            else:
                print(f"   ❌ {result['file']}: FAILED - {result.get('error', 'Unknown error')}")
        
        # Final validation
        print(f"\n🧪 Final Syntax Validation:")
        import subprocess
        for result in results['results']:
            if result['success']:
                file_path = result['file']
                try:
                    subprocess.run(['python3', '-m', 'py_compile', file_path], 
                                 check=True, capture_output=True)
                    print(f"   ✅ {file_path}: SYNTAX PERFECT")
                except subprocess.CalledProcessError:
                    print(f"   ⚠️ {file_path}: Still needs attention")
        
    except Exception as e:
        print(f"\n❌ Final targeted syntax fixing failed: {e}")
        logger.error(f"Final targeted syntax fixing failed: {e}")


if __name__ == "__main__":
    main()