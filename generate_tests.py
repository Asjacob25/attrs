import subprocess
import requests
import os
import sys
import logging
import json
from pathlib import Path
from requests.exceptions import RequestException
from typing import List, Optional, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TestGenerator:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
        
        try:
            self.max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
        except ValueError:
            logging.error("Invalid value for OPENAI_MAX_TOKENS. Using default value: 2000")
            self.max_tokens = 2000

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

    def get_changed_files(self) -> List[str]:
        """Retrieve list of changed files passed as command-line arguments."""
        if len(sys.argv) <= 1:
            return []
        return [f.strip() for f in sys.argv[1].split() if f.strip()]

    def detect_language(self, file_name: str) -> str:
        """Detect programming language based on file extension."""
        extensions = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp':'C++',
            '.cs': 'C#',
            '.go':'Go'
        }
        _, ext = os.path.splitext(file_name)
        return extensions.get(ext.lower(), 'Unknown')

    def get_test_framework(self, language: str) -> str:
        """Get the appropriate test framework based on language."""
        frameworks = {
            'Python': 'pytest',
            'JavaScript': 'jest',
            'TypeScript': 'jest',
            'Java': 'JUnit',
            'C++': 'Google Test',
            'C#': 'NUnit',
            'Go':'testing'
        }
        return frameworks.get(language, 'unknown')
    
    def get_related_files(self, language: str, file_name: str) -> List[str]:
        """Identify related files based on import statements or includes."""
        related_files = []
        
        try:
            if (language=="Python" or language =='JavaScript' or language =='TypeScript'):
                with open(file_name, 'r') as f:
                    for line in f:
                        if 'import ' in line or 'from ' in line or 'require(' in line:
                            parts = line.split()
                            for part in parts:
                                if len(part) > 1 and part[0]=="." and part[1] != ".":
                                    path = part.replace(".","")
                                    for ext in ('.py', '.js', '.ts'):
                                        potential_file = f"{path}{ext}"
                                        if Path(potential_file).exists():
                                            related_files.append(potential_file)
                                            break
                                elif '.' in part:
                                    path = part.replace(".","/")
                                    for ext in ('.py', '.js', '.ts'):
                                        potential_file = f"{path}{ext}"
                                        if Path(potential_file).exists():
                                            related_files.append(potential_file)
                                            break
                                else:
                                    if part.endswith(('.py', '.js', '.ts')) and Path(part).exists():
                                        related_files.append(part)
                                    elif part.isidentifier():
                                        base_name = part.lower()
                                        for ext in ('.py', '.js', '.ts'):
                                            potential_file = f"{base_name}{ext}"
                                            if Path(potential_file).exists():
                                                related_files.append(potential_file)
                                                break
            elif language =='C++' or language =='C#':
                pass

        except Exception as e:
            logging.error(f"Error identifying related files in {file_name}: {e}")
        return related_files

    def get_related_test_files(self, language: str, file_name: str) -> List[str]:
        related_test_files = []
        
        try:
            if (language=="Python"):
                directory = Path(os.path.dirname(os.path.abspath(__file__)))
                test_files =  list(directory.rglob("tests.py")) + list(directory.rglob("test.py")) + list(directory.rglob("test_*.py")) + list(directory.rglob("*_test.py"))
                
                for file in test_files:
                    with open(file, 'r') as f:
                        for line in f:
                            if 'from ' in line:
                                parts = line.split()
                                for part in parts:
                                    if len(part) > 1 and part[0]=="." and part[1] != ".":
                                        path = part.replace(".","")
                                        for ext in ('.py', '.js', '.ts'):
                                            potential_file = f"{path}{ext}"
                                            stringPotentialFile = str(potential_file)
                                            if Path(file_name).exists() and (stringPotentialFile in str(file_name)):
                                                related_test_files.append(str(file))
                                                break
                                    elif '.' in part:
                                        path = part.replace(".","/")
                                        for ext in ('.py', '.js', '.ts'):
                                            potential_file = f"{path}{ext}"
                                            stringPotentialFile = str(potential_file)
                                            if Path(file_name).exists() and (stringPotentialFile in str(file_name)):
                                                related_test_files.append(str(file))
                                                break
                                    else:
                                        if part.endswith(('.py', '.js', '.ts')) and Path(part).exists() and ((str(file_name)) in str(part)):
                                            related_test_files.append(str(file))
                                        elif part.isidentifier():
                                            base_name = part.lower()
                                            for ext in ('.py', '.js', '.ts','.js'):
                                                potential_file = f"{base_name}{ext}"
                                                stringPotentialFile = str(potential_file)
                                                if Path(file_name).exists() and (stringPotentialFile in str(file_name)):
                                                    related_test_files.append(file)
                                                    break
        except Exception as e:
            logging.error(f"Error identifying related test files in {file_name}: {e}")
        
        limited_test_files = related_test_files[:1]
        return limited_test_files

    def generate_coverage_report(self, test_file: Path, language: str):
        report_file = test_file.parent / f"{test_file.stem}_coverage_report.txt"

        try:
            if language == "Python":
                subprocess.run(
                    ["coverage", "run", str(test_file)],
                    check=True
                )
                subprocess.run(
                    ["coverage", "report", "-m", "--omit=*/site-packages/*"],
                    stdout=open(report_file, "w"),
                    check=True
                )
            elif language == "JavaScript":
                subprocess.run(
                    ["jest", "--coverage", "--config=path/to/jest.config.js"],
                    stdout=open(report_file, "w"),
                    check=True
                )
            logging.info(f"Code coverage report saved to {report_file}")

        except subprocess.CalledProcessError as e:
            logging.error(f"Error generating coverage report for {test_file}: {e}")

    def ensure_coverage_installed(self, language: str):
        try:
            if language.lower() == 'python':
                subprocess.check_call([sys.executable, '-m', 'pip', 'show', 'coverage'])
                logging.info(f"Coverage tool for Python is already installed.")
            elif language.lower() == 'javascript':
                subprocess.check_call(['npm', 'list', 'jest'])
                logging.info(f"Coverage tool for JavaScript (jest) is already installed.")
            elif language.lower() == 'java':
                logging.info("Make sure Jacoco is configured in your Maven/Gradle build.")
            elif language.lower() == 'ruby':
                subprocess.check_call(['gem', 'list', 'simplecov'])
                logging.info(f"Coverage tool for Ruby (simplecov) is already installed.")
            else:
                logging.warning(f"Coverage tool check is not configured for {language}. Please add it manually.")
                return

        except subprocess.CalledProcessError:
            logging.error(f"Coverage tool for {language} is not installed. Installing...")

            try:
                if language.lower() == 'python':
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'coverage'])
                    logging.info(f"Coverage tool for Python has been installed.")
                elif language.lower() == 'javascript':
                    subprocess.check_call(['npm', 'install', 'jest'])
                    logging.info(f"Coverage tool for JavaScript (jest) has been installed.")
                elif language.lower() == 'ruby':
                    subprocess.check_call(['gem', 'install', 'simplecov'])
                    logging.info(f"Coverage tool for Ruby (simplecov) has been installed.")
                else:
                    logging.error(f"Could not install coverage tool for {language} automatically. Please install manually.")
            except subprocess.CalledProcessError:
                logging.error(f"Failed to install the coverage tool for {language}. Please install it manually.")

    def create_prompt(self, file_name: str, language: str) -> Optional[str]:
        try:
            with open(file_name, 'r') as f:
                code_content = f.read()
        except Exception as e:
            logging.error(f"Error reading file {file_name}: {e}")
            return None

        related_files = self.get_related_files(language, file_name)
        related_content = ""

        if related_files:
            logging.info(f"Related files for {file_name}: {related_files}")
        else:
            logging.info(f"No related files found for {file_name} to reference")
        
        for related_file in related_files:
            try:
                with open(related_file, 'r') as rf:
                    file_content = rf.read()
                    related_content += f"\n{related_file}:\n{file_content}"
            except Exception as e:
                logging.error(f"Error reading related file {related_file}: {e}")

        test_files = self.get_related_test_files(language, file_name)
        coverage_data = ""
        for test_file in test_files:
            test_path = Path(test_file)
            self.generate_coverage_report(test_path, language)
            report_file = test_path.parent / f"{test_path.stem}_coverage_report.txt"
            try:
                with open(report_file, 'r') as rf:
                    coverage_data += rf.read()
            except Exception as e:
                logging.error(f"Error reading coverage report {report_file}: {e}")

        framework = self.get_test_framework(language)
        prompt = (
            f"The following is a {language} file '{file_name}' that uses the {framework} testing framework:\n\n"
            f"{code_content}\n\n"
        )
        
        if related_content:
            prompt += f"\nRelated files:\n{related_content}\n\n"

        if coverage_data:
            prompt += f"\nCode coverage report:\n{coverage_data}\n\n"
        
        prompt += (
            f"Write test cases for the code above using {framework}. "
            f"Ensure that any uncovered lines in the coverage report are fully tested."
        )

        return prompt

    def call_openai_api(self, prompt: str) -> Optional[str]:
        """Call OpenAI API to generate tests based on a prompt."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': self.max_tokens,
            'temperature': 0.5
        }

        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            if result.get('choices'):
                normalized_text = result['choices'][0]['message']['content']
                if normalized_text.startswith('```'):
                    normalized_text = normalized_text[3:]
                if normalized_text.endswith('```'):
                    normalized_text = normalized_text[:-3]

                logging.info("Test cases generated successfully")
                return normalized_text
        except RequestException as e:
            logging.error(f"Error calling OpenAI API: {e}")
            return None

    def run_generation_workflow(self):
        changed_files = self.get_changed_files()
        if not changed_files:
            logging.warning("No changed files detected.")
            return

        for file_name in changed_files:
            language = self.detect_language(file_name)
            prompt = self.create_prompt(file_name, language)
            if not prompt:
                logging.warning(f"Skipping file {file_name} due to prompt generation issues.")
                continue

            generated_tests = self.call_openai_api(prompt)
            if generated_tests:
                output_path = Path(file_name).parent / f"{Path(file_name).stem}_test.{language.lower()}"
                with open(output_path, 'w') as f:
                    f.write(generated_tests)
                logging.info(f"Test cases for {file_name} saved to {output_path}")
            else:
                logging.error(f"Failed to generate tests for {file_name}")

def main():
    # Initialize the TestGenerator and run the generation workflow
    test_generator = TestGenerator()
    test_generator.run_generation_workflow()

if __name__ == '__main__':
    main()