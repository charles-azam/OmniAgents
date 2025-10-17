import asyncio
from pydantic_ai import Agent, AgentRunResultEvent, AgentStreamEvent

agent = Agent('openai:gpt-5-mini')

async def main():
    result = await agent.run('What is the capital of France?')
    print(result.output)
    #> The capital of France is Paris.

    events: list[AgentStreamEvent | AgentRunResultEvent] = []
    async for event in agent.run_stream_events('What is the capital of Mexico?'):
        events.append(event)
    print(events)

    
if __name__ == "__main__":
    asyncio.run(main())