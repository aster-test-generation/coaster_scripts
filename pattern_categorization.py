import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

class IntegrationPatternClassification(BaseModel):
    pattern_type: str = Field(
        description="The type of pattern used for implementing self-contained integration tests. One of: 'Restart and initialize persistent state', 'Clear and reload', 'Create via API calls', 'Manually create and clean', or 'Not enough information to decide'."
    )
    explanation: str = Field(
        description="A detailed explanation of why this pattern was chosen, citing specific annotations, methods, or logic found in the code."
    )

def classify_integration_test_pattern(file_content: str) -> IntegrationPatternClassification:
    api_key = "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" 


    llm = ChatOpenAI(
        model="gpt-4o",  # or "gpt-3.5-turbo"
        temperature=0.7,
        api_key=api_key
    ).with_structured_output(IntegrationPatternClassification)


    system_rules = """
Role: You are an expert Software Test Architect specializing in Java REST API integration testing strategies.

Task: Analyze the provided Java test class code and classify it into one of the 4 Integration Test Patterns defined below.

Decision Logic (Order of Precedence):
1. Check for Application Restart: If the application restarts between tests (Pattern 1), select Pattern 1 regardless of how data is loaded.
   - Do they start up the app in fixture (@Before, @BeforeAll, @After, @AfterAll or equivalent) methods? -> Pattern 1.
   - Do they restart the app using annotations like @DirtiesContext, @WebIntegrationTest, or similar? -> Pattern 1.
2. Check Test Method Logic: If no fixtures (@Before, @BeforeAll, @After, @AfterAll or equivalents) are used for data setup, check the @Test methods.
   - Do the test methods manually handle setup/teardown? -> Pattern 4.
3. Check Fixture Logic: If the application does not restart, check the @Before/@After (or equivalent) methods.
   - Do they directly wipe/load the DB? -> Pattern 2.
   - Do they make HTTP API calls to create state? -> Pattern 3.

The Patterns:

1. Restart and Initialize (App Lifecycle)
Description: The application undergoes a startup/shutdown cycle for every test class or method to ensure a clean state. Data reloading is a side effect of the app startup (e.g., Hibernate hbm2ddl.auto=create).
Key Indicators: Annotations like @DirtiesContext, @WebIntegrationTest, or logics in the fixtures ensuring a fresh context per test.
Differentiation: Even if data is reloaded, if the application restarts, it is Pattern 1, not Pattern 2.

2. Clear and Reload (Fixture-based DB Manipulation)
Description: The application instance is reused (shared context). Persistent data (Database) is wiped and re-populated using test fixtures.
Key Indicators: Presence of lifecycle methods (@BeforeEach, @AfterEach, setUp) that call SQL scripts, repositories, or DB cleaners (e.g., flyway.clean(), repository.deleteAll()).
Differentiation: The application context must remain active (no restart). The manipulation is direct against the DB/Storage, not via external API calls.

3. Create via API Calls (Fixture-based API Manipulation)
Description: The application instance is reused. The test does not touch the DB directly. Instead, it uses an HTTP Client to send API requests to set up the required state before the test logic runs.
Key Indicators: Lifecycle methods (@BeforeEach, setUp) containing HTTP requests (e.g., client.post("/users", ...)).
Differentiation: Setup occurs in the fixtures, not the test method. It uses API endpoints, not direct DB access.

4. Manually Create and Clean (Inline Logic)
Description: The test relies on neither external fixtures nor app restarts. All data setup and teardown logic is hardcoded inside the specific @Test method.
Key Indicators: The @Test method is long and contains "Arrange" logic (creating data) immediately followed by "Act" and "Assert". No @Before/@After methods are used for data state.
Differentiation: Applies even if the inline logic uses API calls or DB calls. If it is inside the @Test method, it is Pattern 4.

Instructions for Output:

1. Analyze the imports, class annotations, lifecycle methods, and test methods.
2. Classify the pattern.
3. Explain your reasoning, citing specific lines of code or annotations.
4. Exceptions:
   - If the class is abstract or inherits setup logic from a parent class not provided in the context, output: "Not enough information to decide" and list what is missing.
   - If the strategy fits none of the above, classify as "New Pattern" and describe it.
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_rules),
        ("human", "Analyze this Java code:\n\n{code}")
    ])
    
    chain = prompt | llm

    result = chain.invoke({"code": file_content})

    return result

if __name__ == "__main__":
    # the file path is the first command line argument
    file_path = os.sys.argv[1]

    # Read the Java file content
    with open(file_path, 'r') as file:
        file_content = file.read()

    # Run the analysis
    classification = classify_integration_test_pattern(file_content)

    # The result is a real Python object, not just a string!
    print(f"Pattern Type: {classification.pattern_type}")
    print(f"Explanation: {classification.explanation}")