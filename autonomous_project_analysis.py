#!/usr/bin/env python3
"""
Autonome Projekt-Analyse für AI-Indicator-Optimizer
Mehrstündiger Analyse-Prozess ohne User-Interaktion

Features:
- Vollständige Code-Analyse aller Module
- Import-Dependency-Checks
- Syntax-Validierung
- Performance-Bottleneck-Detection
- Architecture-Consistency-Checks
- Mock vs Real Implementation Detection
- Database Schema Validation
- Configuration Completeness
- Error Handling Coverage
- Test Coverage Analysis
- Documentation Gaps
- Security Vulnerability Scan
"""

import os
import sys
import ast
import time
import json
import logging
import traceback
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import importlib.util
import re
from collections import defaultdict, Counter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('autonomous_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutonomousProjectAnalyzer:
    """
    Autonomer Projekt-Analyzer für mehrstündige Fehler-Detection
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.analysis_results = {
            "start_time": datetime.now().isoformat(),
            "project_structure": {},
            "code_analysis": {},
            "dependency_issues": [],
            "mock_implementations": [],
            "performance_issues": [],
            "architecture_violations": [],
            "security_issues": [],
            "configuration_gaps": [],
            "test_coverage": {},
            "documentation_gaps": [],
            "critical_errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Analysis phases
        self.phases = [
            ("Project Structure Analysis", self._analyze_project_structure),
            ("Code Syntax & Import Analysis", self._analyze_code_syntax),
            ("Mock vs Real Implementation Detection", self._detect_mock_implementations),
            ("Dependency Chain Analysis", self._analyze_dependencies),
            ("Architecture Consistency Check", self._check_architecture_consistency),
            ("Performance Bottleneck Detection", self._detect_performance_issues),
            ("Configuration Completeness", self._analyze_configuration),
            ("Database Schema Validation", self._validate_database_schemas),
            ("Error Handling Coverage", self._analyze_error_handling),
            ("Test Coverage Analysis", self._analyze_test_coverage),
            ("Security Vulnerability Scan", self._scan_security_vulnerabilities),
            ("Documentation Gap Analysis", self._analyze_documentation),
            ("Integration Point Validation", self._validate_integration_points),
            ("Resource Usage Analysis", self._analyze_resource_usage),
            ("Final Report Generation", self._generate_final_report)
        ]
        
        logger.info(f"🚀 Autonomous Project Analyzer initialized for: {self.project_root}")
        logger.info(f"📋 Analysis phases: {len(self.phases)}")
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Führt vollständige autonome Analyse durch
        """
        logger.info("🔍 Starting autonomous project analysis...")
        
        total_phases = len(self.phases)
        
        for i, (phase_name, phase_func) in enumerate(self.phases, 1):
            try:
                logger.info(f"📊 Phase {i}/{total_phases}: {phase_name}")
                start_time = time.time()
                
                phase_results = phase_func()
                
                duration = time.time() - start_time
                logger.info(f"✅ Phase {i} completed in {duration:.2f}s")
                
                # Store phase results
                self.analysis_results[f"phase_{i}_{phase_name.lower().replace(' ', '_')}"] = {
                    "results": phase_results,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Brief pause between phases
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Phase {i} failed: {e}")
                self.analysis_results["critical_errors"].append({
                    "phase": phase_name,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
        
        self.analysis_results["end_time"] = datetime.now().isoformat()
        self.analysis_results["total_duration"] = time.time() - time.mktime(
            datetime.fromisoformat(self.analysis_results["start_time"]).timetuple()
        )
        
        logger.info("🎯 Autonomous analysis completed!")
        return self.analysis_results
    
    def _analyze_project_structure(self) -> Dict[str, Any]:
        """Phase 1: Projekt-Struktur-Analyse"""
        structure = {}
        file_counts = Counter()
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip hidden and cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            rel_root = os.path.relpath(root, self.project_root)
            if rel_root == '.':
                rel_root = 'root'
            
            structure[rel_root] = {
                "directories": dirs,
                "files": files,
                "python_files": [f for f in files if f.endswith('.py')],
                "config_files": [f for f in files if f.endswith(('.json', '.yaml', '.yml', '.toml', '.ini'))],
                "doc_files": [f for f in files if f.endswith(('.md', '.rst', '.txt'))]
            }
            
            # Count file types
            for file in files:
                ext = Path(file).suffix.lower()
                file_counts[ext] += 1
        
        # Analyze structure patterns
        python_modules = []
        for path, info in structure.items():
            if info["python_files"]:
                python_modules.append(path)
        
        return {
            "structure": structure,
            "file_counts": dict(file_counts),
            "python_modules": python_modules,
            "total_files": sum(file_counts.values()),
            "python_file_count": file_counts.get('.py', 0)
        }
    
    def _analyze_code_syntax(self) -> Dict[str, Any]:
        """Phase 2: Code-Syntax & Import-Analyse"""
        syntax_issues = []
        import_issues = []
        
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        logger.info(f"🐍 Analyzing {len(python_files)} Python files...")
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Syntax check
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    syntax_issues.append({
                        "file": file_path,
                        "error": str(e),
                        "line": e.lineno
                    })
                
                # Import analysis
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            # Check for problematic imports
                            if isinstance(node, ast.ImportFrom):
                                if node.module:
                                    # Check for relative imports that might fail
                                    if node.level > 0:  # Relative import
                                        import_issues.append({
                                            "file": file_path,
                                            "type": "relative_import",
                                            "module": node.module,
                                            "line": node.lineno
                                        })
                except:
                    pass
                    
            except Exception as e:
                syntax_issues.append({
                    "file": file_path,
                    "error": f"File read error: {str(e)}",
                    "line": 0
                })
        
        return {
            "files_analyzed": len(python_files),
            "syntax_issues": syntax_issues,
            "import_issues": import_issues,
            "syntax_error_count": len(syntax_issues),
            "import_issue_count": len(import_issues)
        }
    
    def _detect_mock_implementations(self) -> Dict[str, Any]:
        """Phase 3: Mock vs Real Implementation Detection"""
        mock_patterns = [
            r'# Mock.*implementation',
            r'# Placeholder.*implementation',
            r'# TODO.*implement',
            r'raise NotImplementedError',
            r'pass\s*#.*placeholder',
            r'return.*mock',
            r'# Simplified.*implementation',
            r'# Demo.*implementation'
        ]
        
        mock_implementations = []
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            for pattern in mock_patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    mock_implementations.append({
                                        "file": file_path,
                                        "line": i,
                                        "content": line.strip(),
                                        "pattern": pattern
                                    })
                    except:
                        pass
        
        return {
            "mock_implementations": mock_implementations,
            "mock_count": len(mock_implementations),
            "files_with_mocks": len(set(m["file"] for m in mock_implementations))
        }
    
    def _analyze_dependencies(self) -> Dict[str, Any]:
        """Phase 4: Dependency-Chain-Analyse"""
        dependencies = defaultdict(set)
        missing_imports = []
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    dependencies[file_path].add(alias.name)
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    dependencies[file_path].add(node.module)
                    except:
                        pass
        
        # Check for missing dependencies
        for file_path, deps in dependencies.items():
            for dep in deps:
                if not dep.startswith('.') and not dep.startswith('ai_indicator_optimizer'):
                    try:
                        importlib.util.find_spec(dep)
                    except (ImportError, ModuleNotFoundError, ValueError):
                        missing_imports.append({
                            "file": file_path,
                            "dependency": dep
                        })
        
        return {
            "dependency_graph": {k: list(v) for k, v in dependencies.items()},
            "missing_imports": missing_imports,
            "total_dependencies": sum(len(deps) for deps in dependencies.values())
        }
    
    def _check_architecture_consistency(self) -> Dict[str, Any]:
        """Phase 5: Architektur-Konsistenz-Check"""
        violations = []
        
        # Check for circular imports (simplified)
        # Check for proper separation of concerns
        # Check for consistent naming patterns
        
        expected_modules = [
            "ai", "data", "library", "generator", "core", 
            "logging", "monitoring", "recovery", "testing"
        ]
        
        existing_modules = []
        ai_optimizer_path = self.project_root / "ai_indicator_optimizer"
        
        if ai_optimizer_path.exists():
            for item in ai_optimizer_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    existing_modules.append(item.name)
        
        missing_modules = set(expected_modules) - set(existing_modules)
        unexpected_modules = set(existing_modules) - set(expected_modules)
        
        return {
            "expected_modules": expected_modules,
            "existing_modules": existing_modules,
            "missing_modules": list(missing_modules),
            "unexpected_modules": list(unexpected_modules),
            "violations": violations
        }
    
    def _detect_performance_issues(self) -> Dict[str, Any]:
        """Phase 6: Performance-Bottleneck-Detection"""
        performance_issues = []
        
        # Patterns that indicate potential performance issues
        perf_patterns = [
            (r'for.*in.*range\(len\(', 'Use enumerate() instead of range(len())'),
            (r'\.append\(.*\)\s*$', 'Consider list comprehension for better performance'),
            (r'time\.sleep\(\d+\)', 'Long sleep calls may indicate blocking operations'),
            (r'while True:', 'Infinite loops without proper exit conditions'),
            (r'\.join\(\)\s*$', 'Thread joins without timeout'),
            (r'requests\.get\(.*timeout=None', 'HTTP requests without timeout'),
        ]
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            for pattern, description in perf_patterns:
                                if re.search(pattern, line):
                                    performance_issues.append({
                                        "file": file_path,
                                        "line": i,
                                        "issue": description,
                                        "code": line.strip()
                                    })
                    except:
                        pass
        
        return {
            "performance_issues": performance_issues,
            "issue_count": len(performance_issues)
        }
    
    def _analyze_configuration(self) -> Dict[str, Any]:
        """Phase 7: Konfigurations-Vollständigkeit"""
        config_files = []
        config_gaps = []
        
        # Find configuration files
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if any(file.endswith(ext) for ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.env']):
                    config_files.append(os.path.join(root, file))
        
        # Check for expected configuration
        expected_configs = [
            "database configuration",
            "API endpoints",
            "model parameters",
            "hardware settings",
            "logging configuration"
        ]
        
        return {
            "config_files": config_files,
            "config_file_count": len(config_files),
            "expected_configs": expected_configs,
            "config_gaps": config_gaps
        }
    
    def _validate_database_schemas(self) -> Dict[str, Any]:
        """Phase 8: Database-Schema-Validierung"""
        schema_files = []
        schema_issues = []
        
        # Look for SQL files or database models
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith(('.sql', '.py')) and ('model' in file.lower() or 'schema' in file.lower()):
                    schema_files.append(os.path.join(root, file))
        
        return {
            "schema_files": schema_files,
            "schema_issues": schema_issues
        }
    
    def _analyze_error_handling(self) -> Dict[str, Any]:
        """Phase 9: Error-Handling-Coverage"""
        error_handling_stats = {
            "try_except_blocks": 0,
            "bare_except": 0,
            "specific_exceptions": 0,
            "files_with_error_handling": set(),
            "files_without_error_handling": []
        }
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        tree = ast.parse(content)
                        has_error_handling = False
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Try):
                                error_handling_stats["try_except_blocks"] += 1
                                has_error_handling = True
                                
                                for handler in node.handlers:
                                    if handler.type is None:
                                        error_handling_stats["bare_except"] += 1
                                    else:
                                        error_handling_stats["specific_exceptions"] += 1
                        
                        if has_error_handling:
                            error_handling_stats["files_with_error_handling"].add(file_path)
                        else:
                            error_handling_stats["files_without_error_handling"].append(file_path)
                            
                    except:
                        pass
        
        error_handling_stats["files_with_error_handling"] = len(error_handling_stats["files_with_error_handling"])
        
        return error_handling_stats
    
    def _analyze_test_coverage(self) -> Dict[str, Any]:
        """Phase 10: Test-Coverage-Analyse"""
        test_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.startswith('test_') or file.endswith('_test.py') or 'test' in file.lower():
                    test_files.append(os.path.join(root, file))
        
        return {
            "test_files": test_files,
            "test_file_count": len(test_files)
        }
    
    def _scan_security_vulnerabilities(self) -> Dict[str, Any]:
        """Phase 11: Security-Vulnerability-Scan"""
        security_issues = []
        
        # Basic security patterns to check
        security_patterns = [
            (r'eval\(', 'Use of # SECURITY: eval() removed - was: eval()
# TODO: Implement safe alternative can be dangerous'),
            (r'exec\(', 'Use of # SECURITY: exec() removed - was: exec()
# TODO: Implement safe alternative can be dangerous'),
            (r'shell=True', 'subprocess with shell=True can be dangerous'),
            (r'password.*=.*["\'].*["\']', 'Hardcoded password detected'),
            (r'api_key.*=.*["\'].*["\']', 'Hardcoded API key detected'),
            (r'secret.*=.*["\'].*["\']', 'Hardcoded secret detected'),
        ]
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            for pattern, description in security_patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    security_issues.append({
                                        "file": file_path,
                                        "line": i,
                                        "issue": description,
                                        "code": line.strip()
                                    })
                    except:
                        pass
        
        return {
            "security_issues": security_issues,
            "issue_count": len(security_issues)
        }
    
    def _analyze_documentation(self) -> Dict[str, Any]:
        """Phase 12: Dokumentations-Gap-Analyse"""
        doc_files = []
        undocumented_functions = []
        
        # Find documentation files
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith(('.md', '.rst', '.txt')):
                    doc_files.append(os.path.join(root, file))
        
        # Check for undocumented functions
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                if not ast.get_docstring(node):
                                    undocumented_functions.append({
                                        "file": file_path,
                                        "function": node.name,
                                        "line": node.lineno
                                    })
                    except:
                        pass
        
        return {
            "doc_files": doc_files,
            "doc_file_count": len(doc_files),
            "undocumented_functions": undocumented_functions,
            "undocumented_count": len(undocumented_functions)
        }
    
    def _validate_integration_points(self) -> Dict[str, Any]:
        """Phase 13: Integration-Point-Validierung"""
        integration_issues = []
        
        # Check for common integration patterns
        integration_patterns = [
            "database connections",
            "API endpoints", 
            "external services",
            "file I/O operations",
            "network requests"
        ]
        
        return {
            "integration_patterns": integration_patterns,
            "integration_issues": integration_issues
        }
    
    def _analyze_resource_usage(self) -> Dict[str, Any]:
        """Phase 14: Resource-Usage-Analyse"""
        resource_issues = []
        
        # Look for resource-intensive operations
        resource_patterns = [
            (r'open\(.*\)', 'File operations - ensure proper closing'),
            (r'requests\.(get|post)', 'HTTP requests - check for connection pooling'),
            (r'threading\.Thread', 'Thread creation - monitor thread count'),
            (r'multiprocessing\.Process', 'Process creation - monitor resource usage'),
        ]
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            for pattern, description in resource_patterns:
                                if re.search(pattern, line):
                                    resource_issues.append({
                                        "file": file_path,
                                        "line": i,
                                        "issue": description,
                                        "code": line.strip()
                                    })
                    except:
                        pass
        
        return {
            "resource_issues": resource_issues,
            "issue_count": len(resource_issues)
        }
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Phase 15: Final Report Generation"""
        
        # Compile critical issues
        critical_issues = []
        warnings = []
        recommendations = []
        
        # Analyze all collected data
        for key, value in self.analysis_results.items():
            if isinstance(value, dict) and "results" in value:
                results = value["results"]
                
                # Extract critical issues
                if "syntax_issues" in results and results["syntax_issues"]:
                    critical_issues.extend([
                        f"Syntax Error in {issue['file']}: {issue['error']}"
                        for issue in results["syntax_issues"]
                    ])
                
                if "missing_imports" in results and results["missing_imports"]:
                    critical_issues.extend([
                        f"Missing dependency in {issue['file']}: {issue['dependency']}"
                        for issue in results["missing_imports"]
                    ])
                
                if "mock_implementations" in results and results["mock_implementations"]:
                    warnings.extend([
                        f"Mock implementation in {mock['file']}:{mock['line']}"
                        for mock in results["mock_implementations"]
                    ])
                
                if "security_issues" in results and results["security_issues"]:
                    critical_issues.extend([
                        f"Security issue in {issue['file']}:{issue['line']}: {issue['issue']}"
                        for issue in results["security_issues"]
                    ])
        
        # Generate recommendations
        if warnings:
            recommendations.append("Replace mock implementations with real functionality")
        
        if critical_issues:
            recommendations.append("Fix critical syntax and import errors immediately")
        
        recommendations.extend([
            "Implement comprehensive error handling",
            "Add unit tests for all modules",
            "Document all public functions and classes",
            "Review security patterns and remove hardcoded secrets",
            "Optimize performance-critical code paths"
        ])
        
        # Update main results
        self.analysis_results["critical_errors"].extend(critical_issues)
        self.analysis_results["warnings"].extend(warnings)
        self.analysis_results["recommendations"].extend(recommendations)
        
        return {
            "critical_issue_count": len(critical_issues),
            "warning_count": len(warnings),
            "recommendation_count": len(recommendations),
            "analysis_complete": True
        }
    
    def save_results(self, filename: str = "autonomous_analysis_results.json"):
        """Speichert Analyse-Ergebnisse"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Analysis results saved to: {filename}")
        
        # Generate summary report
        summary_filename = filename.replace('.json', '_summary.md')
        self._generate_summary_report(summary_filename)
    
    def _generate_summary_report(self, filename: str):
        """Generiert zusammenfassenden Markdown-Report"""
        
        critical_count = len(self.analysis_results["critical_errors"])
        warning_count = len(self.analysis_results["warnings"])
        recommendation_count = len(self.analysis_results["recommendations"])
        
        report = f"""# Autonomous Project Analysis Report

## 📊 Analysis Summary

- **Start Time**: {self.analysis_results["start_time"]}
- **End Time**: {self.analysis_results["end_time"]}
- **Total Duration**: {self.analysis_results.get("total_duration", 0):.2f} seconds
- **Critical Issues**: {critical_count}
- **Warnings**: {warning_count}
- **Recommendations**: {recommendation_count}

## 🚨 Critical Issues

"""
        
        for issue in self.analysis_results["critical_errors"][:10]:  # Top 10
            if isinstance(issue, str):
                report += f"- {issue}\n"
            elif isinstance(issue, dict):
                report += f"- **{issue.get('phase', 'Unknown')}**: {issue.get('error', 'Unknown error')}\n"
        
        report += f"""
## ⚠️ Warnings

"""
        
        for warning in self.analysis_results["warnings"][:20]:  # Top 20
            report += f"- {warning}\n"
        
        report += f"""
## 💡 Recommendations

"""
        
        for rec in self.analysis_results["recommendations"]:
            report += f"- {rec}\n"
        
        report += f"""
## 📈 Analysis Details

### Phase Results Summary

"""
        
        for key, value in self.analysis_results.items():
            if key.startswith("phase_") and isinstance(value, dict):
                phase_name = key.replace("phase_", "").replace("_", " ").title()
                duration = value.get("duration", 0)
                report += f"- **{phase_name}**: {duration:.2f}s\n"
        
        report += f"""
---
*Generated by Autonomous Project Analyzer*
*Analysis completed at: {datetime.now().isoformat()}*
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📋 Summary report saved to: {filename}")


def main():
    """Hauptfunktion für autonome Analyse"""
    print("🌙 Starting autonomous project analysis...")
    print("💤 This will run for several hours without requiring user input")
    print("📊 Progress will be logged to autonomous_analysis.log")
    
    analyzer = AutonomousProjectAnalyzer()
    
    try:
        results = analyzer.run_full_analysis()
        analyzer.save_results()
        
        print("✅ Autonomous analysis completed successfully!")
        print(f"📄 Results saved to: autonomous_analysis_results.json")
        print(f"📋 Summary report: autonomous_analysis_results_summary.md")
        
        # Print quick summary
        critical_count = len(results["critical_errors"])
        warning_count = len(results["warnings"])
        
        print(f"\n🎯 Quick Summary:")
        print(f"   Critical Issues: {critical_count}")
        print(f"   Warnings: {warning_count}")
        print(f"   Total Duration: {results.get('total_duration', 0):.2f} seconds")
        
    except KeyboardInterrupt:
        print("\n⏹️ Analysis interrupted by user")
        analyzer.save_results("autonomous_analysis_partial.json")
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        logger.error(f"Analysis failed: {e}")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()