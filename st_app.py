import streamlit as st
import textwrap

import warnings

warnings.filterwarnings("ignore")

from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage
import os
from classes import *
from prompts import *
from tools import *
from langchain.pydantic_v1 import Field
import inspect
from agentipy import SolanaAgentKit
import asyncio

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
load_dotenv(override=True)
solana_agent = SolanaAgentKit(
    private_key=os.getenv("SOL_PRIVATE_KEY"),
    rpc_url="https://api.devnet.solana.com",
)
# print(os.getenv("GROQ_API_KEY2"))
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

    print(f"\nRequired tools are: {reqdTools}\n")
    return {"reqdTools": reqdTools}


def call_tool_node(state: AppState):
    global x
    actions_dict = {}

    for tool in state["reqdTools"]:
        func_params = inspect.signature(tool_func_dict[tool]).parameters
        param_list = ""
        toolargs = {}
        for param in func_params.keys():
            if param == "solana_agent":
                continue
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
        print(f"\nExtracted tool args for tool {tool}: {output}\n")
        toolargs = {}
        for key, val in output.items():
            if val != "None":
                print("obj: ", key, val)
                toolargs[key] = val
        missing_params = check_missing(output, tool)

        print(toolargs)

        if len(missing_params):
            output_content = f"We cannot call this {tool} tool. Since some of the parameters were missing and cannot be parsed. list of mission params={missing_params}. Please re enter them in next message."
        else:
            toolargs["solana_agent"] = solana_agent
            print(toolargs)
            # output_generator = tool_func_dict[tool](**toolargs)
            try:
                task = loop.create_task(tool_func_dict[tool](**toolargs))  # Create task
                output = loop.run_until_complete(task)  # Run until the task completes
                output_content = f"Output for call of {tool} tool: {output}"

            except Exception as e:
                output_content = (
                    f"Some error occured while calling {tool} tool. Error message: {e}"
                )

        print(output_content)

        state["messages"].append(
            ToolMessage(
                content=output_content,
                tool_call_id=x,
            )
        )
        actions_dict[tool] = output_content

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

    structured_llm = llm.with_structured_output(FinalReport)

    output = structured_llm.invoke(
        state["messages"] + [sys_message] + [HumanMessage(prompt)]
    )
    state["messages"].append(AIMessage(str(dict(output))))

    return {"result": output, "final_report": output}


graph = StateGraph(AppState)

graph.add_node("required_tools_extractor", get_required_tools)

graph.add_node("tool_caller", call_tool_node)

graph.add_node("final_response_node", final_response_node)

graph.set_entry_point("required_tools_extractor")

graph.add_edge("required_tools_extractor", "tool_caller")

graph.add_edge("tool_caller", "final_response_node")

graph.set_finish_point("final_response_node")

app = graph.compile()

graph_app = graph.compile()
png_graph = graph_app.get_graph().draw_mermaid_png()

state = AppState()

st.title("AI Agent for Solana ToolKit")

# st.subheader("Enter Your Prompt")
user_query = st.text_input("Enter Your Prompt")

# Process Query Button
if st.button("Get Response"):
    if user_query:
        state["user_message"] = user_query

        try:
            state = app.invoke(state)
            with st.expander("⚙️ Actions Performed (Click to expand)"):
                action_report = state["final_report"].actionAnalysis
                for line in action_report.split("\n"):
                    st.write(textwrap.fill(line, 80))

            st.subheader("📢 Response")
            final_response = state["final_report"].finalResponse
            for line in final_response.split("\n"):
                st.write(textwrap.fill(line, 80))
        except Exception as e:
            template = PromptTemplate(
                input_variables=["ERROR_MESSAGE"], template=error_handler_template
            )
            prompt = template.format(ERROR_MESSAGE=repr(e))

            output = llm.invoke(prompt)
            final_response = output.content
            for line in final_response.split("\n"):
                st.write(textwrap.fill(line, 80))

    else:
        st.error("Please enter a query.")


# Footer
st.markdown("---")
st.markdown("Developed by Prakhar Shukla with ❤️")
