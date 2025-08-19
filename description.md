# Project: AI Language Tutor - Development Phases

*   **Phase 0: Foundation & Environment Setup**
    *   **Goal**: To create a stable, reproducible, and secure development environment for the entire team. This phase ensures that all foundational services are in place before any application code is written.

*   **Phase 1: The Knowledge Graph (Building the Brain)**
    *   **Goal**: To build and populate the core knowledge graphs (Lexical, Grammatical, Pragmatic) that will serve as the "brain" of the application. This involves migrating existing data and creating new, AI-enriched content.

*   **Phase 2: The Core API (The Nervous System)**
    *   **Goal**: To develop the backend API that exposes the power of the knowledge graph. This API will handle all business logic, user management, personalization, and communication with the databases and AI services.

*   **Phase 3: The Frontend Experience (The Body)**
    *   **Goal**: To build an intuitive, responsive, and deeply personalized user interface. This is where the user interacts with the system, so the experience must be seamless and engaging.

*   **Phase 4: Voice Integration (The Voice)**
    *   **Goal**: To integrate Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities, transforming the application into an interactive conversational coach.

*   **Phase 5: Deployment & Operations (Going Live)**
    *   **Goal**: To reliably deploy the application to the cloud and establish an automated CI/CD pipeline for future updates and maintenance.


# Phase 0: Foundation & Environment Setup

**Goal**: To create a stable, reproducible, and secure development environment for the entire team. This phase ensures that all foundational services are in place before any application code is written. Following these steps will result in a "one-command" local setup.

---

### 1. Code Repository & Project Structure

*Goal: Establish a clean, organized monorepo and a clear Git workflow.*

- [ ] **Initialize Git Repository**
    - [ ] Create a new project directory: `mkdir ai-language-tutor && cd ai-language-tutor`.
    - [ ] Initialize Git: `git init`.
    - [ ] Create a `README.md` file with the project title and a brief description.
    - [ ] Create a `.gitignore` file. Use a comprehensive template for Python and Node.js. A good starting point can be found at [gitignore.io](https://www.toptal.com/developers/gitignore/api/python,node,vscode,macos,windows). Key entries must include:
        ```
        # Environments
        .env
        .venv/
        
        # Python
        __pycache__/
        *.pyc
        
        # Node
        node_modules/
        .next/
        
        # IDE / OS
        .vscode/
        .DS_Store
        ```

- [ ] **Establish Git Branching Strategy**
    - [ ] Adopt **GitHub Flow**:
        - `main` is the primary branch, always deployable.
        - All new work is done on descriptive feature branches (e.g., `feat/setup-backend-docker`, `fix/login-bug`).
        - Open a Pull Request (PR) to merge feature branches into `main`.
        - Code reviews are mandatory for merging PRs.
    - [ ] **Optional but Recommended**: Adopt **Conventional Commits** for commit messages (e.g., `feat:`, `fix:`, `docs:`, `chore:`). This standardizes commit history and enables automated changelog generation.

- [ ] **Set Up Monorepo Directory Structure**
    - [ ] Create the top-level directories within the project root:
        ```
        /ai-language-tutor
        |-- .git/
        |-- .gitignore
        |-- README.md
        |-- backend/       # FastAPI application
        |-- frontend/      # Next.js application
        |-- scripts/       # One-off scripts (data migration, generation)
        |-- docker-compose.yml
        ```

---

### 2. Cloud Services Provisioning & Security

*Goal: Provision all necessary third-party services and establish a secure method for managing credentials.*

- [ ] **Provision Databases & Services**
    - [ ] **Neo4j Graph Database**:
        - [ ] Create an account on [Neo4j AuraDB](https://neo4j.com/cloud/aura-db/).
        - [ ] Create a new **Free Tier** instance and record credentials.
    - [ ] **AI & Voice Services**:
        - [ ] Create an [OpenAI API](https://platform.openai.com/) account. Generate an API Key.
        - [ ] Create a [Google Cloud Platform](https://cloud.google.com/) project. Enable Speech-to-Text & Text-to-Speech APIs and get credentials.
    - [ ] **Vector Database**:
        - [ ] **No external provisioning needed.** We use PostgreSQL with pgvector via Docker.

- [ ] **Implement Secure Configuration Management**
    - [ ] Create/update the `.env.template` file.
        ```.env.template
        # Neo4j
        NEO4J_URI=
        NEO4J_USERNAME=neo4j
        NEO4J_PASSWORD=
        
        # PostgreSQL (running locally via Docker)
        DATABASE_URL=postgresql+asyncpg://postgres:testpassword123@postgres:5432/ai_language_tutor
        PGVECTOR_ENABLED=true
        EMBEDDING_DIMENSIONS=1536
        
        # OpenAI (used for AI responses and embeddings)
        OPENAI_API_KEY=
        
        # Backend JWT Secret
        JWT_SECRET_KEY=
        JWT_ALGORITHM=HS256
        ```
    - [ ] Each developer will create a local `.env` file in the project root by copying the template: `cp .env.template .env`.
    - [ ] Populate the `.env` file with the actual credentials obtained above. The `JWT_SECRET_KEY` can be generated using `openssl rand -hex 32`.

---

### 3. Local Development Environment with Docker

*Goal: Create a fully containerized local environment that can be launched with a single command.*

- [ ] **Create the Master `docker-compose.yml` file**
    - [ ] In the project root, create/update `docker-compose.yml` to include PostgreSQL and Neo4j services.
    ```yaml
    version: '3.8'

    services:
      # PostgreSQL Database with pgvector for user data and conversations
      postgres:
        image: pgvector/pgvector:pg16
        container_name: ai-tutor-postgres
        restart: unless-stopped
        ports:
          - "5432:5432"
        volumes:
          - postgres_data:/var/lib/postgresql/data
          - ./backend/migrations/init.sql:/docker-entrypoint-initdb.d/init.sql
        environment:
          - POSTGRES_DB=ai_language_tutor
          - POSTGRES_USER=postgres
          - POSTGRES_PASSWORD=testpassword123
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U postgres -d ai_language_tutor"]
          interval: 10s
          timeout: 5s
          retries: 5

      # Neo4j Graph Database
      neo4j:
        image: neo4j:5.15-community
        container_name: ai-tutor-neo4j
        restart: unless-stopped
        ports:
          - "7474:7474"  # HTTP
          - "7687:7687"  # Bolt
        volumes:
          - neo4j_data:/data
          - neo4j_logs:/logs
        environment:
          - NEO4J_AUTH=neo4j/testpassword123

      backend:
        build:
          context: ./backend
          dockerfile: Dockerfile
        ports:
          - "8000:8000"
        volumes:
          - ./backend:/app
        env_file:
          - ./.env
        command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
        depends_on:
          postgres:
            condition: service_healthy
          neo4j:
            condition: service_started

      frontend:
        build:
          context: ./frontend
          dockerfile: Dockerfile
        ports:
          - "3000:3000"
        volumes:
          - ./frontend:/app
          - /app/node_modules
          - /app/.next
        depends_on:
          - backend

    volumes:
      postgres_data:
        driver: local
      neo4j_data:
        driver: local
      neo4j_logs:
        driver: local
    ```

- [ ] **Create the Backend `Dockerfile`**
    - [ ] Inside the `/backend` directory, create a `Dockerfile`. Use a multi-stage build for efficiency and security.
    ```Dockerfile
    # Stage 1: Builder - Install dependencies
    FROM python:3.11-slim as builder
    
    WORKDIR /app
    
    # Install Poetry
    RUN pip install poetry
    
    # Copy only dependency files and install
    COPY poetry.lock pyproject.toml ./
    RUN poetry config virtualenvs.create false && poetry install --no-root --no-dev
    
    # Stage 2: Runner - Run the application
    FROM python:3.11-slim
    
    WORKDIR /app
    
    # Copy installed dependencies from the builder stage
    COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
    
    # Copy application code
    COPY . .
    
    EXPOSE 8000
    
    # This command will be overridden by docker-compose for local dev, but is good for production
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```

- [ ] **Create the Frontend `Dockerfile`**
    - [ ] Inside the `/frontend` directory, create a `Dockerfile`.
    ```Dockerfile
    # Stage 1: Builder - Install dependencies & build
    FROM node:18-alpine AS builder

    WORKDIR /app
    
    COPY package.json yarn.lock ./
    # Or package-lock.json for npm
    
    RUN yarn install --frozen-lockfile
    
    COPY . .
    
    RUN yarn build

    # Stage 2: Runner - Serve the production build
    FROM node:18-alpine
    
    WORKDIR /app

    COPY --from=builder /app/public ./public
    COPY --from=builder /app/.next ./.next
    COPY --from=builder /app/node_modules ./node_modules
    COPY --from=builder /app/package.json ./package.json
    
    EXPOSE 3000

    CMD ["yarn", "start"]
    ```

---

### 4. Tooling & Code Quality

*Goal: Integrate modern, high-performance tooling to enforce code consistency and catch errors early.*

- [ ] **Backend (Python) Tooling Setup**
    - [ ] Navigate to `/backend` and initialize **Poetry**: `poetry init`. Add dependencies like `fastapi`, `uvicorn`, `neo4j`, `pinecone-client`, `openai`, `pydantic`, `python-dotenv`.
    - [ ] Add development dependencies: `poetry add --group dev ruff mypy`.
    - [ ] Configure `pyproject.toml` to use **Ruff** for linting AND formatting, replacing `black`, `isort`, and `flake8`.
        ```toml
        [tool.ruff]
        line-length = 88
        
        [tool.ruff.lint]
        select = ["E", "F", "W", "I"] # Standard flake8, pyflakes, isort
        ```
    - [ ] Configure **Mypy** for static type checking in `pyproject.toml`.

- [ ] **Frontend (JS/TS) Tooling Setup**
    - [ ] Navigate to `/frontend` and initialize a Next.js project: `npx create-next-app@latest . --typescript`.
    - [ ] Configure **ESLint** (comes with Next.js) and **Prettier**.
    - [ ] Install Prettier: `npm install --save-dev prettier eslint-config-prettier`.
    - [ ] Configure them to work together by adding `prettier` to the `extends` array in `.eslintrc.json`.

- [ ] **IDE Configuration (VS Code)**
    - [ ] In the project root, create a `.vscode/settings.json` file to standardize settings for the team.
        ```json
        {
            "editor.formatOnSave": true,
            "editor.defaultFormatter": "esbenp.prettier-vscode",
            "[python]": {
                "editor.defaultFormatter": "ms-python.black-formatter", // Or use Ruff's formatter
                "editor.codeActionsOnSave": {
                    "source.organizeImports": true
                }
            },
            "python.linting.enabled": true,
            "python.linting.ruffEnabled": true,
            "python.formatting.provider": "none" // Use Ruff/Black directly
        }
        ```
    - [ ] Create a `.vscode/extensions.json` file with recommended extensions.
        ```json
        {
            "recommendations": [
                "ms-python.python",
                "ms-python.vscode-pylance",
                "ms-python.ruff",
                "esbenp.prettier-vscode",
                "dbaeumer.vscode-eslint",
                "ms-azuretools.vscode-docker"
            ]
        }
        ```

### 5. Verification

*Goal: Ensure the entire setup works correctly with a single command.*

- [ ] **Run the Application**
    - [ ] From the project root, run `docker-compose up --build`.
    - [ ] **Expectation**: Both the backend and frontend services build successfully and start without errors.
- [ ] **Test Endpoints**
    - [ ] Access the backend's interactive docs at `http://localhost:8000/docs`.
    - [ ] Access the frontend Next.js application at `http://localhost:3000`.
- [ ] **Verify Live Reloading**
    - [ ] Make a small, saved change to a file in `/backend`. The `uvicorn` server should automatically restart.
    - [ ] Make a small, saved change to a file in `/frontend`. The Next.js page in the browser should automatically update.




    # Phase 1: The Knowledge Graph (Building the Brain)

**Goal**: To build and populate the core knowledge graphs (Lexical, Grammatical) that will serve as the "brain" of the application. This involves migrating existing data and creating new, AI-enriched content.

---

### 1. Data Schema Definition (The Blueprint)

*Goal: Define the exact structure of our knowledge graph in Neo4j and vector embeddings in PostgreSQL before writing any import code. This ensures consistency.*

- [ ] **Define Neo4j Graph Schema**
    - [ ] Create a markdown document (`/docs/graph_schema.md`) to formally define the schema.
    - [ ] **Node Labels**: Define the primary node types:
        - `(:Word)`: Represents a lexical entry (e.g., a vocabulary word).
            - *Properties*: `id` (unique, e.g., the lemma), `lemma`, `reading`, `meaning`, `jlptLevel`.
        - `(:GrammarPoint)`: Represents a grammatical rule or pattern.
            - *Properties*: `id` (unique name), `name`, `description`, `structure`, `jlptLevel`, `status` (`approved`, `pending_review`).
        - `(:Example)`: An example sentence.
            - *Properties*: `text`, `reading`, `translation`.
        - `(:PartOfSpeech)`: e.g., Noun, Verb, Adjective.
        - `(:User)`: A user of the application.
        - `(:Goal)`, `(:Domain)`: Metadata nodes for personalization.
    - [ ] **Relationship Types**: Define the connections:
        - `[:IS_A]`: `(:Word)-[:IS_A]->(:PartOfSpeech)`
        - `[:HAS_PREREQUISITE]`: `(:GrammarPoint)-[:HAS_PREREQUISITE]->(:GrammarPoint)`
        - `[:CONTRASTS_WITH]`: `(:GrammarPoint)-[:CONTRASTS_WITH]->(:GrammarPoint)`
        - `[:APPEARS_IN]`: `(:Word)-[:APPEARS_IN]->(:Example)`
        - `[:SHOWS_GRAMMAR]`: `(:Example)-[:SHOWS_GRAMMAR]->(:GrammarPoint)`
        - `[:KNOWS]`: `(:User)-[:KNOWS]->(:Word or :GrammarPoint)`
            - *Properties*: `mastery`, `lastReviewed`, `correctAttempts`, `incorrectAttempts`.
        - `[:HAS_GOAL]`, `[:INTERESTED_IN]`: For user personalization.

- [ ] **Define PostgreSQL Vector Schema**
    - [ ] Plan the vector embedding tables we will create in PostgreSQL with pgvector. This will be done programmatically in a Python script later.
    - [ ] **Table Name**: `knowledge_embeddings`
    - [ ] **Properties**:
        - `neo4jId`: The unique `id` from the Neo4j node. **This is the critical link between the two databases.**
        - `content`: The text to be vectorized (e.g., a `GrammarPoint` description or a `Word`'s meaning).
        - `type`: The node label from Neo4j (`Word`, `GrammarPoint`).
    - [ ] **Vectorizer Configuration**: Define that we will use `text2vec-openai` to automatically generate vectors for the `content` property.

---

### 2. Data Migration & Ingestion (The Foundation)

*Goal: To port the existing lexical knowledge from the `jln.syntagent.com` NetworkX graph into our robust Neo4j database.*

- [ ] **Develop NetworkX Export Script**
    - [ ] Create a script: `/scripts/export_networkx.py`.
    - [ ] This script will load the existing NetworkX graph object.
    - [ ] It will use `networkx.readwrite.json_graph.node_link_data(G)` to convert the graph into a standard JSON format.
    - [ ] It will save the output to `jln_graph_export.json`.

- [ ] **Develop Neo4j Ingestion Script**
    - [ ] Create a script: `/scripts/import_from_json.py`.
    - [ ] This script will connect to the Neo4j AuraDB instance using credentials from the `.env` file.
    - [ ] **Step 1: Ingest Nodes**. Read the `nodes` array from the JSON file and use an `UNWIND` Cypher query to `MERGE` all nodes into the database, setting their properties.
    - [ ] **Step 2: Ingest Relationships**. Read the `links` array from the JSON file. Use an `UNWIND` query to `MATCH` the source and target nodes (which now exist) and `MERGE` the relationships between them.

- [ ] **Populate Metadata Nodes**
    - [ ] Create a simple script `/scripts/populate_metadata.py` to pre-populate the graph with essential metadata.
    - [ ] This will create `(:Goal)` nodes (e.g., 'Travel', 'Business'), `(:Domain)` nodes ('Anime', 'Food'), and `(:Level)` nodes ('Beginner', 'Intermediate').

---

### 3. AI-Powered Content Enrichment (The Intelligence)

*Goal: To use Large Language Models to systematically build out the Grammar Graph and create vector embeddings for all knowledge points.*

- [ ] **Develop the Grammar Generation Pipeline**
    - [ ] Create a script: `/scripts/generate_grammar.py`.
    - [ ] **Input**: A simple text file (`jlpt_n5_grammar.txt`) containing a list of grammar point names to be generated.
    - [ ] **Pydantic Schemas**: Create Pydantic models in `/backend/app/schemas.py` for `GrammarPoint` and its related items (`prerequisites`, `contrasts_with`, etc.). These will define the desired JSON structure.
    - [ ] **LangChain Orchestration**:
        - Use `PydanticOutputParser` to get formatting instructions from your Pydantic model.
        - Create a `PromptTemplate` that instructs the LLM to act as a Japanese linguistics expert and return a JSON object matching the format. The prompt will take a `grammar_point_name` as input.
        - Create the full chain: `prompt | llm | parser`.
    - [ ] **Logic**: The script will loop through the input list, invoke the chain for each grammar point, and on successful parsing, run a Cypher query to `MERGE` the new `(:GrammarPoint)` node and its relationships into Neo4j. Set its status to `pending_review`.

- [ ] **Develop the Knowledge Embedding Pipeline**
    - [ ] Create a script: `/scripts/embed_knowledge.py`.
    - [ ] **Step 1: Configure PostgreSQL Schema**. The script will first connect to PostgreSQL and ensure the `knowledge_embeddings` table exists with pgvector support.
    - [ ] **Step 2: Fetch Data from Neo4j**. The script will run a Cypher query to get the `id` and a content field (like `description` or `meaning`) for all `(:Word)` and `(:GrammarPoint)` nodes.
    - [ ] **Step 3: Generate and Store Embeddings**. The script will connect to OpenAI API to generate embeddings for the content, then batch insert to PostgreSQL. Each record will contain the `neo4j_id`, `content`, `type`, and `embedding` vector. PostgreSQL with pgvector will handle the vector storage and similarity search.

### 4. Verification

*Goal: Ensure the knowledge graph is populated correctly and the two databases are linked.*

- [ ] **Inspect Neo4j Database**
    - [ ] Connect to the AuraDB instance using the Neo4j Browser.
    - [ ] Run `MATCH (n) RETURN n LIMIT 100` to visually inspect the imported nodes.
    - [ ] Run `MATCH (g:GrammarPoint) RETURN g` to see the AI-generated content.
- [ ] **Inspect PostgreSQL Vector Database**
    - [ ] Use a simple Python script to query the `knowledge_embeddings` table with pgvector.
    - [ ] Perform a vector similarity search for a concept like "apology" and verify it returns records whose `neo4j_id` corresponds to nodes like "gomenasai" or "sumimasen" in Neo4j.


# Phase 2: The Core API (The Nervous System)

**Goal**: To develop the backend API that exposes the power of the knowledge graph. This API will handle all business logic, user management, personalization, and communication with the databases and AI services.

---

### 1. Backend Application Setup

*Goal: To establish a robust, well-structured FastAPI application with all necessary configurations and connections.*

- [ ] **Initialize FastAPI Project Structure**
    - [ ] Inside the `/backend` directory, create the main application structure. Use this structure to organize concerns logically:
        ```
        /backend
        |-- app/
        |   |-- __init__.py
        |   |-- main.py           # Main FastAPI app instance, middleware, and routers
        |   |-- schemas.py        # Pydantic models for API requests/responses
        |   |-- crud.py           # Functions for direct database interactions (CRUD)
        |   |-- services.py       # Higher-level business logic, calls to external APIs
        |   |-- db.py             # Database driver/client initialization and session management
        |   |-- core/
        |   |   |-- __init__.py
        |   |   |-- config.py     # Pydantic-based settings management to load .env
        |   |   |-- security.py   # JWT token logic, password hashing, user dependencies
        |   |-- api/
        |   |   |-- __init__.py
        |   |   |-- v1/
        |   |   |   |-- __init__.py
        |   |   |   |-- api.py        # Central router for v1 endpoints
        |   |   |   |-- endpoints/
        |   |   |   |   |-- auth.py
        |   |   |   |   |-- users.py
        |   |   |   |   |-- learning.py
        ```

- [ ] **Configure Settings and Database Connections**
    - [ ] **Settings Management**: In `app/core/config.py`, use Pydantic's `BaseSettings` to load and validate all environment variables from the `.env` file (e.g., `NEO4J_URI`, `OPENAI_API_KEY`, etc.).
    - [ ] **Database Connectors**: In `app/db.py`, create functions to initialize and manage the Neo4j driver and PostgreSQL connection instances. Implement FastAPI dependency injection functions (`get_neo4j_session`, `get_postgresql_session`) to provide these to API endpoints cleanly.

### 2. User Authentication & Onboarding

*Goal: To securely manage users and create the personalized onboarding experience.*

- [ ] **Implement Core Security Logic**
    - [ ] In `app/core/security.py`, create robust security utility functions:
        - `hash_password(password)` and `verify_password(plain_password, hashed_password)` using `passlib`.
        - `create_access_token(data: dict)` and `verify_access_token(token: str)` to handle JWTs.
        - A reusable dependency `get_current_active_user` that validates the JWT from the request header and returns the user model. This will be used to protect all authenticated endpoints.

- [ ] **Develop Authentication Endpoints (`/app/api/v1/endpoints/auth.py`)**
    - [ ] `POST /api/v1/auth/register`:
        - Accepts user details via a Pydantic schema.
        - Hashes the password securely.
        - Calls a `crud` function to create a new `(:User)` node in Neo4j.
        - Returns a success response.
    - [ ] `POST /api/v1/auth/token`:
        - Implements the standard OAuth2 `password` flow.
        - Accepts `username` and `password` in a form data request.
        - Authenticates the user against the database.
        - Returns a JWT `access_token` and `token_type`.

- [ ] **Develop User & Onboarding Endpoints (`/app/api/v1/endpoints/users.py`)**
    - [ ] `GET /api/v1/users/me`: A protected endpoint that uses `get_current_active_user` to return the current user's profile data.
    - [ ] `POST /api/v1/users/me/onboard`:
        - A protected endpoint.
        - Accepts a Pydantic model containing the user's `goals`, `domains`, and the results of their diagnostic quiz.
        - **Logic**: Calls a `service` function that runs Cypher queries to `MERGE` `[:HAS_GOAL]` and `[:INTERESTED_IN]` relationships. It then creates the initial `[:KNOWS]` relationships based on quiz results, setting a low starting `mastery` score.

### 3. Personalization & Learning Logic

*Goal: To create the core endpoints that deliver intelligent, personalized content to the user.*

- [ ] **Develop Dashboard Endpoint (`/app/api/v1/endpoints/learning.py`)**
    - [ ] `GET /api/v1/users/me/dashboard`:
        - A protected endpoint.
        - **Logic**: This is a critical `service` function that orchestrates several complex Neo4j queries:
            1.  **"Next Lesson" Query**: Finds a `GrammarPoint` whose prerequisites have a high mastery score but which the user has not yet learned.
            2.  **"Advanced Review Queue" Query**:
                - Implements an advanced Spaced Repetition System (SRS).
                - Calculates a `review_score` for each `Word` and `GrammarPoint` a user knows. This score is increased for items with **low mastery** and **older `lastReviewed` dates**.
                - **Domain Boost**: The score is given a priority boost if the item `[:USED_IN_DOMAIN]` the user is `[:INTERESTED_IN]`.
                - **Concept-Driven Triggers**: Periodically run queries to check for "rusty topics" (low average mastery within a `Topic`) or "unpracticed situations" (`PragmaticFunction` nodes not seen recently). If found, inject the weakest items from these concepts into the review queue.
            3.  **"Weakest Points" Query**: Finds nodes with a high `incorrectAttempts` ratio.
        - Returns a Pydantic schema containing the structured results, including the *reason* for a review item (e.g., "Rusty Topic: Food").

- [ ] **Develop Lesson & Practice Endpoints (`/app/api/v1/endpoints/learning.py`)**
    - [ ] `GET /api/v1/lessons/{item_id}`:
        - Fetches the details for a `Word` or `GrammarPoint`.
        - **Personalization Logic**: If it's a grammar point, the `service` function fetches multiple example sentences and runs a sub-query to find the one whose vocabulary the current user knows best, reducing cognitive load. Returns this "best fit" example.
    - [ ] `POST /api/v1/practice/generate`:
        - Takes a `topic_id`. This could be a single item, or an abstract concept like a `PragmaticFunction`.
        - **Logic**: If the topic is a `PragmaticFunction`, generate a situational exercise. Otherwise, if it's a contrast (e.g., `は` vs `が`), generate a fill-in-the-blank or multiple-choice question using vocabulary the user knows well.
    - [ ] `POST /api/v1/practice/submit`:
        - Takes `exercise_id` and the user's `answer` (as text).
        - **NLP Logic**: The `service` layer uses a Japanese NLP library (e.g., **GiNZA**/**spaCy**) to parse the user's answer into tokens, lemmas, and parts of speech.
        - **Evaluation Logic**: Compares the user's answer structure to the correct answer structure stored in the graph.
        - **Update Logic**: Calls a `crud` function to run a Cypher query that `MATCH`es the user and the knowledge nodes involved, then updates the `mastery`, `lastReviewed`, and `attempts` properties on the `[:KNOWS]` relationship.
        - Returns structured feedback (e.g., "Correct!" or "You used the wrong particle, here's why...").

### 4. Verification

*Goal: To ensure all API endpoints are working correctly and are robust.*

- [ ] **Manual Testing with Interactive Docs**
    - [ ] While developing, continuously test each endpoint's logic and schema validation using the auto-generated docs at `http://localhost:8000/docs`.
    - [ ] Manually run through the entire user flow: Register -> Login (get token) -> Onboard -> Request Dashboard -> Complete a Practice item -> Request Dashboard again to see changes.
- [ ] **Automated Testing Setup**
    - [ ] Configure `pytest` in the backend project.
    - [ ] Write unit tests for critical business logic in `services.py` and `crud.py`, mocking database calls where appropriate.
    - [ ] Write integration tests for the most important API endpoints (e.g., `token`, `dashboard`, `submit`) using FastAPI's `TestClient`. These tests can be configured to run against a separate, temporary test database for full coverage.


# Phase 3: The Frontend Experience (The Body)

**Goal**: To build an intuitive, responsive, and deeply personalized user interface. This is where the user interacts with the system, so the experience must be seamless and engaging.

---

### 1. Frontend Project Setup & Architecture

*Goal: To establish a modern, scalable, and maintainable Next.js project with a solid architecture for data fetching and state management.*

- [ ] **Initialize Next.js Project**
    - [ ] Navigate to the `/frontend` directory.
    - [ ] Initialize a new Next.js project using the App Router model and TypeScript: `npx create-next-app@latest . --typescript --tailwind --eslint`. (We'll choose Tailwind CSS for rapid, utility-first styling).
    - [ ] Clean up the default boilerplate code (e.g., in `app/page.tsx`).

- [ ] **Install and Configure Core Libraries**
    - [ ] **Data Fetching**: Install TanStack Query (formerly React Query) to manage all server state: `npm install @tanstack/react-query`.
    - [ ] **API Client**: Install `axios` for making HTTP requests to the backend: `npm install axios`.
    - [ ] **Global State Management**: Install `zustand` for minimal, non-server client state (like storing the auth token): `npm install zustand`.
    - [ ] **UI Components**: Install a component library like **Shadcn/UI**. This is not a traditional library but a set of beautifully designed, reusable components you can copy into your project. Follow its installation guide which uses the `npx shadcn-ui@latest init` command. This is highly recommended for its customizability and modern aesthetic.
    - [ ] **Icons**: Install `lucide-react` for a clean set of icons to use with Shadcn/UI.

- [ ] **Establish Frontend Architecture**
    - [ ] **API Layer**: Create a file `/lib/apiClient.ts`. Configure a global `axios` instance here. This instance should be set up to automatically include the JWT from the state manager in the `Authorization` header for all requests.
    - [ ] **State Management**: Create a state store `/stores/authStore.ts` using Zustand. This store will hold the user's authentication token, profile information, and login/logout actions.
    - [ ] **Component Structure**: Organize components logically in a `/components` directory. Create subdirectories like `/components/ui` (for Shadcn components), `/components/dashboard`, `/components/layout`, etc.
    - [ ] **Authentication Flow**: Implement a high-level component or logic in `app/layout.tsx` that checks for the auth token. If no token exists, redirect the user to the `/login` page for all protected routes.

### 2. User Authentication & Onboarding Screens

*Goal: To create a smooth and welcoming entry point for new and returning users.*

- [ ] **Build Authentication Pages**
    - [ ] Create a `/login/page.tsx`. Build a simple form with email and password fields. On submit, call the `/api/v1/auth/token` backend endpoint. If successful, save the token to the Zustand store and redirect to the `/dashboard`.
    - [ ] Create a `/register/page.tsx`. Build a form to capture user details. On submit, call `/api/v1/auth/register`, and upon success, redirect the user to the login page or directly to the onboarding flow.
    - [ ] Use Shadcn/UI's `Card`, `Input`, `Button`, and `Label` components to build these forms.

- [ ] **Build the Conversational Onboarding Flow**
    - [ ] Create a new route `/onboarding/page.tsx` that is protected and only accessible after first login.
    - [ ] Design a multi-step, conversational UI. Instead of one giant form, present one question at a time (e.g., "What are your goals?").
    - [ ] Use state (`useState`) to manage the current step of the onboarding process.
    - [ ] **Diagnostic Quiz**:
        - Fetch a small set of adaptive questions from a new `/api/v1/onboarding/quiz` endpoint.
        - The UI should present one question at a time.
        - Collect all user answers (goals, domains, quiz results).
    - [ ] On the final step, send all collected data to the `POST /api/v1/users/me/onboard` endpoint. Upon success, redirect to the `/dashboard`.

### 3. Core Application Screens

*Goal: To build the main interactive screens where learning takes place.*

- [ ] **Build the Dashboard Screen (`/dashboard/page.tsx`)**
    - [ ] This page will use TanStack Query's `useQuery` hook to fetch data from the `GET /api/v1/users/me/dashboard` endpoint.
    - [ ] **Componentize**: Create separate components for each part of the dashboard to keep the page clean:
        - `NextLessonCard.tsx`: Displays the primary "Next Lesson" call to action. Should be a clickable link that navigates to the lesson page.
        - `ReviewQueue.tsx`: Displays a list of items from the advanced SRS query. For each item, show the *reason* for the review (e.g., "Rusty Topic", "Goal-related").
        - `WeakestPoints.tsx`: Displays concepts the user is struggling with.
    - [ ] Implement loading states (e.g., showing skeleton loaders using Shadcn's `Skeleton` component) and error states (showing an error message if the API call fails).

- [ ] **Build the Lesson Screen (`/learn/lesson/[itemId]/page.tsx`)**
    - [ ] This is a dynamic route. It will use the `itemId` from the URL to fetch data from `/api/v1/lessons/{itemId}`.
    - [ ] The page should beautifully render the grammar/word information. Use a markdown renderer if descriptions support it.
    - [ ] **Personalized Examples**: Prominently display the personalized example sentence returned by the API.
    - [ ] **Connections Component**: Visually display the prerequisite and contrasting grammar points, with links to their respective lesson pages.

- [ ] **Build the Practice Screen ("Dojo") (`/practice/[topicId]/page.tsx`)**
    - [ ] This screen will be highly interactive.
    - [ ] It will fetch an exercise from `/api/v1/practice/generate` based on the `topicId`.
    - [ ] Dynamically render the correct exercise type (fill-in-the-blank, multiple choice, or a situational prompt).
    - [ ] On submission, post the answer to `/api/v1/practice/submit`. The UI should enter a "loading" state while awaiting feedback.
    - [ ] Display the feedback from the API clearly and visually. Use colors (green for correct, red for incorrect) and provide the explanatory text. Offer a "Next" button to fetch another exercise for the same topic.

- [ ] **Build the Knowledge Explorer Screen (Stretch Goal)**
    - [ ] Create a `/explore/page.tsx`.
    - [ ] Integrate a graph visualization library like `react-force-graph` or `vis-network`.
    - [ ] Fetch a subgraph from a new API endpoint (e.g., `/api/v1/graph/explore`).
    - [ ] Implement the dynamic node coloring based on the user's `mastery_score` fetched from their profile. This requires merging graph structure data with user progress data on the frontend.
    - [ ] Make nodes clickable to navigate to their respective lesson pages.

### 4. Verification

*Goal: To ensure the frontend is responsive, bug-free, and provides a delightful user experience.*

- [ ] **Manual End-to-End Testing**
    - [ ] Perform a full user journey: Register -> Onboard -> Go to Dashboard -> Start a Lesson -> Complete a Practice Session -> Check if Dashboard updates.
    - [ ] Test on multiple screen sizes (Desktop, Tablet, Mobile) to ensure responsiveness.
- [ ] **Component Testing (Optional)**
    - [ ] Use a testing framework like `Jest` with `React Testing Library` to write tests for individual components, especially those with complex logic.
- [ ] **Developer Experience**
    - [ ] Ensure TanStack Query Devtools are set up for easy debugging of server state during development.


# Phase 4: Voice Integration (The Voice)

**Goal**: To integrate Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities, transforming the application from a text-based tool into an interactive conversational coach.

---

### 1. Backend API Enhancements for Voice

*Goal: To create the necessary API endpoints to handle audio processing and generation, abstracting the complexity away from the frontend.*

- [ ] **Configure Voice Service SDKs**
    - [ ] Add the required Python SDKs to the backend's `pyproject.toml` using Poetry: `poetry add google-cloud-speech google-cloud-texttospeech`.
    - [ ] Update the Pydantic settings in `app/core/config.py` to load the Google Cloud credentials (e.g., the path to the service account JSON file).

- [ ] **Develop Speech-to-Text (STT) Endpoint**
    - [ ] In `/app/api/v1/endpoints/learning.py`, create a new endpoint: `POST /api/v1/practice/submit_audio`.
    - [ ] This endpoint will accept a file upload (`UploadFile` in FastAPI).
    - [ ] **Service Logic (`services.py`)**:
        - Create a function `transcribe_audio(audio_file)`.
        - This function will take the uploaded audio bytes.
        - It will call the Google Cloud Speech-to-Text API, configured for the Japanese language (`ja-JP`). Specify a model optimized for short commands or dictation.
        - It must handle API errors gracefully (e.g., if no speech is detected).
        - It returns the transcribed text as a string.
    - [ ] **Endpoint Flow**: The endpoint will call this service function. Once it receives the transcribed text, it will pass this text to the **exact same evaluation logic** used by the `POST /api/v1/practice/submit` endpoint. This is a crucial design choice to avoid duplicating code.

- [ ] **Develop Text-to-Speech (TTS) Endpoint**
    - [ ] In `/app/api/v1/endpoints/learning.py`, create a new endpoint: `GET /api/v1/tts/{item_id}`.
    - [ ] This endpoint will take a knowledge item's ID (e.g., a `Word` or `Example` ID).
    - [ ] **Service Logic (`services.py`)**:
        - Create a function `synthesize_speech(text_to_speak)`.
        - This function will call the Google Cloud Text-to-Speech API.
        - **Crucially, it must be configured to use a high-quality, neural Japanese voice** (e.g., a "WaveNet" voice like `ja-JP-Wavenet-B`).
        - It should request the output as an MP3 audio format.
        - It returns the audio content as bytes.
    - [ ] **Endpoint Flow**:
        - The endpoint will first query Neo4j to fetch the text content (and its `reading` for accuracy) associated with the `{item_id}`.
        - It will then pass this text to the `synthesize_speech` service function.
        - It will return the resulting MP3 audio bytes directly in the response with the correct `Content-Type` header (`audio/mpeg`). This is more efficient than saving a file to disk and then serving it.

### 2. Frontend Integration for Voice I/O

*Goal: To build a seamless user interface for recording audio and playing back generated speech.*

- [ ] **Implement Microphone Access & Recording Logic**
    - [ ] Create a reusable React hook: `useAudioRecorder()`.
    - [ ] This hook will handle the logic for:
        - Requesting microphone permissions from the user. This must be handled gracefully, including states for denied or pending permissions.
        - Using the browser's `MediaRecorder` API to start and stop recording.
        - Storing the recorded audio data in "chunks".
        - On `stop`, combining the chunks into a single `Blob` (e.g., in `audio/webm` format).
        - Providing state information back to the component (e.g., `isRecording`, `hasPermission`).

- [ ] **Integrate Recording into the Practice Screen ("Dojo")**
    - [ ] In the `/practice/[topicId]/page.tsx` component, add a microphone icon button.
    - [ ] Use the `useAudioRecorder` hook to manage recording state.
    - [ ] The microphone button's appearance should change based on the recording state (e.g., idle, recording, processing).
    - [ ] When a recording is complete, the frontend will create a `FormData` object, append the audio `Blob`, and `POST` it to the `/api/v1/practice/submit_audio` endpoint.
    - [ ] The UI should show a "transcribing..." or "processing..." state while awaiting the response from the backend.

- [ ] **Implement Audio Playback Logic**
    - [ ] Create a reusable component, e.g., `AudioPlayerButton.tsx`.
    - [ ] This component will take an `itemId` as a prop.
    - [ ] When clicked, it will make a `GET` request to the `/api/v1/tts/{itemId}` endpoint. **Crucially, it must specify that the expected response type is a `blob`.**
    - [ ] On receiving the audio blob, it will create an `Audio` object in the browser (`new Audio(URL.createObjectURL(blob))`) and play it.
    - [ ] The button should show a loading state while the audio is being fetched and generated.

- [ ] **Integrate Playback into the UI**
    - [ ] Add the `AudioPlayerButton` component wherever spoken Japanese is beneficial:
        - Next to example sentences on the **Lesson Screen**.
        - Next to vocabulary items in lists.
        - For the tutor's questions or feedback on the **Practice Screen**.

### 3. Verification

*Goal: To ensure the voice features are reliable, responsive, and work across different browsers.*

- [ ] **Manual End-to-End Voice Testing**
    - [ ] Perform a full voice-centric user journey:
        1.  Navigate to a lesson, click the audio button, and hear the example sentence spoken correctly.
        2.  Navigate to the practice screen.
        3.  Click the record button, speak a correct answer. Verify the app processes it and returns a "Correct" response.
        4.  Speak an incorrect answer. Verify the app returns the correct feedback.
        5.  Speak gibberish or stay silent. Verify the app handles the "no transcription" error gracefully.
- [ ] **Cross-Browser Compatibility Check**
    - [ ] Test the `MediaRecorder` API and audio playback on major browsers (Chrome, Firefox, Safari) as implementation can have subtle differences.
- [ ] **User Experience Testing**
    - [ ] Ensure the latency is acceptable. The time from when a user stops speaking to when they get feedback should feel near-instantaneous.
    - [ ] Confirm that the UI clearly communicates the state of permissions and recording to avoid user confusion.


# Phase 5: Deployment & Operations (Going Live)

**Goal**: To reliably deploy the application to the cloud and establish an automated CI/CD pipeline for future updates and maintenance.

---

### 1. Production Environment Preparation

*Goal: To prepare the application and its configuration for a production environment.*

- [ ] **Optimize Dockerfiles for Production**
    - [ ] **Backend `Dockerfile`**: Review the multi-stage build. Ensure no development dependencies (like `pytest` or `ruff`) are included in the final runner stage. The final image should be as small and secure as possible.
    - [ ] **Frontend `Dockerfile`**: Review the multi-stage build. The final runner stage should only contain the minimal files needed to serve the built Next.js application (`.next`, `public`, `node_modules`, `package.json`).

- [ ] **Configure Production Logging**
    - [ ] **Backend**: Modify the FastAPI logger configuration to output structured JSON logs instead of plain text. This is crucial for easy parsing by cloud logging services (like Google Cloud Logging or AWS CloudWatch). Libraries like `structlog` can be used for this.
    - [ ] **Frontend**: Implement an error tracking service like **Sentry** or **LogRocket**. This will capture and report any runtime errors or exceptions that occur in the user's browser, which are otherwise invisible to you.

- [ ] **Finalize Production Configuration**
    - [ ] Create a production-ready `.env.prod` file (this will NOT be committed to Git). This file will contain the real production database credentials and API keys.
    - [ ] Set `DEBUG` flags to `False` in all relevant parts of the application.
    - [ ] Configure the frontend to point to the production API domain name instead of `http://localhost:8000`.

### 2. Infrastructure Deployment

*Goal: To provision and configure the cloud infrastructure that will host the application.*

- [ ] **Choose and Configure Hosting Provider**
    - [ ] **Recommendation**: **Google Cloud Run**. It is a serverless platform that is perfect for containerized applications. It automatically scales (even to zero, which is cost-effective) and is very easy to manage.
    - [ ] **Alternative**: **AWS Fargate**. A similar serverless container offering from Amazon.

- [ ] **Set Up a Container Registry**
    - [ ] Create a private container registry to store your production Docker images.
    - [ ] **Recommendation**: **Google Artifact Registry**. It integrates seamlessly with Google Cloud Run.
    - [ ] **Alternative**: **Amazon Elastic Container Registry (ECR)** or **Docker Hub**.

- [ ] **Deploy the Application Manually (First Time)**
    - [ ] **Build and Push Images**: Manually build your production Docker images and push them to your container registry:
        - `docker build -f backend/Dockerfile . -t your-registry/ai-tutor-backend:0.1.0`
        - `docker push your-registry/ai-tutor-backend:0.1.0`
        - (Repeat for the frontend)
    - [ ] **Create Cloud Run Services**:
        - Create a Cloud Run service for the `backend`. Point it to the backend image in your registry. Crucially, use the built-in **Secret Manager** to securely provide all the environment variables from your `.env.prod` file. Do not paste them in plain text.
        - Create a Cloud Run service for the `frontend`. Point it to the frontend image. Configure its environment variables to point to the public URL of the backend service.
    - [ ] **Configure Networking**: Assign a public domain name to your frontend service and configure DNS records. Ensure CORS is correctly configured on the backend to only accept requests from your production frontend domain.

### 3. CI/CD Automation

*Goal: To create a "push-to-deploy" workflow that automatically tests and deploys new changes.*

- [ ] **Set Up GitHub Actions Secrets**
    - [ ] In your GitHub repository settings, navigate to `Secrets and variables > Actions`.
    - [ ] Add all the necessary credentials and IDs as encrypted secrets. Examples: `GCP_PROJECT_ID`, `GCP_SA_KEY` (service account key), `DOCKER_USERNAME`, etc. The workflow will use these to authenticate with your cloud provider.

- [ ] **Create the CI/CD Workflow File**
    - [ ] In your project root, create `.github/workflows/deploy.yml`.
    - [ ] **Define the Trigger**: The workflow should trigger on a `push` to the `main` branch.
        ```yaml
        on:
          push:
            branches:
              - main
        ```
    - [ ] **Define the Build & Test Job**:
        - This job will check out the code.
        - It can run linters (`ruff check .`) and tests (`poetry run pytest`) to ensure code quality before deploying. If any of these steps fail, the entire workflow fails.
    - [ ] **Define the Build & Push Job**:
        - This job (which depends on the success of the test job) will:
        - Authenticate with your container registry.
        - Build the backend and frontend Docker images using the production Dockerfiles.
        - Tag the images with a unique identifier, like the Git commit SHA, for traceability (`your-registry/backend:${{ github.sha }}`).
        - Push the newly tagged images to the registry.
    - [ ] **Define the Deploy Job**:
        - This job (which depends on the success of the push job) will:
        - Authenticate with your cloud provider (e.g., Google Cloud).
        - Run the `gcloud run deploy` command (or equivalent for AWS) to update your backend and frontend services, pointing them to the new image tags pushed in the previous step. This performs a zero-downtime deployment.

### 4. Monitoring & Maintenance

*Goal: To ensure the application remains healthy and performant after launch.*

- [ ] **Set Up Health Checks & Logging**
    - [ ] Create a simple `/health` endpoint on the backend that returns a `200 OK` status. Configure your cloud provider to ping this endpoint regularly to ensure the service is alive.
    - [ ] Connect your cloud logging service to the structured logs being emitted by your backend. Create dashboards or alerts for high error rates.
- [ ] **Database Backup Strategy**
    - [ ] **Neo4j AuraDB**: Backups are handled automatically by Neo4j. Familiarize yourself with the restore process just in case.
    - [ ] **PostgreSQL**: Set up automated backups using pg_dump. Create a scheduled job (e.g., a simple cron job or a serverless function) that periodically creates database backups including vector data and saves them to a secure cloud storage bucket (like Google Cloud Storage or AWS S3).
- [ ] **Review and Triage User Feedback**
    - [ ] Monitor Sentry or LogRocket for frontend errors.
    - [ ] Set up a system for collecting and prioritizing user-reported bugs and feature requests.





