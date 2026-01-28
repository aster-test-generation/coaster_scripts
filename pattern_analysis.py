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
    is_self_contained: bool = Field(
        ...,
        description="True if the test manages its own state and does not depend on execution order or pre-existing data. False otherwise."
    )
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

Context: We have identified 4 common patterns developers use to ensure integration tests are self-contained (i.e., one test's data does not break another test). We are analyzing a dataset of tests to see if they fit these patterns or if developers are using strategies we haven't documented yet. We first need to confirm if the test is actually self-contained (i.e., it can run reliably regardless of previous test executions and leaves the system clean). If it is, we want to classify how it achieves that.

The Known Patterns (Reference):

1. Restart and Initialize
Description: The application undergoes a startup/shutdown cycle for every test class or method to ensure a clean state. Data reloading is a side effect of the app startup (e.g., Hibernate hbm2ddl.auto=create).
Key Indicators: Annotations like @DirtiesContext, @WebIntegrationTest, or logics in the fixtures ensuring a fresh context per test class.
Differentiation: Even if data is reloaded, if the application restarts, it is Pattern 1, not Pattern 2.

2. Clear and Reload (Fixture-based DB Manipulation)
Description: The application instance is reused (shared context). Persistent data (Database) is wiped and re-populated using test fixtures.
Key Indicators: Presence of test fixtures (@BeforeEach, @Before, etc.) that call SQL scripts, repositories, or DB cleaners (e.g., flyway.clean(), repository.deleteAll()).
Differentiation: The application context must remain active (no restart). The manipulation is direct against the DB/Storage in the fixtures, not via external API calls. If there is no fixture, it is Pattern 4.

3. Create via API Calls (Fixture-based API Manipulation)
Description: The application instance is reused. Fixtures are used. The test does not touch the DB directly. Instead, in the test fixtures, it uses an HTTP Client to send API requests to set up the required state before the test logic runs.
Key Indicators: Fixtures (@BeforeEach, @Before, etc.) containing HTTP requests (e.g., client.post("/users", ...)).
Differentiation: Setup occurs in the fixtures, not the test method. It uses API endpoints, not direct DB access. If there is no fixture, it is Pattern 4.

4. Manually Create and Clean (Inline Logic)
Description: The test relies on neither external fixtures nor app restarts. All data setup and teardown logic is hardcoded inside the specific @Test method.
Key Indicators: The @Test method contains data setup logic (creating data). No @Before/@After methods are used for data state.
Differentiation: Applies even if the inline logic uses API calls or DB calls. If it is inside the fixture, it is Pattern 4.

5. Not Self-Contained: The test relies on pre-existing data (that it didn't create), depends on the execution order of other tests, or fails to clean up data that might impact subsequent tests.

Your Task:

1. Determine Self-Containment:

    Does the test assume data already exists in the DB (without creating it)?

    Does it use @TestMethodOrder or similar annotations suggesting order dependency?

    Does it lack any cleanup logic (no transaction rollback, no deletes, no restarts)?

    If any of these are true, classify as "Not Self-Contained".

2. Analyze the Code: Read the provided test class. specifically looking for how it manages state.

    Does the application context restart?

    Are there test fixture methods (@Before, @After)? What do they do?

    Is there transaction management (e.g., @Transactional that rolls back)?

    Is data explicitly deleted, or does the test rely on unique IDs to avoid collisions?

3. Compare & Categorize: Compare your findings against the "Known Patterns."

4. Propose (if needed): If the strategy used in the code is not clearly described by the 4 patterns above, you must propose a new pattern.

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
        