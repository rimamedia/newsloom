Agents
======

Agents are LLM-powered components that process news content in Newsloom. Each agent represents a configured instance of a language model that can analyze and transform news content according to specified prompts.

Components
---------

An agent consists of:

- **Name**: A unique identifier for the agent
- **Description**: Details about what the agent does
- **Provider**: The LLM provider to use (OpenAI, Anthropic, Google, or Bedrock)
- **System Prompt**: The base prompt that defines the agent's behavior and capabilities
- **User Prompt Template**: A template for processing news content that must include a ``{news}`` placeholder
- **Active Status**: Whether the agent is currently enabled for use in streams

How It Works
-----------

1. Each agent is configured with two key prompts:

   - A system prompt that establishes the agent's role and behavior
   - A user prompt template that defines how news content should be processed

2. The user prompt template must contain a ``{news}`` placeholder where the news content will be inserted

3. When processing news, the agent:

   - Takes the incoming news content
   - Inserts it into the user prompt template
   - Sends both the system prompt and formatted user prompt to the specified LLM provider
   - Returns the LLM's response

Configuration
------------

Agents can be configured through the Django admin interface, where you can:

- Create new agents
- Define their prompts
- Select the LLM provider
- Enable/disable agents
- Monitor their creation and update timestamps

Available Providers
-----------------

Newsloom supports multiple LLM providers:

- OpenAI
- Anthropic
- Google
- Bedrock

Each provider may have different capabilities and pricing models. Choose the provider that best fits your needs in terms of:

- Model capabilities
- Cost
- Rate limits
- Response quality
- Processing speed

Best Practices
-------------

1. **System Prompts**:
   - Keep them focused on a single responsibility
   - Clearly define the expected behavior
   - Include any necessary constraints or guidelines

2. **User Prompt Templates**:
   - Always include the ``{news}`` placeholder
   - Structure the prompt to get consistent outputs
   - Consider including examples if needed

3. **Testing**:
   - Test agents with various types of news content
   - Verify outputs match expected format
   - Monitor performance and costs

4. **Maintenance**:
   - Regularly review and update prompts
   - Monitor agent performance
   - Keep track of usage and costs
   - Disable unused agents
