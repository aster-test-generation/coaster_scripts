import sys
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import os



# 1. Define the Output Schema (Pydantic)
# This tells LangChain exactly what structure we want back.
class TestClassification(BaseModel):
    is_integration_test: bool = Field(
        description="True if the class is an integration test, False if it is a unit test."
    )
    reasoning: str = Field(
        description="A concise explanation citing specific annotations or logic found in the code."
    )

def is_integration_test(file_content: str) -> TestClassification:
    # api_key = os.getenv("OPENAI_API_KEY") 
    api_key = os.getenv("OPENROUTER_API_KEY") 

    # if the environment variable is not set, raise an error
    if not api_key:
        raise ValueError("API_KEY environment variable is not set.")
    
    # 2. Setup the Model
    # We use 'with_structured_output' to bind the Pydantic model to the LLM
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        model="gpt-4o",
        temperature=0.1,
        api_key=api_key
    ).with_structured_output(TestClassification)


    # 3. Create the Prompt Template
    # We use a template to separate instructions from the dynamic input
    system_rules = """
Role: You are an expert Java Test Architect.

Task: Analyze the provided Java test class and determine if it is a REST API Integration Test.

Definition: For the purpose of this analysis, a REST API Integration Test is defined as a test that verifies the behavior of the application by interacting with its HTTP Interface (Controllers/Endpoints).

It IS a REST API Integration Test if:
1. It sends requests using HTTP clients (e.g., TestRestTemplate, WebTestClient, RestAssured, HttpClient).
2. It uses mock HTTP dispatchers (e.g., Spring's MockMvc) to simulate HTTP requests against the controller layer.
3. It asserts on HTTP concepts (Status Codes like 200/404, JSON bodies, Headers).

It is NOT a REST API Integration Test if:
1. It tests Service, Repository, or Utility classes by directly calling their Java methods (e.g., userService.createUser()).
2. It only mocks dependencies using Mockito without any HTTP layer interaction.
3. It is a UI test (Selenium, Playwright) interacting with a browser DOM rather than raw API endpoints.

Analysis Steps:
1. Check Class Name (Naming Heuristics): Look for common naming conventions that hint at integration testing, such as classes ending in IT (e.g., UserIT), IntegrationTest, or classes starting/ending with ApiTest or ControllerTest. 
2. Check Imports: Look for libraries like org.springframework.test.web.servlet (MockMvc), io.restassured, org.springframework.boot.test.web.client.
3. Check Annotations: Look for @SpringBootTest(webEnvironment = ...), @WebMvcTest, @AutoConfigureMockMvc.
4. Check Method Body: Do the tests perform actions like .perform(get(...)), .getForEntity(...), or given().when().get(...)?s
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_rules),
        ("human", "Analyze this Java code:\n\n{code}")
    ])

    # 4. Create the Chain and Invoke
    # Chain: Prompt -> LLM -> Pydantic Object
    chain = prompt | llm
    
    result = chain.invoke({"code": file_content})
    
    return result

# --- Usage Example ---
if __name__ == "__main__":
    # the file path is the first command line argument
    file_path = sys.argv[1]

    # Read the Java file content
    with open(file_path, 'r') as file:
        file_content = file.read()

    # Run the analysis
    classification = is_integration_test(file_content)

    # The result is a real Python object, not just a string!
    print(f"Is Integration Test? {classification.is_integration_test}")
    print(f"Reasoning: {classification.reasoning}")
    