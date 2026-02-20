# SheetMind Agent Upgrade Plan

## Overview
Transform SheetMind from a "plan-execute" pattern to a true **ReAct Agent** with tool calling, memory, and self-correction.

---

## Phase 1: LangChain Foundation

### 1.1 Install Dependencies
```bash
pip install langchain langchain-google-genai langchain-openai langgraph
```

### 1.2 Define Tools (Replace JSON Actions)
```python
from langchain.tools import tool

@tool
def create_sheet(name: str) -> str:
    """Create a new Google Sheet with the given name."""
    # Call GAS via frontend bridge or Google Sheets API directly
    return f"Created sheet '{name}'"

@tool
def set_formula(sheet: str, cell: str, formula: str) -> str:
    """Set a formula in a specific cell."""
    return f"Set {cell} = {formula}"

@tool
def read_range(sheet: str, range: str) -> list:
    """Read values from a range to verify results."""
    return [["Major", "Total"], ["CS", 1500], ["EE", 1200]]

@tool
def filter_data(column: str, criteria: str) -> str:
    """Apply a filter to the sheet."""
    return f"Filtered {column} where {criteria}"
```

### 1.3 Create ReAct Agent
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

tools = [create_sheet, set_formula, read_range, filter_data]

agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=REACT_PROMPT  # Includes sheet context
)

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=10,  # Prevent infinite loops
    handle_parsing_errors=True,
)
```

### Benefits of Phase 1:
- ✅ AI calls tools directly (no JSON parsing)
- ✅ Automatic retries on errors
- ✅ Observation loop (sees tool results)
- ✅ Natural multi-step reasoning

---

## Phase 2: Memory Systems

### 2.1 Conversation Memory
```python
from langchain.memory import ConversationBufferWindowMemory

memory = ConversationBufferWindowMemory(
    k=10,  # Last 10 exchanges
    return_messages=True,
    memory_key="chat_history"
)
```

### 2.2 Entity Memory (Remembers Schema)
```python
from langchain.memory import ConversationEntityMemory

entity_memory = ConversationEntityMemory(llm=llm)
# Remembers: "Column A is Name", "Sheet1 has 500 rows", etc.
```

### 2.3 Long-term Memory with Vector Store
```python
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

embeddings = GoogleGenerativeAIEmbeddings(model="embedding-001")
vectorstore = Chroma(embedding_function=embeddings, persist_directory="./memory")

# Store past successful queries
vectorstore.add_texts([
    "User asked for sales by region, created pivot with SUMIF",
    "User asked for duplicates, used COUNTIF > 1 formula",
])

# Retrieve similar past solutions
relevant_memories = vectorstore.similarity_search("sum by category", k=3)
```

### Benefits of Phase 2:
- ✅ Remembers user preferences
- ✅ Learns from past successful queries
- ✅ Understands sheet schema over time
- ✅ "Do it like last time" works

---

## Phase 3: RAG for Large Sheets

### Problem
Currently sends 200 rows to AI blindly. For 10,000 row sheets, this fails.

### Solution: Semantic Search on Sheet Data
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

def index_sheet_data(cells: dict):
    """Index sheet data for semantic retrieval."""
    # Convert cells to documents
    docs = []
    for cell, value in cells.items():
        docs.append(f"{cell}: {value}")

    # Create embeddings
    vectorstore = Chroma.from_texts(docs, embeddings)
    return vectorstore

def get_relevant_rows(query: str, vectorstore, k=50):
    """Retrieve only relevant rows for the query."""
    results = vectorstore.similarity_search(query, k=k)
    return results
```

### Query Flow
```
User: "Find all CS majors with GPA > 3.5"
       ↓
RAG: Retrieve rows where Major contains "CS" (semantic search)
       ↓
AI: Gets only 50 relevant rows instead of 10,000
       ↓
Result: Accurate, fast, token-efficient
```

### Benefits of Phase 3:
- ✅ Handle 10,000+ row sheets
- ✅ Faster responses (less tokens)
- ✅ More accurate (focused context)
- ✅ Lower API costs

---

## Phase 4: LangGraph for Complex Workflows

### When to Use
- Multi-step analysis with branching
- Conditional logic (if error → try alternative)
- Human-in-the-loop approval

### Example: Self-Correcting Agent
```python
from langgraph.graph import StateGraph, END

def plan_step(state):
    """AI creates execution plan."""
    plan = llm.invoke("Create a plan for: " + state["query"])
    return {"plan": plan}

def execute_step(state):
    """Execute each action in the plan."""
    results = []
    for action in state["plan"]:
        result = execute_tool(action)
        results.append(result)
    return {"results": results}

def verify_step(state):
    """Read back and verify results."""
    verification = read_range(state["target_sheet"], "A1:Z100")
    return {"verification": verification}

def should_retry(state):
    """Check if results are correct."""
    if "error" in state["verification"]:
        return "retry"
    return "complete"

# Build graph
workflow = StateGraph()
workflow.add_node("plan", plan_step)
workflow.add_node("execute", execute_step)
workflow.add_node("verify", verify_step)

workflow.add_edge("plan", "execute")
workflow.add_edge("execute", "verify")
workflow.add_conditional_edges("verify", should_retry, {
    "retry": "plan",      # Re-plan if failed
    "complete": END
})

agent = workflow.compile()
```

### Benefits of Phase 4:
- ✅ Self-correction on errors
- ✅ Complex conditional workflows
- ✅ Visual debugging (graph view)
- ✅ Human approval gates

---

## Phase 5: Multi-Agent with CrewAI (Optional)

### When to Use
- Complex analysis needing different perspectives
- Quality assurance (one agent checks another)

### Example Crew
```python
from crewai import Agent, Task, Crew

analyst = Agent(
    role="Data Analyst",
    goal="Analyze spreadsheet data and create formulas",
    tools=[create_sheet, set_formula, read_range]
)

reviewer = Agent(
    role="QA Reviewer",
    goal="Verify formulas are correct and results make sense",
    tools=[read_range]
)

task1 = Task(
    description="Create a summary of sales by region",
    agent=analyst
)

task2 = Task(
    description="Verify the summary is accurate",
    agent=reviewer
)

crew = Crew(agents=[analyst, reviewer], tasks=[task1, task2])
result = crew.kickoff()
```

### Benefits of Phase 5:
- ✅ Quality assurance built-in
- ✅ Specialized agents for different tasks
- ✅ Collaborative problem solving

---

## Implementation Priority

| Phase | Effort | Impact | Priority |
|-------|--------|--------|----------|
| Phase 1: LangChain Tools | 2 days | High | 🔴 Do First |
| Phase 2: Memory | 1 day | Medium | 🟡 Second |
| Phase 3: RAG | 2 days | High (large sheets) | 🟡 Second |
| Phase 4: LangGraph | 2 days | Medium | 🟢 Later |
| Phase 5: CrewAI | 3 days | Low (overkill) | ⚪ Optional |

---

## Recommended Stack

```
┌─────────────────────────────────────────┐
│           SheetMind v2                   │
├─────────────────────────────────────────┤
│  Frontend: React + Google Apps Script   │
├─────────────────────────────────────────┤
│  Agent: LangChain ReAct + LangGraph     │
├─────────────────────────────────────────┤
│  Memory: Chroma Vector DB               │
├─────────────────────────────────────────┤
│  LLM: Gemini 2.0 Flash (direct API)     │
├─────────────────────────────────────────┤
│  Tools: Native Google Sheets API        │
└─────────────────────────────────────────┘
```

---

## Quick Win: Enable Native Tool Calling (No Framework)

If you don't want to add LangChain, Gemini supports native function calling:

```python
import google.generativeai as genai

tools = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="create_sheet",
                description="Create a new sheet",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "name": genai.protos.Schema(type=genai.protos.Type.STRING)
                    }
                )
            )
        ]
    )
]

model = genai.GenerativeModel("gemini-2.0-flash", tools=tools)
response = model.generate_content("Create a summary sheet")

# AI returns function call, not text
if response.candidates[0].content.parts[0].function_call:
    func = response.candidates[0].content.parts[0].function_call
    # Execute: create_sheet(name=func.args["name"])
```

This gives you tool calling without any framework dependency.

---

## Decision

Choose your path:

1. **Minimal Change**: Native Gemini function calling (1 day)
2. **Recommended**: LangChain + Memory (3-4 days)
3. **Full Power**: LangChain + LangGraph + RAG (1 week)
4. **Enterprise**: Add CrewAI multi-agent (2 weeks)
