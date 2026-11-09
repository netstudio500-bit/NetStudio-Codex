# NetStudio-Codex API Documentation

## Overview

RESTful API for interacting with NetStudio-Codex agents and system.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints require authentication via Bearer token:

```
Authorization: Bearer <your-token>
```

## Endpoints

### Agents

#### List Agents

```
GET /agents
```

**Response:**
```json
{
  "agents": [
    {
      "id": "agent-1",
      "name": "ResearchAgent",
      "description": "Agent for research tasks"
    }
  ]
}
```

#### Create Agent

```
POST /agents
```

**Request:**
```json
{
  "name": "CodeAgent",
  "description": "Agent for coding tasks",
  "system_prompt": "You are a coding expert"
}
```

#### Execute Task

```
POST /agents/{agent_id}/execute
```

**Request:**
```json
{
  "task": "Write a function to sort a list",
  "context": {}
}
```

**Response:**
```json
{
  "task_id": "task-123",
  "status": "running",
  "result": null
}
```

### Tasks

#### Get Task Status

```
GET /tasks/{task_id}
```

**Response:**
```json
{
  "id": "task-123",
  "status": "completed",
  "result": "The function implementation...",
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:05:00Z"
}
```

### Memory

#### Search Memory

```
GET /memory/search?query=python&limit=10
```

**Response:**
```json
{
  "results": [
    {
      "id": "mem-1",
      "content": "Python is a programming language",
      "similarity": 0.95,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

## WebSocket

Real-time updates via WebSocket:

```
ws://localhost:8001/ws
```

### Events

- `task_started` - Task execution started
- `task_progress` - Task progress update
- `task_completed` - Task execution completed
- `task_error` - Task execution error

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid request parameters",
    "details": {}
  }
}
```

### Status Codes

- `200` - OK
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error
