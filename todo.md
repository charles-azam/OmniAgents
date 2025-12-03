Current todo: maintenant tout semble fonctionner, il faut vérifier que tout fonctionne ensemble et correctement, lancer le benchmark sur les agents pour comparer les performances sur un cas d'école, on peut écrire un article dessus, il va falloir aussi et surtout vérifier les tools. 

On va ensuite vouloir écrire un benchmark et essayer de comparer tout ce petit monde avec y compris claude code. 

il faut se reseigner aussi sur les benchmark agentic

Il faudra ensuite tester un agent plus complexe sur la base de https://github.com/langchain-ai/deepagents.git et lancer le même benchmark

OK I want you to look at the entire code and do the following refactor: I expect get_working_directory to return the working directory as seen by the LLM (so /workspace for the docker backend), I want the conversion to the actual directory to be made only in the backend. Out of the backend, every path should relative the the workding directory file. I also want you to prepare the next refactor where we will change the way LocalBackend works, the LLM will believe it works under /workspace wheras the real path will be a temporary path. Any path give to the tools that is not relative to the LLM should raise an error
reverse ingeneer claude code: https://github.com/bgauryy/open-docs/blob/main/docs/claude-agent-sdk/internal-flows.md