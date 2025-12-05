Current todo: maintenant tout semble fonctionner, il faut vérifier que tout fonctionne ensemble et correctement, lancer le benchmark sur les agents pour comparer les performances sur un cas d'école, on peut écrire un article dessus, il va falloir aussi et surtout vérifier les tools. 

On va ensuite vouloir écrire un benchmark et essayer de comparer tout ce petit monde avec y compris claude code. 

il faut se reseigner aussi sur les benchmark agentic

Il faudra ensuite tester un agent plus complexe sur la base de https://github.com/langchain-ai/deepagents.git et lancer le même benchmark

OK I want you to look at the entire code and do the following refactor: I expect get_working_directory to return the working directory as seen by the LLM (so /workspace for the docker backend), I want the conversion to the actual directory to be made only in the backend. Out of the backend, every path should relative the the workding directory file. I also want you to prepare the next refactor where we will change the way LocalBackend works, the LLM will believe it works under /workspace wheras the real path will be a temporary path. Any path give to the tools that is not relative to the LLM should raise an error
reverse ingeneer claude code: https://github.com/bgauryy/open-docs/blob/main/docs/claude-agent-sdk/internal-flows.md


look at the code, the objective of this library is to be able to write coding agent that function with every framework (smolagents, pydantic ai, langchain, ect...) and that can code either locally, in a docker or in a remote e2b vm. What I don't like about this code is that there seem to be hardcoded that it generates a python code using UV. Why ? Because in the tools, there are python only tools (a uv tool) '/Users/charlesazam/charloupioupiou/prompttodraft/src/prompttodraft/tools/uv_tool.py'. Also, at initialisation, we call initialize_project '/Users/charlesazam/charloupioupiou/prompttodraft/src/prompttodraft/utils.py' which is made for python. Here you can get an example of the current API '/Users/charlesazam/cha rloupioupiou/prompttodraft/src/prompttodraft/agents/langchain_example.py' '/Users/charl esazam/charloupioupiou/prompttodraft/src/prompttodraft/agents/langchain_agent.py'. What I want you to do is to think very long and carefully and to suggest a change in the API so that it gets crystal clear on how we can create an agent for another programming language or with just a different initialisation, both for the files at initialisation but also with special tools. Also, in your reflection, you must also think of the current API (choosing a state manager, a backend, a framework) and how we can improve this so that in the end it gets super intuitive to create the agent we need.

Also keep in mind that might want to add an option to a specific docker image, meaning that the user must be able to provide this options, which is linked to the initialisation but must be accessible to the backend (keep that in mind). Also, it is not clear for me to the user that he needs to pick the runtime (or another name), the state_manager and the backend, so I would like the user to provide all those things to the same function or object with a clear string explaining all this

ok I like it more but I like when the typing is clear,  I want everything to be typed using the objects in this repo. Also, 
what about the fact that he might want to use a CoreBackendTool and convert them 
using the converters, OR, he might want to define directly tools in the framework's 
API (let say langchain) and give them directly to LangchainAgent. He might also very
like our idea with coding tools and a backend and a initialiser but he wants to 
write it's own agent, for instance with langchain using a customized loop. 