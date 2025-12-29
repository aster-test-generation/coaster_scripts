import os
from pathlib import Path
from langchain_openai import ChatOpenAI
import sys
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from cldk import CLDK
from cldk.analysis.java import JavaAnalysis
from hamster.code_analysis.common import CommonAnalysis
from is_integration_test import is_integration_test
from pattern_rating import rate_integration_test_pattern
import json
import subprocess

def process_project(project_path: str) -> list[dict]:
    cldk = CLDK(language="java")
    analysis: JavaAnalysis = cldk.analysis(project_path=project_path)
    common_analysis = CommonAnalysis(analysis=analysis)
    test_entities, app_classes = common_analysis.get_test_methods_classes_and_application_classes()

    results = []

    for test_class_name, test_methods in test_entities.items():
        java_file_name = analysis.get_java_file(test_class_name)
        class_file_path = Path(java_file_name).absolute().resolve()
        klass = analysis.get_class(test_class_name)
        code_body = class_file_path.read_text()

        # if not "ActivitiesIntegrationTest" in test_class_name:
        #     continue

        is_integration = is_integration_test(code_body).is_integration_test
        
        # print(f"Test Class: {test_class_name}")
        # print(f"  Is Integration Test? {is_integration}")
        # print()


        if not is_integration:
            # print(f"Test Class: {test_class_name}")
            # print("  Not an integration test.")
            # print()
            results.append({
                "test_class": test_class_name,
                "pattern": "Not an integration test"
            })
            continue
        
        # pattern_classification = classify_integration_test_pattern(code_body)

        # print(f"Test Class: {test_class_name}")
        # print(f"  Pattern Type: {pattern_classification.pattern_type}")
        # print(f"  Explanation: {pattern_classification.explanation}")
        # print()

        pattern_rating = rate_integration_test_pattern(code_body)

        # print(pattern_rating)

        if pattern_rating.manual_setup_in_tests:
            # print(f"Test Class: {test_class_name}")
            # print("  Manual setup in tests.")
            # print()
            results.append({
                "test_class": test_class_name,
                "pattern": "Manual setup in tests"
            })
        elif pattern_rating.has_restart:
            # print(f"Test Class: {test_class_name}")
            # print("  Restart")
            # print()
            results.append({
                "test_class": test_class_name,
                "pattern": "Restart"
            })
        elif pattern_rating.has_fixture and pattern_rating.reloading_data_in_fixtures:
            # print(f"Test Class: {test_class_name}")
            # print("  Clear and reload")
            # print()
            results.append({
                "test_class": test_class_name,
                "pattern": "Clear and reload"
            })
        elif pattern_rating.has_fixture and pattern_rating.API_calls_in_fixtures:
            # print(f"Test Class: {test_class_name}")
            # print("  API calls")
            # print()
            results.append({
                "test_class": test_class_name,
                "pattern": "API calls"
            })
        else:
            # print(f"Test Class: {test_class_name}")
            # print(f"  No recognized pattern: {pattern_rating}")
            # print()
            results.append({
                "test_class": test_class_name,
                "pattern": f"No recognized pattern: {{ {pattern_rating} }}"
            })
    
    return results


if __name__ == "__main__":
    repos_info_json = sys.argv[1]
    
    with open(repos_info_json, "r") as f:
        repos_info = json.load(f)
    
    # repo_results = {}

    for folder_name, details in repos_info.items():
        url = details['github_url']
        commit_hash = details['commit']

        folder_path=Path("./temp") / folder_name
        if not folder_path.exists():
            try:
                subprocess.check_call(["git", "clone", url, str(folder_path)])
            except subprocess.CalledProcessError:
                print(f"Failed to clone {url}. Skipping.")
                continue
        

        try:
            # We run the command INSIDE the new folder using the cwd argument
            subprocess.check_call(["git", "checkout", commit_hash], cwd=folder_path)
        except subprocess.CalledProcessError:
            print(f"Failed to checkout {commit_hash} in {folder_path}")

        
        # remove the cloned repo after processing
        pattern_results = process_project(str(folder_path))
        
        # write results to a json file
        with open(Path("./stats")/f"{folder_name}.json", "w") as f_out:
            json.dump(pattern_results, f_out, indent=4)

        subprocess.check_call(["rm", "-rf", str(folder_path)])
    
    
