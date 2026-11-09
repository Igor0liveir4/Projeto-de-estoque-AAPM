# 📦 Sistema de Gestão de Estoque e Vendas — AAPM SENAI

Este é um sistema web desenvolvido para a **AAPM (Associação de Alunos, Pais e Mestres) do SENAI**, com o objetivo de centralizar e automatizar o controle de estoque, o fluxo de movimentações de produtos e a operação de vendas (PDV).

🌐 **Acesse a aplicação online:** [https://projeto-de-estoque-aapm-1.onrender.com](https://projeto-de-estoque-aapm-1.onrender.com)

A aplicação conta com um painel administrativo completo (Dashboard), gráficos gerenciais dinâmicos, controle de permissões por perfil (Administrador e Usuário Padrão) e autenticação segura via tokens JWT armazenados em cookies criptografados.

---

## 👥 Equipe de Desenvolvimento

- **Igor Oliveira** — *Desenvolvedor Back-end* (Regras de negócio, APIs e estruturação do banco de dados)
- **Gleidson Brian Muniz Lira** — *Desenvolvedor Front-end* (Estilização de interfaces e design do sistema)
- **Francisco Araujo Lima** — *Desenvolvedor Front-end* (Estilização de interfaces e design do sistema)

---

## 🚀 Tecnologias Utilizadas

- **Framework Web:** [FastAPI](https://fastapi.tiangolo.com/) (Python) — alta performance, assíncrono e baseado em Pydantic.
- **Engine de Templates:** [Jinja2](https://jinja.palletsprojects.com/) — renderização dinâmica das páginas HTML no servidor.
- **Mapeamento Objeto-Relacional (ORM):** [SQLAlchemy](https://www.sqlalchemy.org/) — abstração de consultas ao banco de dados.
- **Banco de Dados:** SQLite (`banco.db`) — leve e integrado nativamente.
- **Gerenciamento de Migrações:** [Alembic](https://alembic.sqlalchemy.org/) — controle de versão estrutural do banco.
- **Autenticação:** JWT (JSON Web Tokens) com segurança baseada em cookies `HttpOnly` (proteção contra XSS/CSRF) e senhas criptografadas via `bcrypt`.
- **Hospedagem / Deploy:** [Render](https://render.com/)
- **Integrações Externas:** API do Unsplash (exibição de imagens dinâmicas na página de erro 404).

---

## 🛠️ Principais Recursos Implementados

- 🔒 **Segurança Robusta (Auth):** Proteção contra ataques de tempo (*timing attacks*) na validação de credenciais e sessões mantidas com cookies seguros `HttpOnly` (`access_token` com `samesite="lax"`).
- 📊 **Dashboard Inteligente (Home):** Métricas agregadas em cards dinâmicos e gráficos interativos injetados via JSON (Chart.js):
  - *Doughnut Chart:* Distribuição de produtos ativos por categoria.
  - *Horizontal Bar Chart:* Top 5 produtos com maior volume em estoque.
  - *Vertical Bar Chart:* Avaliação financeira real (Preço de Venda × Estoque Atual) por categoria.
- 🛒 **Ponto de Venda Integrado (PDV):** Módulo ágil para registrar transações de vendas vinculadas a clientes cadastrados.
- 🔄 **Controle Flexível de Estoque:** Histórico e rotas dedicadas para entradas e saídas manuais de mercadorias no almoxarifado.
- 🎨 **Experiência do Usuário (UX):** Separação entre visitantes (Landing Page pública com catálogo) e usuários autenticados (Dashboard interno), além de tratamento customizado do Erro 404 integrado assincronamente à API do Unsplash.

---

## 📂 Estrutura do Projeto

```text
├── app/
│   ├── controllers/            # Controladores e definição das rotas (APIRouter)
│   │   ├── admin_controller.py        # Gestão administrativa e relatórios
│   │   ├── auth_controller.py         # Login, cadastro e logout de usuários
│   │   ├── categoria_controller.py    # CRUD de categorias de produtos
│   │   ├── cliente_controller.py      # CRUD de clientes cadastrados
│   │   ├── movimentacao_controller.py # Entradas e saídas manuais do estoque
│   │   ├── pdv_controller.py          # Interface do Ponto de Venda (PDV)
│   │   └── produto_controller.py      # CRUD de produtos e upload de imagens
│   ├── models/                 # Modelos do banco de dados (SQLAlchemy)
│   │   ├── categoria.py
│   │   ├── cliente.py
│   │   ├── movimentacao.py
│   │   ├── produto.py
│   │   ├── usuario.py
│   │   └── venda.py
│   ├── static/                 # Arquivos estáticos globais
│   │   ├── logo/                      # Logos e identidades visuais
│   │   ├── uploads/                   # Imagens enviadas dos produtos
│   │   └── style.css                  # Folha de estilo principal da aplicação
│   ├── templates/              # Páginas HTML (Jinja2)
│   │   ├── auth/                      # Telas de login e cadastro
│   │   ├── categorias/                # Interfaces de gerenciamento de categorias
│   │   ├── Cliente/                   # Interfaces de gerenciamento de clientes
│   │   ├── movimentacoes/             # Históricos e formulários de estoque
│   │   ├── pdv/                       # Interface de Frente de Caixa (PDV)
│   │   ├── produtos/                  # Telas de inventário e novos produtos
│   │   ├── usuarios/                  # Administração de contas de usuários
│   │   ├── 404.html                   # Página de erro customizada (Integração Unsplash)
│   │   ├── base.html                  # Template base (Navbar e Sidebar comuns)
│   │   ├── contato.html               # Página de suporte e contato
│   │   ├── home.html                  # Dashboard interno pós-login (Gráficos)
│   │   └── index.html                 # Landing page pública para usuários anônimos
│   ├── auth.py                 # Utilitários de segurança (JWT e hash de senhas)
│   ├── pix.py                  # Geração local do payload e QR Code Pix
│   ├── database.py             # Inicialização e injeção do banco (SessionLocal)
│   └── main.py                 # Ponto de entrada do FastAPI (Montagem das rotas)
├── migrations/                 # Arquivos gerados automaticamente pelo Alembic
├── .env                        # Variáveis de ambiente secretas (Chaves JWT)
├── .gitignore                  # Arquivos ignorados pelo versionamento Git
├── alembic.ini                 # Arquivo de configuração do Alembic
├── banco.db                    # Arquivo do banco de dados SQLite local
├── criar_usuario.py            # Script utilitário para criação do Administrador inicial
├── README.md                   # Documentação técnica do projeto
└── requirements.txt            # Lista de dependências e bibliotecas do ecossistema
🌐 Acesso Online (Produção)
O sistema está implantado e pronto para uso na nuvem:

👉 https://projeto-de-estoque-aapm-1.onrender.com

⚙️ Instalação e Execução Local
Caso queira rodar o ambiente de desenvolvimento localmente na sua máquina, siga os passos abaixo:

1. Clonar o Repositório e Acessar a Pasta
Bash
git clone [https://github.com/Igor0liveir4/Projeto-de-estoque-AAPM.git](https://github.com/Igor0liveir4/Projeto-de-estoque-AAPM.git)
cd Projeto-de-estoque-AAPM
2. Criar e Ativar um Ambiente Virtual (Recomendado)
No Windows:

Bash
python -m venv venv
venv\Scripts\activate
No Linux/macOS:

Bash
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

# Aplicar as migrações para criar as tabelas no banco.db
python -m alembic upgrade head
5. Criar o Usuário Administrador Inicial
Execute o script utilitário para cadastrar a primeira conta gerencial:

Bash
python criar_usuario.py
(Após o login com essa conta, é possível cadastrar novos colaboradores ou administradores direto pelo painel do sistema).

6. Inicializar o Servidor de Desenvolvimento
Execute a aplicação com o Uvicorn ativando o modo de recarregamento automático (hot-reload):

Bash
python -m uvicorn app.main:app --reload
Acesse o sistema localmente no navegador pelo endereço: http://127.0.0.1:8000

📄 Licença
Projeto desenvolvido para fins educacionais e de gestão interna da AAPM SENAI.