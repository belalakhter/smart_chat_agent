## Slack AI Bot
Uses LLMs and RAG to summarize documents and QA channel related activity.

### Features
- Summarize documents using llm
- Send alerts for user activity monitors
- Manage user notes
- Ask About anything related to channel activity

### Slack Integeration
- Requires BOT and APP Token
- Socket mode enabled with event subscription for bot with channel.message permissions
- Required OAuth scopes: channels:read, chat:write, users:read, files:read

#### Slack commands
- /accept-alerts Start receiving messages summary
- /cancel-alert Stop recieving messages summary
- /list-alerts List users accepted alerts
- /note Add a user note
- /get-notes get user notes
- /summarize summarize documents
- /ask {query} Ask about channel activity

### Run app
- Using docker-compose up --build -d
- poetry lock && poetry install && poetry run -m python3 src.agent.main
- Depends On ENV SLACK_BOT_TOKEN, SLACK_APP_TOKEN, PORT, PINECONE_API_KEY, DEEPSEEK_URL

### Images
![QA](./assets/qa.png)
