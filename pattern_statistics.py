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
from pattern_categorization import classify_integration_test_pattern

if __name__ == "__main__":
    # read the first command line argument as the project path
    project_path = sys.argv[1]
    cldk = CLDK(language="java")
    analysis: JavaAnalysis = cldk.analysis(project_path=project_path)
    common_analysis = CommonAnalysis(analysis=analysis)
    test_entities, app_classes = common_analysis.get_test_methods_classes_and_application_classes()

    for test_class_name, test_methods in test_entities.items():
        java_file_name = analysis.get_java_file(test_class_name)
        class_file_path = Path(java_file_name).absolute().resolve()
        klass = analysis.get_class(test_class_name)
        code_body = class_file_path.read_text()

        if not "ActivitiesIntegrationTest" in test_class_name:
            continue
        
        is_integration = is_integration_test(code_body).is_integration_test
        
        # print(f"Test Class: {test_class_name}")
        # print(f"  Is Integration Test? {is_integration}")
        # print()


        if not is_integration:
            print(f"Test Class: {test_class_name}")
            print("  Not an integration test.")
            continue
        
        pattern_classification = classify_integration_test_pattern(code_body)

        print(f"Test Class: {test_class_name}")
        print(f"  Pattern Type: {pattern_classification.pattern_type}")
        print(f"  Explanation: {pattern_classification.explanation}")
        print()
