# AI Language Tutor - Development Workflow with Archon

**Document ID**: `1d93e70a-1a03-459f-86b3-600caf84d0ef`  
**Type**: Guide Document  
**Author**: Development Team  
**Last Updated**: 2025-08-21  

## 🎯 Overview

This document outlines the comprehensive development workflow for the AI Language Tutor project using Archon for project management, task tracking, and knowledge organization.

## 🔄 The Golden Rule: Task-Driven Development with Archon

**MANDATORY: Always complete the full Archon task cycle before any coding:**

### Core Workflow Steps

```
1. Check Current Task
   ↓
2. Research for Task  
   ↓
3. Implement the Task
   ↓
4. Update Task Status
   ↓
5. Get Next Task
   ↓
6. Repeat Cycle
```

### Detailed Workflow Process

#### Step 1: Check Current Task 📋
**Objective**: Review task details and requirements

**Actions**:
```bash
# List all tasks to see priorities and status
mcp_archon_list_tasks(project_id="b92eed44-93e0-49d4-9cd5-011893b43edd")

# Get detailed task information
mcp_archon_get_task(task_id="[selected_task_id]")
```

**Key Information to Extract**:
- Task title and description
- Assignee and priority (task_order)
- Feature category and dependencies
- Acceptance criteria and requirements
- Related sources and code examples

#### Step 2: Research for Task 🔍
**Objective**: Search relevant documentation and examples

**Actions**:
```bash
# Search knowledge base for relevant content
mcp_archon_perform_rag_query(
    query="How does [specific functionality] work?",
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd"
)

# Find relevant code examples
mcp_archon_search_code_examples(
    query="[implementation pattern]",
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd"
)
```

**Research Areas**:
- Existing codebase patterns and implementations
- Architecture decisions and constraints
- Integration points with other components
- Testing strategies and quality requirements
- Performance and security considerations

#### Step 3: Implement the Task ⚙️
**Objective**: Write code based on research

**Implementation Guidelines**:
- Follow existing code patterns and architecture
- Maintain consistency with established conventions
- Include comprehensive error handling
- Add appropriate logging and monitoring
- Write tests for new functionality
- Update documentation as needed

**Code Quality Standards**:
- **Python**: Use Ruff for formatting, type hints, docstrings
- **TypeScript**: ESLint + Prettier, strict mode, proper typing
- **Testing**: Pytest for backend, comprehensive test coverage
- **Documentation**: Google-style docstrings for all functions

#### Step 4: Update Task Status 📊
**Objective**: Move task through proper status progression

**Status Progression**:
```
todo → doing → review → completed
```

**Actions**:
```bash
# Move task to "doing" when starting work
mcp_archon_update_task(
    task_id="[task_id]",
    status="doing"
)

# Add implementation notes and progress updates
mcp_archon_update_task(
    task_id="[task_id]",
    description="[updated_description_with_progress]"
)

# Move to "review" when ready for validation
mcp_archon_update_task(
    task_id="[task_id]",
    status="review"
)
```

**Important Notes**:
- **Never skip status progression**: Always go todo → doing → review
- **Add implementation notes**: Document decisions, challenges, solutions
- **Update task descriptions**: Include progress, blockers, next steps
- **Link to related work**: Reference PRs, commits, documentation updates

#### Step 5: Get Next Task 🎯
**Objective**: Check for next priority task

**Task Selection Criteria**:
1. **Priority**: Higher task_order numbers first
2. **Dependencies**: Ensure prerequisites are completed
3. **Assignee**: Match your role (User, AI IDE Agent, etc.)
4. **Feature Area**: Consider context switching costs
5. **Complexity**: Balance challenging and straightforward tasks

#### Step 6: Repeat Cycle 🔄
**Objective**: Maintain continuous development flow

**Cycle Optimization**:
- Keep task cycles short (1-3 days maximum)
- Regular status updates and progress tracking
- Proactive communication of blockers
- Documentation of decisions and learnings

## 🛠️ Archon MCP Tools Reference

### Project Management Tools

#### Task Management
```bash
# List tasks with filtering options
mcp_archon_list_tasks(
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    filter_by="status",  # "status", "project", "assignee"
    filter_value="todo"  # "todo", "doing", "review", "done"
)

# Get detailed task information
mcp_archon_get_task(task_id="[task_id]")

# Create new tasks
mcp_archon_create_task(
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    title="[task_title]",
    description="[detailed_description]",
    assignee="AI IDE Agent",  # "User", "AI IDE Agent", "prp-executor"
    task_order=10,  # Priority (higher = more important)
    feature="[feature_category]"
)

# Update task status and details
mcp_archon_update_task(
    task_id="[task_id]",
    status="doing",  # "todo", "doing", "review", "done"
    description="[updated_description]"
)
```

#### Documentation Management
```bash
# List all project documents
mcp_archon_list_documents(project_id="b92eed44-93e0-49d4-9cd5-011893b43edd")

# Get document details
mcp_archon_get_document(
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    doc_id="[document_id]"
)

# Create new documentation
mcp_archon_create_document(
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    title="[document_title]",
    document_type="spec",  # "spec", "design", "note", "guide", "api"
    content={},  # JSON structure
    tags=["tag1", "tag2"],
    author="Development Team"
)

# Update existing documents
mcp_archon_update_document(
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    doc_id="[document_id]",
    title="[updated_title]",
    content={}  # Updated JSON content
)
```

#### Knowledge & Research
```bash
# Search knowledge base for relevant content
mcp_archon_perform_rag_query(
    query="How does authentication work in FastAPI?",
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    match_count=5
)

# Search for relevant code examples
mcp_archon_search_code_examples(
    query="JWT authentication implementation",
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    match_count=5
)
```

#### Version Control
```bash
# Create version snapshots
mcp_archon_create_version(
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    field_name="docs",  # "docs", "features", "data", "prd"
    content=[],  # Content to snapshot
    change_summary="Added authentication documentation"
)

# List version history
mcp_archon_list_versions(
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    field_name="docs"
)

# Restore previous version
mcp_archon_restore_version(
    project_id="b92eed44-93e0-49d4-9cd5-011893b43edd",
    field_name="docs",
    version_number=2
)
```

## 📋 Current Task Priorities

### High Priority Tasks (Ready for Development)

1. **Phase 4 - Voice Integration** (Priority: 16)
   - **Assignee**: AI IDE Agent
   - **Scope**: Speech-to-Text, Text-to-Speech, voice exercises
   - **Status**: todo
   - **Feature**: voice-integration

2. **Complete Streamlit Validation Interface** (Priority: 13)
   - **Assignee**: AI IDE Agent
   - **Scope**: Human validation workbench, linguistic analysis
   - **Status**: todo
   - **Feature**: validation-interface

3. **Enhance Knowledge Graph Data Import** (Priority: 10)
   - **Assignee**: AI IDE Agent
   - **Scope**: Execute NetworkX & Lee's vocabulary import
   - **Status**: todo
   - **Feature**: knowledge-graph

### Medium Priority Tasks

4. **Phase 5 - Deployment & Operations** (Priority: 8)
   - **Assignee**: AI IDE Agent
   - **Scope**: Production deployment, CI/CD, monitoring
   - **Status**: todo
   - **Feature**: deployment

5. **Implement Grammar Study Interface** (Priority: 7)
   - **Assignee**: AI IDE Agent
   - **Scope**: Enhanced grammar learning UI
   - **Status**: todo
   - **Feature**: grammar-learning

6. **Documentation Updates** (Priority: 6)
   - **Assignee**: User
   - **Scope**: Comprehensive documentation maintenance
   - **Status**: todo
   - **Feature**: documentation

### Future Tasks

7. **Multi-Language Expansion - Korean** (Priority: 3)
   - **Assignee**: AI IDE Agent
   - **Scope**: Korean language support integration
   - **Status**: todo
   - **Feature**: multi-language

## 🎯 Task Assignment Guidelines

### Assignee Roles

#### User
- **Responsibilities**: Manual tasks, documentation, project management
- **Typical Tasks**: Documentation updates, requirement gathering, testing coordination
- **Tools**: Archon MCP tools, local development environment

#### AI IDE Agent  
- **Responsibilities**: Code implementation, technical tasks, testing
- **Typical Tasks**: Feature development, bug fixes, integration work
- **Tools**: Full development stack, AI-assisted coding, automated testing

#### prp-executor
- **Responsibilities**: PRP coordination, project orchestration
- **Typical Tasks**: Cross-component integration, workflow coordination
- **Tools**: Project management, coordination between teams

#### prp-validator
- **Responsibilities**: Testing, validation, quality assurance
- **Typical Tasks**: Test execution, validation workflows, quality checks
- **Tools**: Testing frameworks, validation tools

## 📊 Progress Tracking

### Task Status Definitions

- **todo**: Task is defined and ready to be started
- **doing**: Task is actively being worked on
- **review**: Task implementation is complete, awaiting review/validation
- **done**: Task is completed and validated

### Progress Metrics

#### Individual Task Progress
- Time from todo → doing (task pickup time)
- Time from doing → review (implementation time)
- Time from review → done (review/validation time)
- Total cycle time (todo → done)

#### Project Progress
- Tasks completed per sprint/week
- Feature completion percentage
- Blocker resolution time
- Code quality metrics (test coverage, linting scores)

## 🚧 Common Workflow Scenarios

### Scenario 1: Starting a New Feature
1. **Research Phase**:
   - Use RAG query to understand existing patterns
   - Search code examples for similar implementations
   - Review architecture documentation

2. **Planning Phase**:
   - Break down large tasks into smaller subtasks
   - Identify dependencies and integration points
   - Plan testing strategy

3. **Implementation Phase**:
   - Update task status to "doing"
   - Follow established code patterns
   - Write tests alongside implementation
   - Document decisions and trade-offs

4. **Review Phase**:
   - Update task status to "review"
   - Run comprehensive tests
   - Update documentation
   - Request validation if needed

### Scenario 2: Handling Blockers
1. **Identify Blocker**:
   - Update task description with blocker details
   - Add blocker tag or status indicator
   - Document attempted solutions

2. **Research Solutions**:
   - Use RAG queries for similar issues
   - Search code examples for alternative approaches
   - Consult project documentation

3. **Escalate if Needed**:
   - Update task with escalation request
   - Provide detailed context and attempted solutions
   - Suggest alternative approaches

### Scenario 3: Task Dependencies
1. **Identify Dependencies**:
   - Check prerequisite tasks in task description
   - Verify dependency completion status
   - Plan work order to minimize blocking

2. **Coordinate Work**:
   - Communicate with dependency task owners
   - Plan parallel work where possible
   - Update task descriptions with dependency status

## 🔧 Development Environment Integration

### Local Development Workflow
```bash
# 1. Check current tasks
mcp_archon_list_tasks(project_id="b92eed44-93e0-49d4-9cd5-011893b43edd")

# 2. Start development environment
docker-compose up -d

# 3. Update task status
mcp_archon_update_task(task_id="[task_id]", status="doing")

# 4. Implement feature
# ... development work ...

# 5. Run tests
.\scripts\run_tests.ps1

# 6. Update task status
mcp_archon_update_task(task_id="[task_id]", status="review")

# 7. Document progress
mcp_archon_update_task(
    task_id="[task_id]",
    description="[updated_description_with_progress]"
)
```

### Quality Assurance Integration
- **Automated Testing**: Run tests before moving to "review" status
- **Code Quality**: Ensure Ruff (Python) and ESLint (TypeScript) pass
- **Documentation**: Update relevant documentation with changes
- **Performance**: Consider performance impact of changes

## 📈 Success Metrics

### Development Velocity
- Tasks completed per week
- Average task cycle time
- Blocker resolution time
- Feature delivery time

### Quality Metrics
- Test coverage percentage
- Code quality scores (Ruff, ESLint)
- Bug discovery rate
- User feedback scores

### Process Metrics
- Task status progression smoothness
- Documentation completeness
- Knowledge sharing effectiveness
- Team collaboration quality

## 🎯 Best Practices

### Task Management
- **Keep tasks focused**: Single responsibility, clear acceptance criteria
- **Regular updates**: Update status and progress frequently
- **Clear communication**: Document decisions, blockers, and solutions
- **Dependency awareness**: Understand and communicate task dependencies

### Research and Learning
- **Use RAG queries**: Leverage knowledge base for context and examples
- **Document learnings**: Share insights and solutions with the team
- **Stay updated**: Keep up with project architecture and decisions
- **Ask questions**: Don't make assumptions, clarify requirements

### Code Quality
- **Follow patterns**: Maintain consistency with existing codebase
- **Test thoroughly**: Write comprehensive tests for new functionality
- **Document code**: Add clear comments and docstrings
- **Performance aware**: Consider scalability and performance impact

### Collaboration
- **Share knowledge**: Document solutions and patterns
- **Help others**: Assist with blockers and knowledge sharing
- **Communicate proactively**: Update status and progress regularly
- **Learn continuously**: Stay updated with project evolution

---

**This workflow ensures systematic, high-quality development while maintaining clear progress tracking and knowledge sharing through Archon's comprehensive project management capabilities.**
