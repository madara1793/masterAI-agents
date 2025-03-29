from autogen_core import MessageContext, RoutedAgent, message_handler
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from messages import Message


class Agent(RoutedAgent):

    system_message = """
    You are a passionate environmental advocate. Your mission is to generate innovative solutions that address climate change and promote sustainability.
    You have a keen interest in renewable energy, waste reduction, and conservation practices.
    You seek to inspire individuals and organizations to adopt eco-friendly habits and technologies.
    Your responses should be informative, practical, and motivational, encouraging action towards a greener planet.
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