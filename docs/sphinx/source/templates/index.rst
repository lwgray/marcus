Project Templates
=================

These templates help you structure your projects for optimal results with Marcus.

Why Use Templates?
------------------

Marcus works best when it has clear, structured information about your project:

* **PRD Template**: Define your project's goals, users, and requirements
* **Product Spec Template**: Technical specifications for implementation
* **Task Writing Guide**: Create tasks that AI agents can effectively complete

Available Templates
-------------------

.. toctree::
   :maxdepth: 1
   
   prd_template
   product_spec_template
   task_writing_guide

Best Practices
--------------

1. **Start with the PRD**: Define what you're building and why
2. **Create detailed specs**: The more detail, the better AI agents perform
3. **Break down features**: Create specific, actionable tasks
4. **Use clear language**: Avoid ambiguity in requirements
5. **Include examples**: Show expected inputs/outputs where possible

Marcus Metadata
---------------

Both templates include a special section for Marcus configuration::

    ## Marcus Metadata
    
    ### Automation Hints
    ```yaml
    marcus:
      project_type: "web-application"
      complexity: "medium"
      team_size: "3-5"
      preferred_agents:
        - backend_developer
        - frontend_developer
        - qa_engineer
    ```

This helps Marcus understand your project needs and assign appropriate workers.

Using Templates with GitHub
---------------------------

1. **Create a New Repository**
   
   * Use a descriptive name
   * Add a README with project overview
   * Set up issue labels

2. **Add Your PRD**
   
   * Create ``docs/PRD.md`` using the template
   * Fill in all sections
   * Commit to repository

3. **Create Product Spec**
   
   * Add ``docs/PRODUCT_SPEC.md``
   * Include technical details
   * Reference the PRD

4. **Generate Tasks**
   
   * Create GitHub issues from spec sections
   * Use clear titles and descriptions
   * Add appropriate labels

Example Workflow
----------------

1. **Define Project** (PRD)::

      Project: E-commerce Product Catalog
      Users: Online shoppers and store administrators
      Goals: Browse products, search, filter, and purchase

2. **Specify Technical Details** (Product Spec)::

      Backend: Python FastAPI with PostgreSQL
      Frontend: React with TypeScript
      Features: Product CRUD, search, cart, checkout

3. **Create Tasks**::

      - Task 1: Set up FastAPI project structure
      - Task 2: Create product database schema
      - Task 3: Implement product API endpoints
      - Task 4: Build product listing component
      - Task 5: Add search functionality

4. **Let Marcus Coordinate**
   
   * Workers will pick up tasks based on skills
   * Progress tracked automatically
   * Blockers resolved with AI assistance

Template Sections Explained
---------------------------

PRD Template
~~~~~~~~~~~~

**Executive Summary**
   2-3 paragraphs explaining the project vision

**Problem Statement**
   What problem does this solve? Why now?

**User Personas**
   Who will use this? What are their needs?

**Functional Requirements**
   What features must be included?

**Success Metrics**
   How do we measure success?

Product Spec Template
~~~~~~~~~~~~~~~~~~~~~

**Technical Architecture**
   System design and technology choices

**API Specification**
   Detailed endpoint documentation

**Data Models**
   Database schema and relationships

**UI/UX Requirements**
   Interface specifications and flows

**Testing Strategy**
   How to verify functionality

Customizing Templates
---------------------

Feel free to adapt templates for your needs:

* Add sections relevant to your domain
* Remove sections that don't apply
* Include company-specific requirements
* Add compliance or security sections

Tips for Success
----------------

1. **Be Specific**
   
   ❌ "Users should be able to log in"
   
   ✅ "Users log in with email/password, receive JWT token valid for 24 hours"

2. **Include Examples**
   
   Show sample API requests/responses, UI mockups, or data structures

3. **Define Edge Cases**
   
   What happens when things go wrong? How should errors be handled?

4. **Set Clear Priorities**
   
   Mark features as "Must Have", "Should Have", or "Nice to Have"

5. **Version Your Specs**
   
   Track changes as requirements evolve

Next Steps
----------

* Download and customize the templates
* Create your first project specification
* Generate tasks from your specifications
* Start Marcus and watch your project come to life!