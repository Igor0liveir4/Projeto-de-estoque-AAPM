Instalação e Configuração
Siga os passos abaixo para preparar o ambiente e rodar o projeto localmente:

1. Clonar o Repositório e Acessar a Pasta
Bash
git clone <url-do-seu-repositorio>
cd Projeto-de-estoque-AAPM
2. Criar e Ativar um Ambiente Virtual (Recomendado)
Bash
# No Windows:
python -m venv venv
venv\\Scripts\\activate

# No Linux/macOS:
python3 -m venv venv
source venv/bin/activate
3. Instalar as Dependências
Bash
pip install -r requirements.txt
4. Configurar as Migrações do Banco de Dados (Alembic)
Caso precise redefinir ou inicializar a estrutura das tabelas:

Bash
# Inicializar o diretório do alembic (se necessário)
python -m alembic init migrations

# Gerar a revisão estrutural baseada nos modelos atuais
python -m alembic revision --autogenerate -m "reset inicial"

# Aplicar as migrações para criar as tabelas no arquivo banco.db
python -m alembic upgrade head
5. Criar o Usuário Administrador Inicial
Rode o script fornecido na raiz para alimentar o banco de dados com a primeira conta gerencial:

Bash
python criar_usuario.py
(Após o login com esta conta, você conseguirá cadastrar novos colaboradores diretamente pelo painel do site).

6. Inicializar o Servidor de Desenvolvimento
Coloque a aplicação para rodar localmente utilizando o Uvicorn com hot-reload ativado:

Bash
python -m uvicorn app.main:app --reload
Acesse o sistema pelo navegador através do endereço: http://127.0.0.1:8000

🛠️ Principais Recursos Implementados
🔒 Segurança Robusta (Auth):

Formulários de login e cadastro contra ataques de tempo (timing attacks).

Sessões mantidas por cookies HttpOnly (access_token) com parâmetro samesite="lax".

📊 Dashboard Inteligente (Home):

Métricas agregadas em cards (total de produtos, estoque geral acumulado, vendas e movimentações).

Gráficos interativos injetados dinamicamente via JSON:

Doughnut Chart: Quantidade de produtos ativos distribuídos por categoria.

Horizontal Bar Chart: Top 5 produtos com maior volume em estoque.

Vertical Bar Chart: Avaliação financeira real (Preço × Estoque) por categoria.

🛒 Ponto de Venda Integrado (PDV):

Módulo ágil para registrar transações de vendas de forma imediata aos clientes cadastrados.

🔄 Controle Flexível de Estoque:

Histórico e rotas dedicadas para entradas e saídas de mercadorias no almoxarifado da associação.

🎨 Experiência do Usuário (UX):

Diferenciação clara entre visitantes (Landing Page comercial com catálogo das últimas novidades) e usuários autenticados (Dashboard gerencial completo).

Tratamento customizado do Erro 404 integrado com carregamento de supercarros via API assíncrona (httpx).
"""

with open("README.md", "w", encoding="utf-8") as f:
f.write(markdown_content)

print("README.md gerado com sucesso!")

Com as informações adicionais que você passou sobre a **AAPM do SENAI**, os gráficos que sua `main.py` injeta no front-end, o fluxo de autenticação segura via tokens JWT e a estrutura do banco com o Alembic, montei um arquivo **README.md** extremamente técnico, limpo e profissional para o seu repositório.

O código Markdown foi salvo e o arquivo está pronto para ser adicionado à raiz do seu projeto:

[file-tag: code-generated-file-0-1781624282543173296]

Aqui está o conteúdo do arquivo formatado em texto para que você possa visualizar ou copiar diretamente, se preferir:

```markdown
# 📦 Sistema de Gestão de Estoque e Vendas — AAPM SENAI

Este é um sistema web robusto desenvolvido para a **AAPM (Associação de Alunos, Pais e Mestres) do SENAI**, com o objetivo de centralizar e automatizar o controle de estoque, o fluxo de movimentações de produtos e a operação de vendas (PDV).

A aplicação conta com um painel administrativo completo (Dashboard), gráficos gerenciais dinâmicos, controle de permissões por perfil (Administrador e Usuário Padrão) e autenticação segura via tokens JWT armazenados em cookies criptografados.

---

## 👥 Equipe de Desenvolvimento

* **Igor Oliveira** — *Desenvolvedor Back-end* (Regras de negócio, APIs e estruturação do banco de dados).
* **Enzo Rodrigues Leal** — *Desenvolvedor Front-end* (Arquitetura de diretórios e organização do repositório).
* **Gleidson Brian Muniz Lira** — *Desenvolvedor Front-end* (Estilização de interfaces e design do sistema).
* **Francisco Araujo Lima** — *Desenvolvedor Front-end* (Estilização de interfaces e design do sistema).

---

## 🚀 Tecnologias Utilizadas

* **Framework Web:** [FastAPI](https://fastapi.tiangolo.com/) (Python) — de alta performance, assíncrono e baseado em Pydantic.
* **Engine de Templates:** [Jinja2](https://jinja.palletsprojects.com/) — renderização dinâmica das páginas HTML no lado do servidor.
* **Mapeamento Objeto-Relacional (ORM):** [SQLAlchemy](https://www.sqlalchemy.org/) — para abstração das consultas ao banco de dados.
* **Banco de Dados:** SQLite (`banco.db`) — leve e integrado nativamente.
* **Gerenciamento de Migrações:** [Alembic](https://alembic.sqlalchemy.org/) — controle de versão estrutural do banco.
* **Autenticação:** JWT (JSON Web Tokens) com segurança baseada em cookies `HttpOnly` (proteção contra ataques XSS e CSRF) e senhas criptografadas via `bcrypt`.
* **Integrações Externas:** API do Unsplash (exibição aleatória de imagens temáticas de carros customizados na tela de erro 404).

---

## 📂 Estrutura do Projeto

O projeto segue o padrão arquitetural MVC (Model-View-Controller) adaptado para aplicações com FastAPI e Jinja2:

```text
├── app/
│   ├── controllers/               # Controladores e Definição das Rotas (APIRouter)
│   │   ├── admin_controller.py        # Gestão administrativa e relatórios
│   │   ├── auth_controller.py         # Login, cadastro e logout de usuários
│   │   ├── categoria_controller.py    # CRUD de categorias de produtos
│   │   ├── cliente_controller.py      # CRUD de clientes cadastrados
│   │   ├── movimentacao_controller.py # Entradas e saídas manuais do estoque
│   │   ├── pdv_controller.py          # Interface do Ponto de Venda
│   │   └── produto_controller.py      # CRUD de produtos e upload de imagens
│   ├── models/                    # Modelos do Banco de Dados (SQLAlchemy)
│   │   ├── categoria.py
│   │   ├── cliente.py
│   │   ├── movimentacao.py
│   │   ├── produto.py
│   │   ├── usuario.py
│   │   └── venda.py
│   ├── static/                    # Arquivos Estáticos Globais
│   │   ├── logo/                      # Logos e identidades visuais
│   │   ├── uploads/                   # Imagens enviadas dos produtos
│   │   └── style.css                  # Folha de estilo principal da aplicação
│   ├── templates/                 # Páginas HTML (Jinja2)
│   │   ├── auth/                      # Telas de login e cadastro
│   │   ├── categorias/                # Interfaces de gerenciamento de categorias
│   │   ├── Cliente/                   # Interfaces de gerenciamento de clientes
│   │   ├── movimentacoes/             # Históricos e formulários de estoque
│   │   ├── pdv/                       # Interface de Frente de Caixa
│   │   ├── produtos/                  # Telas de inventário e novos produtos
│   │   ├── usuarios/                  # Administração de contas de usuários
│   │   ├── 404.html                   # Página de erro customizada (Integração Unsplash)
│   │   ├── base.html                  # Template base (Navbar/Sidebar comuns)
│   │   ├── contato.html               # Página de suporte e contato
│   │   ├── home.html                  # Dashboard interno pós-login (Gráficos)
│   │   └── index.html                 # Landing page pública para usuários anônimos
│   ├── auth.py                    # Utilitários de segurança (JWT e hash de senhas)
│   ├── database.py                # Inicialização e injeção do banco (SessionLocal)
│   └── main.py                    # Ponto de entrada do FastAPI (Montagem das rotas)
├── migrations/                    # Arquivos gerados automaticamente pelo Alembic
├── .env                           # Variáveis de ambiente secretas (Chaves e JWT)
├── .gitignore                     # Arquivos ignorados no Versionamento
├── alembic.ini                    # Arquivo de configuração do Alembic
├── banco.db                       # Arquivo de banco de dados SQLite local
├── criar_usuario.py               # Script utilitário para criação do Administrador inicial
├── README.md                      # Documentação técnica do projeto
└── requirements.txt               # Lista de dependências e bibliotecas do ecossistema
⚙️ Instalação e Configuração
Siga os passos abaixo para preparar o ambiente e rodar o projeto localmente:

1. Clonar o Repositório e Acessar a Pasta
Bash
git clone <url-do-seu-repositorio>
cd Projeto-de-estoque-AAPM
2. Criar e Ativar um Ambiente Virtual (Recomendado)
Bash
# No Windows:
python -m venv venv
venv\Scripts\activate

# No Linux/macOS:
python3 -m venv venv
source venv/bin/activate
3. Instalar as Dependências
Bash
pip install -r requirements.txt
4. Configurar as Migrações do Banco de Dados (Alembic)
Caso precise redefinir ou inicializar a estrutura das tabelas:

Bash
# Inicializar o diretório do alembic (se necessário)
python -m alembic init migrations

# Gerar a revisão estrutural baseada nos modelos atuais
python -m alembic revision --autogenerate -m "reset inicial"

# Aplicar as migrações para criar as tabelas no arquivo banco.db
python -m alembic upgrade head
5. Criar o Usuário Administrador Inicial
Rode o script fornecido na raiz para alimentar o banco de dados com a primeira conta gerencial:

Bash
python criar_usuario.py
(Após o login com esta conta, você conseguirá cadastrar novos colaboradores ou novos administradores diretamente pelo painel do site).

6. Inicializar o Servidor de Desenvolvimento
Coloque a aplicação para rodar localmente utilizando o Uvicorn com hot-reload ativado:

Bash
python -m uvicorn app.main:app --reload
Acesse o sistema pelo navegador através do endereço: http://127.0.0.1:8000

🛠️ Principais Recursos Implementados
🔒 Segurança Robusta (Auth):

Tratamento contra ataques de tempo (timing attacks) na validação das credenciais.

Sessões mantidas com cookies seguros HttpOnly (access_token) com parâmetro samesite="lax".

📊 Dashboard Inteligente (Home):

Métricas agregadas em cards dinâmicos (total de produtos, estoque geral acumulado, vendas e movimentações).

Gráficos interativos injetados dinamicamente via JSON (Chart.js):

Doughnut Chart: Quantidade de produtos ativos distribuídos por categoria.

Horizontal Bar Chart: Top 5 produtos com maior volume em estoque.

Vertical Bar Chart: Avaliação financeira real (Preço de Venda × Estoque Atual) por categoria.

🛒 Ponto de Venda Integrado (PDV):

Módulo ágil para registrar transações de vendas de forma imediata aos clientes cadastrados.

🔄 Controle Flexível de Estoque:

Histórico e rotas dedicadas para entradas e saídas manuais de mercadorias no almoxarifado da associação.

🎨 Experiência do Usuário (UX):

Diferenciação clara entre visitantes (Landing Page comercial com catálogo de novidades) e usuários autenticados (Dashboard interno).

Tratamento customizado do Erro 404 integrado de forma assíncrona com carregamento via API externa do Unsplash.