# TechStore AI Chat

Chatbot de atendimento para a **TechStore**, uma loja virtual fictícia. O projeto demonstra como conectar uma interface web local a um agente do Microsoft Foundry usando Python e Flask.

A página e o servidor rodam na sua máquina. O processamento das mensagens pelo agente ocorre no Azure, exige conexão com a internet e pode gerar custos na sua assinatura.

## Como funciona

```text
Navegador → Flask (/api/chat) → agente no Microsoft Foundry
Navegador ← resposta em JSON ← resposta do agente
```

O backend valida a mensagem, verifica o limite de requisições e aplica um filtro simples de assuntos antes de chamar o agente. A resposta é exibida na página do chat.

A aplicação se conecta a um projeto e a um agente já existentes. Ela não cria recursos Azure, implanta modelos ou configura agentes automaticamente.

## Tecnologias

- Python e Flask para o servidor e a API.
- HTML, CSS e JavaScript para a interface.
- `azure-ai-projects` para acessar o projeto e o agente no Foundry.
- `azure-identity` para autenticação com `DefaultAzureCredential`.
- `python-dotenv` para carregar a configuração local do `.env`.

## Pré-requisitos

- Python com `pip` e suporte a ambientes virtuais.
- Azure CLI instalada para autenticação local com `az login`.
- Uma assinatura Azure e acesso a um projeto do Microsoft Foundry.
- Um agente compatível com a API atual do Foundry, com modelo e instruções configurados.
- Permissão da identidade autenticada para acessar o projeto e executar o agente.

Consulte o [guia oficial para criar e acessar um prompt agent](https://learn.microsoft.com/en-us/azure/foundry/agents/quickstarts/prompt-agent). A integração usa `get_openai_client(agent_name=...)`, conversas e a API Responses.

## Executar localmente

Os comandos abaixo usam PowerShell no Windows. Execute-os na raiz do projeto.

### 1. Criar o ambiente e instalar as dependências

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install Flask python-dotenv azure-identity "azure-ai-projects>=2.3.0"
```

Os comandos usam diretamente o Python do ambiente virtual, sem precisar ativá-lo no PowerShell.

**Estado atual:** o arquivo `requirements.txt` está vazio. Por isso, a instalação acima lista as dependências explicitamente. O projeto ainda não fixa versões para uma instalação reproduzível.

### 2. Configurar o projeto e o agente

Crie um arquivo `.env` na raiz com os valores do seu Foundry:

```dotenv
FOUNDRY_PROJECT_ENDPOINT=https://SEU-RECURSO.services.ai.azure.com/api/projects/SEU-PROJETO
AGENT_NAME=nome-do-seu-agente
```

| Variável | Conteúdo |
| --- | --- |
| `FOUNDRY_PROJECT_ENDPOINT` | Endpoint completo do projeto, copiado do portal Foundry. |
| `AGENT_NAME` | Nome do agente existente nesse projeto; não é o nome do modelo nem um ID `asst_...`. |

A aplicação usa autenticação por identidade Azure; não é necessário adicionar uma chave de API ao `.env` para esse fluxo. O arquivo `.env` é ignorado pelo Git e não deve ser publicado.

### 3. Autenticar no Azure

```powershell
az login
```

Entre com a conta que possui acesso ao projeto. Se necessário, escolha a assinatura:

```powershell
az account set --subscription "ID-OU-NOME-DA-ASSINATURA"
```

O backend usa `DefaultAzureCredential`, que pode aproveitar a sessão do Azure CLI. Outras credenciais configuradas no ambiente também podem ser usadas por essa cadeia de autenticação.

### 4. Iniciar o servidor

```powershell
.\.venv\Scripts\python.exe -m app.main
```

Abra **http://127.0.0.1:5000** no navegador. Para encerrar, pressione `Ctrl+C` no terminal.

O backend tenta criar uma conversa no Foundry durante a inicialização. A configuração e a autenticação precisam estar válidas para o servidor iniciar.

### 5. Experimentar o chat

A interface e as palavras-chave do filtro estão em inglês. Para testar, envie uma mensagem como:

```text
What is the TechStore return policy?
```

A qualidade e o conteúdo da resposta dependem das instruções e das fontes configuradas no agente.

## Trocar de projeto Foundry

1. Crie ou selecione um projeto acessível e configure um agente com o modelo desejado.
2. Atualize `FOUNDRY_PROJECT_ENDPOINT` e `AGENT_NAME` no `.env`.
3. Autentique com uma conta que tenha acesso ao novo projeto.
4. Reinicie o servidor local.

Se o agente anterior usava documentos ou ferramentas, configure esses recursos novamente no novo agente. Alterar o `.env` não migra a configuração anterior.

## Estrutura

```text
techstore-ai-chat/
├── app/
│   ├── __init__.py
│   ├── main.py              # Rotas Flask e integração com o Foundry
│   ├── config.py            # Arquivo reservado; configuração ainda está em main.py
│   ├── tools.py             # Arquivo reservado; sem ferramentas implementadas
│   ├── templates/
│   │   └── index.html       # Página do chat
│   └── static/
│       ├── app.js           # Envio de mensagens e atualização da interface
│       └── style.css        # Estilos
├── knowledge/               # FAQ e políticas fictícias da TechStore
├── .env                     # Configuração local; ignorada pelo Git
├── .gitignore
├── requirements.txt         # Atualmente vazio
└── README.md
```

## Documentos de conhecimento

A pasta `knowledge/` contém uma FAQ e políticas de entrega, devolução e garantia da loja fictícia.

**O código atual não lê nem envia esses arquivos ao Foundry.** Para utilizá-los nas respostas, é necessário configurar uma fonte de conhecimento ou ferramenta apropriada no agente. Também não há integração implementada com catálogo, estoque, pagamentos ou pedidos reais.

## API local

`GET /` serve a interface. `POST /api/chat` recebe uma mensagem JSON:

```json
{
  "message": "What is the TechStore shipping policy?"
}
```

Em caso de sucesso, retorna:

```json
{
  "response": "Texto retornado pelo agente."
}
```

| Status | Significado |
| --- | --- |
| `200` | Resposta obtida do agente. |
| `400` | Mensagem inválida ou recusada pelo filtro de assuntos. |
| `429` | Limite de requisições atingido. |
| `500` | Falha durante o processamento ou a comunicação com o Foundry. |

As mensagens devem ser strings não vazias de até **500 caracteres**. O limite local é de **10 requisições por minuto por IP**, incluindo tentativas que depois sejam recusadas pela validação.

## Limitações do protótipo

- **Conversa compartilhada:** todas as requisições do mesmo processo usam uma única conversa no Foundry. Usuários diferentes podem compartilhar contexto; não use dados pessoais ou confidenciais nesse cenário.
- **Sem autenticação de usuários:** a rota de chat não possui controle de acesso próprio.
- **Modo de desenvolvimento:** o servidor inicia com `debug=True`. Antes de disponibilizar a aplicação na internet, desative o debugger e configure um servidor adequado.
- **Filtro por palavras-chave:** a verificação de assuntos procura termos em inglês e não garante que o conteúdo esteja dentro do escopo. Mensagens legítimas em português podem ser recusadas.
- **Limite em memória:** o controle de requisições reinicia com o processo, não é compartilhado entre instâncias e confia no cabeçalho `X-Forwarded-For`. Precisa ser revisto antes de uma exposição pública.
- **Sem banco de dados local:** o projeto não persiste usuários, pedidos ou histórico em um banco. A conversa é criada no serviço Foundry; reiniciar o processo cria outra conversa, sem excluir automaticamente a anterior.

## Solução de problemas

| Sintoma | O que verificar |
| --- | --- |
| `KeyError` ao iniciar | Se o `.env` está na raiz e contém as duas variáveis obrigatórias. |
| Erro de autenticação | A sessão de `az login` e a identidade usada por `DefaultAzureCredential`. |
| Acesso negado pelo Azure | Permissões no novo projeto e restrições de rede do recurso. |
| Agente não encontrado | O nome do agente e se o endpoint pertence ao projeto correto. |
| `ModuleNotFoundError` | Se as dependências foram instaladas no mesmo ambiente virtual usado para executar. |
| Mensagem recusada por assunto | Se contém uma das palavras-chave em inglês definidas em `app/main.py`. |
| Resposta genérica de erro | Os detalhes no terminal do Flask; a interface não exibe a exceção interna. |

## Publicação no GitHub

O `.gitignore` exclui o `.env`, ambientes virtuais, configurações locais do VS Code, caches, logs e artefatos de build. Mantenha credenciais fora do código e revise os arquivos preparados para commit antes de publicar.

Publicar o repositório disponibiliza o código. A hospedagem da aplicação exige configuração separada e a revisão das limitações acima.
