import warnings

warnings.filterwarnings("ignore")

from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
import os
from classes import *
from prompts import *
from tools import *
from langchain.pydantic_v1 import Field
import inspect


load_dotenv()
x = 0
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)


def get_required_tools(state: AppState):

    prompt_template = PromptTemplate(
        input_variables=["user_request"], template=reqdToolsPromptTemplate
    )
    if "messages" not in state.keys():
        state["messages"] = []
    user_message = state["user_message"]

    prompt = prompt_template.format(user_request=user_message)
    state["messages"].append(HumanMessage(prompt))

    structured_llm = llm.with_structured_output(toolsReqd)

    parsed_data = dict(structured_llm.invoke(state["messages"]))

    reqdTools = []

    for tool in (parsed_data).keys():
        if parsed_data[tool] == "Required":
            reqdTools.append(tool)
    return {"reqdTools": reqdTools}


def call_tool_node(state: AppState):
    global x
    actions_dict = {}

    for tool in state["reqdTools"]:
        func_params = inspect.signature(tool_func_dict[tool]).parameters
        param_list = ""
        toolargs = {}
        for param in func_params.keys():
            toolargs[param] = Field(
                f"It is a parameter of function {tool}. Name of parameter is {param} and its datatype is {func_params[param].annotation}. Please return None if that required value of that parameter is missing in user query or context."
            )
            param_list += f"{param}: {func_params[param].annotation}"

        class ToolArgs:
            toolArgs = toolargs

        structured_llm = llm.with_structured_output(ToolArgs)
        prompt_template = PromptTemplate(
            input_variables=[
                "function_name",
                "function_use",
                "parameter_list",
                "user_request",
            ],
            template=toolCallPrompt,
        )
        prompt = prompt_template.format(
            function_name=tool,
            function_use=tool_func_dict[tool].__doc__,
            parameter_list=param_list,
            user_request=state["user_message"],
        )
        state["messages"].append(HumanMessage(prompt))
        output = structured_llm.invoke(state["messages"])
        print(output)
        for key, val in output.items():
            toolargs[key] = val
        missing_params = check_missing(output, tool)
        while len(missing_params):
            toolargs = {}
            ai_response = f"""
            The following parameters were found missing that is required to exectute this function named: {tool} please provide them:
            {missing_params}.\n You can use natural language or any format to give these values.
            """
            state["messages"].append(AIMessage(ai_response))
            print(ai_response)
            user_response = input()

            for param in missing_params:
                toolargs[param] = Field(
                    f"It is a parameter of function {tool}. Name of parameter is {param} and its datatype is {func_params[param].annotation}. Please return None if that required value of that parameter is missing in user query or context."
                )
                param_list += f"{param}: {func_params[param].annotation}"

            class ToolArgs:
                toolArgs = toolargs

            structured_llm = llm.with_structured_output(ToolArgs)
            prompt_template = PromptTemplate(
                input_variables=[
                    "function_name",
                    "function_use",
                    "parameter_list",
                    "user_response",
                ],
                template=missingToolCallPrompt,
            )
            prompt = prompt_template.format(
                function_name=tool,
                function_use=tool_func_dict[tool].__doc__,
                parameter_list=missing_params,
                user_response=user_response,
            )
            state["messages"].append(HumanMessage(prompt))
            output = structured_llm.invoke(state["messages"])
            print(output)
            missing_params = check_missing(output, tool)
            for key, val in output.items():
                toolargs[key] = val

        tool_output = tool_func_dict[tool](*toolargs.values())

        state["messages"].append(ToolMessage(content=tool_output, tool_call_id=x))
        actions_dict[tool] = tool_output

        x += 1
    return {"actions_summary": actions_dict}


def final_response_node(state: AppState):
    sys_message = SystemMessage(content=final_system_template)
    final_prompt_template = PromptTemplate(
        input_variables=["user_query", "actions_summary"], template=final_template
    )

    prompt = final_prompt_template.format(
        user_query=state["user_message"], actions_summary=str(state["actions_summary"])
    )

    output = llm.invoke([sys_message] + [HumanMessage(prompt)])
    state["messages"].append(output.content)
    return {"result": output.content}


graph = StateGraph(AppState)

graph.add_node("required_tools_extractor", get_required_tools)

graph.add_node("tool_caller", call_tool_node)

graph.add_node("final_response_node", final_response_node)

graph.set_entry_point("required_tools_extractor")

graph.add_edge("required_tools_extractor", "tool_caller")

graph.add_edge("tool_caller", "final_response_node")

graph.set_finish_point("final_response_node")

app = graph.compile()

os.system("clear")
print("Hello please enter your query: ")
while True:

    user_msg = input()

    state = app.invoke({"user_message": user_msg})

    print(f"Response of AI:\n {state['result']}")
