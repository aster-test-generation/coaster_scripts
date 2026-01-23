import os
import sys
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from enum import Enum
from cldk import CLDK
from cldk.analysis.java import JavaAnalysis
from hamster.code_analysis.common import CommonAnalysis
import json

from is_integration_test import is_integration_test

class FitAssessment(str, Enum):
    PERFECT_FIT = "Perfect Fit"
    LOOSE_FIT = "Loose Fit"
    NO_FIT = "No Fit (New Pattern)"

class ConfidenceScore(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class IntegrationTestAnalysis(BaseModel):
    analysis_of_mechanism: str = Field(
        ..., 
        description="Describe specifically how this class ensures tests don't interfere with each other. Mention specific annotations or method calls."
    )
    fit_assessment: FitAssessment = Field(
        ...,
        description="Assessment of how well the code matches the known patterns."
    )
    pattern_name: str = Field(
        ...,
        description="The name of the known pattern identified, or the name of the new pattern proposed."
    )
    reasoning: str = Field(
        ...,
        description="Explanation of why it fits the known pattern, or why it requires a new definition."
    )
    confidence_score: ConfidenceScore = Field(
        ...,
        description="The confidence level of the classification."
    )

def classify_integration_test_pattern(file_content: str) -> IntegrationTestAnalysis:
    # api_key = os.getenv("OPENAI_API_KEY")
    api_key = os.getenv("OPENROUTER_API_KEY")


    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o",  # or "gpt-3.5-turbo"
        temperature=0.7,
        api_key=api_key
    ).with_structured_output(IntegrationTestAnalysis)


    system_rules = """
Role: You are an expert Software Test Architect researching strategies for "Self-Contained Integration Tests."

Context: We have identified 4 common patterns developers use to ensure integration tests are isolated (i.e., one test's data does not break another test). We are analyzing a dataset of tests to see if they fit these patterns or if developers are using strategies we haven't documented yet.

The Known Patterns (Reference):

1. Restart and Initialize: The application creates a fresh context (restarts) for every test class or method. Data is reset because the app boots up from scratch (e.g., in-memory DBs dropping on shutdown).

2. Clear and Reload: The application stays running (shared context). Test fixtures (e.g., @BeforeEach, @AfterEach) explicitly wipe the database (e.g., repository.deleteAll()) and reload baseline data.

3. Create via API: The application stays running. The test does not touch the DB directly. Instead, fixtures use HTTP API client calls to create the necessary resources before the test and delete them after.

4. Manually Create and Clean: No global fixtures or automated setups are used. The specific @Test method manually handles all data creation and cleanup logic inline.

Your Task:

1. Analyze the Code: Read the provided test class. specifically looking for how it manages state.

    Does the application context restart?

    Are there lifecycle methods (@Before, @After)? What do they do?

    Is there transaction management (e.g., @Transactional that rolls back)?

    Is data explicitly deleted, or does the test rely on unique IDs to avoid collisions?

2. Compare & Categorize: Compare your findings against the "Known Patterns."

3. Propose (if needed): If the strategy used in the code is not clearly described by the 4 patterns above, you must propose a new pattern.

    Note: Do not try to force the code into a category if it doesn't fit well. We are actively looking for new, undocumented patterns.


"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_rules),
        ("human", "Analyze this Java code:\n\n{code}")
    ])
    
    chain = prompt | llm

    result = chain.invoke({"code": file_content})

    return result

if __name__ == "__main__":
    '''
        # the file path is the first command line argument
        file_path = os.sys.argv[1]

        # Read the Java file content
        with open(file_path, 'r') as file:
            file_content = file.read()

        # Run the analysis
        classification = classify_integration_test_pattern(file_content)

        # The result is a real Python object, not just a string!
        print(f"Analysis of Mechanism: {classification.analysis_of_mechanism}")
        print(f"Fit Assessment: {classification.fit_assessment}")
        print(f"Pattern Name: {classification.pattern_name}")
        print(f"Reasoning: {classification.reasoning}")
        print(f"Confidence Score: {classification.confidence_score}")
    '''

    project_path = sys.argv[1]
    cldk = CLDK(language="java")
    analysis: JavaAnalysis = cldk.analysis(project_path=project_path)
    common_analysis = CommonAnalysis(analysis=analysis)
    test_entities, app_classes = common_analysis.get_test_methods_classes_and_application_classes()

    results = dict()

    for test_class_name, test_methods in test_entities.items():
        java_file_name = analysis.get_java_file(test_class_name)
        class_file_path = Path(java_file_name).absolute().resolve()
        klass = analysis.get_class(test_class_name)
        code_body = class_file_path.read_text()

        # if not "ActivitiesIntegrationTest" in test_class_name:
        #     continue

        is_integration = is_integration_test(code_body).is_integration_test

        if not is_integration:
            continue
        
        pattern_classification = classify_integration_test_pattern(code_body)

        results[test_class_name] =  pattern_classification.dict()
    
    # print the results as json
    print(json.dumps(results, indent=4))
        