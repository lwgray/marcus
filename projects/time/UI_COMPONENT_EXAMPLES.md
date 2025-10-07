# User Interface Component Examples

This document provides HTML/CSS/JavaScript examples for implementing user-friendly UI components based on the usability requirements.

## Table of Contents

1. [Form Components](#form-components)
2. [Error Display](#error-display)
3. [Loading States](#loading-states)
4. [Success Feedback](#success-feedback)
5. [Empty States](#empty-states)
6. [Accessibility Examples](#accessibility-examples)

---

## 1. Form Components

### Task Creation Form with Inline Validation

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Create Task - User-Friendly Form</title>
    <style>
        /* Base styles for usability */
        .form-container {
            max-width: 600px;
            margin: 2rem auto;
            padding: 2rem;
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        label {
            display: block;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #374151;
        }

        .required::after {
            content: " *";
            color: #DC2626;
        }

        .optional {
            font-weight: 400;
            color: #6B7280;
            font-size: 0.875rem;
        }

        .help-text {
            display: block;
            font-size: 0.875rem;
            color: #6B7280;
            margin-top: 0.25rem;
        }

        input, textarea, select {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #D1D5DB;
            border-radius: 6px;
            font-size: 1rem;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #3B82F6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        /* Validation states */
        .input-valid {
            border-color: #10B981;
        }

        .input-invalid {
            border-color: #DC2626;
        }

        .validation-message {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 0.5rem;
            font-size: 0.875rem;
        }

        .validation-message.success {
            color: #059669;
        }

        .validation-message.error {
            color: #DC2626;
        }

        .validation-message.warning {
            color: #D97706;
        }

        .char-counter {
            text-align: right;
            font-size: 0.875rem;
            color: #6B7280;
            margin-top: 0.25rem;
        }

        .char-counter.warning {
            color: #D97706;
        }

        .char-counter.danger {
            color: #DC2626;
        }

        /* Button styles */
        .button-group {
            display: flex;
            gap: 1rem;
            margin-top: 2rem;
        }

        button {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s, transform 0.1s;
        }

        button:active {
            transform: translateY(1px);
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-primary {
            background-color: #3B82F6;
            color: white;
        }

        .btn-primary:hover:not(:disabled) {
            background-color: #2563EB;
        }

        .btn-secondary {
            background-color: #E5E7EB;
            color: #374151;
        }

        .btn-secondary:hover:not(:disabled) {
            background-color: #D1D5DB;
        }

        /* Advanced options toggle */
        .advanced-toggle {
            background: none;
            border: none;
            color: #3B82F6;
            cursor: pointer;
            padding: 0.5rem 0;
            font-size: 0.875rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .advanced-options {
            display: none;
        }

        .advanced-options.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>Create New Task</h1>
        <p style="color: #6B7280; margin-bottom: 2rem;">
            Fill out the form below to create a new task. Fields marked with * are required.
        </p>

        <form id="taskForm" novalidate>
            <!-- Title (Required) -->
            <div class="form-group">
                <label for="title" class="required">Task Title</label>
                <span class="help-text">A clear, concise name for your task</span>
                <input
                    type="text"
                    id="title"
                    name="title"
                    placeholder="e.g., Review project proposal"
                    maxlength="200"
                    required
                    aria-describedby="title-help title-validation"
                >
                <div id="title-validation" class="validation-message" role="alert" aria-live="polite"></div>
                <div id="title-counter" class="char-counter">0 / 200 characters</div>
            </div>

            <!-- Description (Optional) -->
            <div class="form-group">
                <label for="description">
                    Description
                    <span class="optional">(Optional)</span>
                </label>
                <span class="help-text">Add more details about what needs to be done</span>
                <textarea
                    id="description"
                    name="description"
                    rows="4"
                    placeholder="Describe the task in more detail..."
                    maxlength="5000"
                    aria-describedby="description-help"
                ></textarea>
                <div id="description-counter" class="char-counter">0 / 5000 characters</div>
            </div>

            <!-- Priority (Optional with default) -->
            <div class="form-group">
                <label for="priority">
                    Priority
                    <span class="optional">(Default: Medium)</span>
                </label>
                <span class="help-text">How important is this task?</span>
                <select id="priority" name="priority" aria-describedby="priority-help">
                    <option value="LOW">Low Priority - No rush, can be done anytime</option>
                    <option value="MEDIUM" selected>Medium Priority - Normal priority, regular workflow</option>
                    <option value="HIGH">High Priority - Important, should be done soon</option>
                    <option value="URGENT">Urgent - Critical, needs immediate attention</option>
                </select>
            </div>

            <!-- Due Date (Optional) -->
            <div class="form-group">
                <label for="due_date">
                    Due Date
                    <span class="optional">(Optional)</span>
                </label>
                <span class="help-text">When does this task need to be completed?</span>
                <input
                    type="datetime-local"
                    id="due_date"
                    name="due_date"
                    aria-describedby="due-date-help"
                >
                <div id="due-date-validation" class="validation-message" role="alert" aria-live="polite"></div>
            </div>

            <!-- Advanced Options Toggle -->
            <button type="button" class="advanced-toggle" onclick="toggleAdvanced()">
                <span id="toggle-icon">▶</span>
                <span id="toggle-text">Show More Options</span>
            </button>

            <div id="advanced-options" class="advanced-options">
                <!-- Start Date -->
                <div class="form-group">
                    <label for="start_date">
                        Start Date
                        <span class="optional">(Optional)</span>
                    </label>
                    <span class="help-text">When do you plan to start working on this?</span>
                    <input
                        type="datetime-local"
                        id="start_date"
                        name="start_date"
                    >
                </div>

                <!-- Estimated Duration -->
                <div class="form-group">
                    <label for="estimated_duration">
                        Estimated Time
                        <span class="optional">(Optional)</span>
                    </label>
                    <span class="help-text">How long do you think this will take? (in minutes)</span>
                    <input
                        type="number"
                        id="estimated_duration"
                        name="estimated_duration"
                        placeholder="e.g., 30, 60, 120"
                        min="1"
                        max="1440"
                        aria-describedby="duration-help"
                    >
                    <div id="duration-validation" class="validation-message" role="alert" aria-live="polite"></div>
                </div>

                <!-- Tags -->
                <div class="form-group">
                    <label for="tags">
                        Tags
                        <span class="optional">(Optional)</span>
                    </label>
                    <span class="help-text">Add tags to organize your tasks (comma-separated, max 10)</span>
                    <input
                        type="text"
                        id="tags"
                        name="tags"
                        placeholder="e.g., documentation, urgent, project-x"
                        aria-describedby="tags-help"
                    >
                    <div id="tags-validation" class="validation-message" role="alert" aria-live="polite"></div>
                </div>
            </div>

            <!-- Buttons -->
            <div class="button-group">
                <button type="submit" class="btn-primary" id="submitBtn">
                    Create Task
                </button>
                <button type="button" class="btn-secondary" onclick="resetForm()">
                    Cancel
                </button>
            </div>
        </form>
    </div>

    <script>
        // Character counter
        function setupCharCounter(inputId, counterId, maxLength) {
            const input = document.getElementById(inputId);
            const counter = document.getElementById(counterId);

            input.addEventListener('input', () => {
                const length = input.value.length;
                counter.textContent = `${length} / ${maxLength} characters`;

                // Color coding
                counter.classList.remove('warning', 'danger');
                if (length > maxLength * 0.9) {
                    counter.classList.add('danger');
                } else if (length > maxLength * 0.75) {
                    counter.classList.add('warning');
                }
            });
        }

        setupCharCounter('title', 'title-counter', 200);
        setupCharCounter('description', 'description-counter', 5000);

        // Title validation
        const titleInput = document.getElementById('title');
        const titleValidation = document.getElementById('title-validation');

        function validateTitle() {
            const value = titleInput.value.trim();

            titleInput.classList.remove('input-valid', 'input-invalid');
            titleValidation.innerHTML = '';

            if (value.length === 0) {
                return false;
            } else if (value.length < 3) {
                titleInput.classList.add('input-invalid');
                titleValidation.className = 'validation-message error';
                titleValidation.innerHTML = '✗ Title must be at least 3 characters long';
                return false;
            } else {
                titleInput.classList.add('input-valid');
                titleValidation.className = 'validation-message success';
                titleValidation.innerHTML = '✓ Looks good!';
                return true;
            }
        }

        titleInput.addEventListener('blur', validateTitle);
        titleInput.addEventListener('input', () => {
            if (titleInput.value.length >= 3) {
                validateTitle();
            }
        });

        // Due date validation
        const dueDateInput = document.getElementById('due_date');
        const dueDateValidation = document.getElementById('due-date-validation');

        dueDateInput.addEventListener('change', () => {
            dueDateValidation.innerHTML = '';
            dueDateInput.classList.remove('input-invalid', 'input-valid');

            if (dueDateInput.value) {
                const selected = new Date(dueDateInput.value);
                const now = new Date();

                if (selected < now) {
                    dueDateInput.classList.add('input-invalid');
                    dueDateValidation.className = 'validation-message warning';
                    dueDateValidation.innerHTML = '⚠ This date is in the past. Did you mean a future date?';
                } else {
                    dueDateInput.classList.add('input-valid');
                    dueDateValidation.className = 'validation-message success';
                    dueDateValidation.innerHTML = '✓ Due date set';
                }
            }
        });

        // Toggle advanced options
        function toggleAdvanced() {
            const options = document.getElementById('advanced-options');
            const icon = document.getElementById('toggle-icon');
            const text = document.getElementById('toggle-text');

            options.classList.toggle('show');

            if (options.classList.contains('show')) {
                icon.textContent = '▼';
                text.textContent = 'Show Fewer Options';
            } else {
                icon.textContent = '▶';
                text.textContent = 'Show More Options';
            }
        }

        // Form submission
        document.getElementById('taskForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            // Validate title
            if (!validateTitle()) {
                titleInput.focus();
                return;
            }

            // Disable submit button
            const submitBtn = document.getElementById('submitBtn');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating...';

            // Simulate API call
            setTimeout(() => {
                alert('Task created successfully!');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Create Task';
            }, 1000);
        });

        // Reset form
        function resetForm() {
            if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
                window.location.href = '/tasks';
            }
        }
    </script>
</body>
</html>
```

---

## 2. Error Display

### Inline Field Errors

```html
<style>
    .error-summary {
        background-color: #FEE2E2;
        border-left: 4px solid #DC2626;
        padding: 1rem;
        margin-bottom: 1.5rem;
        border-radius: 4px;
    }

    .error-summary h3 {
        color: #991B1B;
        margin-top: 0;
        margin-bottom: 0.5rem;
    }

    .error-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .error-list li {
        color: #7F1D1D;
        padding: 0.25rem 0;
    }

    .error-list a {
        color: #DC2626;
        text-decoration: underline;
    }
</style>

<!-- Error Summary at Top of Form -->
<div class="error-summary" role="alert">
    <h3>Please fix the following errors:</h3>
    <ul class="error-list">
        <li><a href="#title">Title is required and cannot be empty</a></li>
        <li><a href="#due_date">The due date must be in the future</a></li>
        <li><a href="#tags">Tag 'urgent!' contains invalid characters</a></li>
    </ul>
</div>
```

---

## 3. Loading States

### Spinner with Progress

```html
<style>
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }

    .loading-card {
        background: white;
        padding: 2rem;
        border-radius: 8px;
        text-align: center;
        max-width: 400px;
    }

    .spinner {
        border: 4px solid #E5E7EB;
        border-top: 4px solid #3B82F6;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        animation: spin 1s linear infinite;
        margin: 0 auto 1rem;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .progress-bar {
        width: 100%;
        height: 8px;
        background: #E5E7EB;
        border-radius: 4px;
        overflow: hidden;
        margin: 1rem 0;
    }

    .progress-fill {
        height: 100%;
        background: #3B82F6;
        transition: width 0.3s ease;
    }
</style>

<div class="loading-overlay" role="alert" aria-live="polite" aria-label="Loading">
    <div class="loading-card">
        <div class="spinner" aria-hidden="true"></div>
        <h3>Syncing with Google Calendar...</h3>
        <div class="progress-bar">
            <div class="progress-fill" style="width: 60%"></div>
        </div>
        <p>Fetched 45 of 75 events</p>
        <p style="color: #6B7280; font-size: 0.875rem;">
            Estimated time remaining: 10 seconds
        </p>
    </div>
</div>
```

---

## 4. Success Feedback

### Toast Notification

```html
<style>
    .toast {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        gap: 1rem;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
        z-index: 9999;
    }

    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    .toast.success {
        border-left: 4px solid #10B981;
    }

    .toast-icon {
        font-size: 1.5rem;
    }

    .toast-close {
        margin-left: auto;
        background: none;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        color: #6B7280;
    }
</style>

<div class="toast success" role="alert" aria-live="polite">
    <span class="toast-icon" aria-hidden="true">✓</span>
    <div>
        <strong>Task Created!</strong>
        <p style="margin: 0.25rem 0 0; color: #6B7280; font-size: 0.875rem;">
            "Complete documentation" has been added to your task list.
        </p>
    </div>
    <button class="toast-close" aria-label="Close notification">×</button>
</div>
```

---

## 5. Empty States

### No Tasks View

```html
<style>
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: #6B7280;
    }

    .empty-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }

    .empty-state h2 {
        color: #374151;
        margin-bottom: 0.5rem;
    }

    .empty-actions {
        margin-top: 2rem;
        display: flex;
        gap: 1rem;
        justify-content: center;
        flex-wrap: wrap;
    }
</style>

<div class="empty-state">
    <div class="empty-icon" aria-hidden="true">📋</div>
    <h2>No Tasks Yet</h2>
    <p>Get started by creating your first task!</p>

    <div class="empty-actions">
        <button class="btn-primary">
            + Create Your First Task
        </button>
        <button class="btn-secondary">
            🗓️ Connect Calendar
        </button>
    </div>

    <p style="margin-top: 2rem; font-size: 0.875rem;">
        Need help? Check out our
        <a href="/guide">Quick Start Guide</a>
    </p>
</div>
```

---

## 6. Accessibility Examples

### Accessible Form with ARIA

```html
<form aria-labelledby="form-title">
    <h2 id="form-title">Create New Task</h2>

    <div class="form-group">
        <label for="task-title" id="title-label">
            Task Title
            <abbr title="required" aria-label="required">*</abbr>
        </label>
        <input
            type="text"
            id="task-title"
            name="title"
            required
            aria-required="true"
            aria-labelledby="title-label"
            aria-describedby="title-help title-error"
            aria-invalid="false"
        >
        <span id="title-help" class="help-text">
            A clear, concise name for your task
        </span>
        <span id="title-error" class="validation-message error" role="alert" aria-live="polite">
            <!-- Error message inserted here -->
        </span>
    </div>

    <!-- Live region for form status -->
    <div role="status" aria-live="polite" aria-atomic="true" class="sr-only">
        <!-- Screen reader announcements -->
    </div>
</form>

<style>
    /* Screen reader only class */
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border-width: 0;
    }
</style>
```

---

## Document Control

- **Version**: 1.0
- **Created**: 2025-10-06
- **Author**: Time Agent 5
- **Purpose**: UI implementation examples for usability requirements
