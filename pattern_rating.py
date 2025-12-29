import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

class IntergrationPatternRating(BaseModel):
    has_restart: bool = Field(
        description="True if the test class uses application restart between tests, False otherwise."
    )
    has_fixture: bool = Field(
        description="True if the test class uses fixtures (@Before, @After, or equivalents) for data setup/teardown, False otherwise."
    )
    reloading_data_in_fixtures: bool = Field(
        description="True if the test class uses fixtures and the test class reloads data in fixtures, False otherwise."
    )
    API_calls_in_fixtures: bool = Field(
        description="True if the test class uses fixtures and the test class makes API calls in fixtures, False otherwise."
    )
    manual_setup_in_tests: bool = Field(
        description="True if the test class uses no fixtures and has manual setup/teardown logic inside @Test methods, False otherwise."
    )

def rate_integration_test_pattern(file_content: str) -> IntergrationPatternRating:
    api_key = os.getenv("OPENAI_API_KEY")    
    
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        api_key=api_key
    ).with_structured_output(IntergrationPatternRating)


    system_rules = """
Role: You are an expert Software Test Architect specializing in Java REST API integration testing strategies.

Task: Analyze the provided Java test class code and rate it on the following aspects related to integration test patterns.

The Aspects to Rate:
1. Application Restart:
   - Does the test class start up the app in fixtures (@Before, @BeforeAll, @After, @AfterAll or similar)?
   - Does the test class use application restart between tests? (e.g., via @DirtiesContext, @WebIntegrationTest, or similar)
2. Use of Fixtures:
   - Does the test class use fixtures (@Before, @After, or equivalents) for data setup/teardown?
3. Data Reloading in Fixtures:
   - If fixtures are used, does the test class directly clear and/or reload the DB or persistent data in these fixtures (e.g., executing SQL scripts, calling repository methods)?
4. API Calls in Fixtures:
   - If fixtures are used, does the test class make API calls to set up data in these fixtures?
5. Manual Setup in Tests:
   - Does the test class have manual setup/teardown logic inside @Test methods?
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_rules),
        ("human", "Analyze this Java code:\n\n{code}")
    ])

    chain = prompt | llm

    result = chain.invoke({"code": file_content})

    return result

if __name__ == "__main__":
    file_path = os.sys.argv[1]

    with open(file_path, 'r') as file:
        java_code = file.read()
    
    rating = rate_integration_test_pattern(java_code)

    print(f"Has Application Restart: {rating.has_restart}")
    print(f"Uses Fixtures: {rating.has_fixture}")
    print(f"Reloads Data in Fixtures: {rating.reloading_data_in_fixtures}")
    print(f"Makes API Calls in Fixtures: {rating.API_calls_in_fixtures}")
    print(f"Manual Setup in Tests: {rating.manual_setup_in_tests}")