from autogen_core import MessageContext, RoutedAgent, message_handler
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from messages import Message


class Agent(RoutedAgent):

    # Change this system message to reflect the unique characteristics of this agent

    system_message = """
    You are a creative entrepreneur. Your task is to come up with a new business idea using Agentic AI.
    Your personal interests are in these sectors: Healthcare, Education.
    You are drawn to ideas that involve disruption.
    You are less interested in ideas that are purely autonation.
    You should respond with your business ideas in an engaging and clear way.
    """



    def __init__(self, name) -> None:
        super().__init__(name)
        model_client = OpenAIChatCompletionClient(model="gpt-4o-mini", temperature=0.7)
        self._delegate = AssistantAgent(name, model_client=model_client, system_message=self.system_message)

    @message_handler
    async def handle_my_message_type(self, message: Message, ctx: MessageContext) -> Message:
        text_message = TextMessage(content=message.content, source="user")
        response = await self._delegate.on_messages([text_message], ctx.cancellation_token)
        return Message(content=response.chat_message.content)