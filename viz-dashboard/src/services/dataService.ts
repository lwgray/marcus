/**
 * Data Service for Marcus Visualization Dashboard
 *
 * Handles fetching data from the Marcus backend API.
 * Supports both live data from the API and fallback to mock data.
 */

import { SimulationData } from '../data/mockDataGenerator';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Fetch all simulation data from the backend API
 */
export async function fetchSimulationData(projectId?: string): Promise<SimulationData> {
  try {
    const url = projectId
      ? `${API_BASE_URL}/api/data?project_id=${projectId}`
      : `${API_BASE_URL}/api/data`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Loaded data from API:', data);
    return data as SimulationData;
  } catch (error) {
    console.error('Error fetching simulation data:', error);
    throw error;
  }
}

/**
 * Fetch only tasks from the backend API
 */
export async function fetchTasks(projectId?: string) {
  try {
    const url = projectId
      ? `${API_BASE_URL}/api/tasks?project_id=${projectId}`
      : `${API_BASE_URL}/api/tasks`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.tasks;
  } catch (error) {
    console.error('Error fetching tasks:', error);
    throw error;
  }
}

/**
 * Fetch only agents from the backend API
 */
export async function fetchAgents(projectId?: string) {
  try {
    const url = projectId
      ? `${API_BASE_URL}/api/agents?project_id=${projectId}`
      : `${API_BASE_URL}/api/agents`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.agents;
  } catch (error) {
    console.error('Error fetching agents:', error);
    throw error;
  }
}

/**
 * Fetch only messages from the backend API
 */
export async function fetchMessages() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/messages`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.messages;
  } catch (error) {
    console.error('Error fetching messages:', error);
    throw error;
  }
}

/**
 * Fetch only events from the backend API
 */
export async function fetchEvents() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/events`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.events;
  } catch (error) {
    console.error('Error fetching events:', error);
    throw error;
  }
}

/**
 * Fetch metadata from the backend API
 */
export async function fetchMetadata(projectId?: string) {
  try {
    const url = projectId
      ? `${API_BASE_URL}/api/metadata?project_id=${projectId}`
      : `${API_BASE_URL}/api/metadata`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.metadata;
  } catch (error) {
    console.error('Error fetching metadata:', error);
    throw error;
  }
}

/**
 * Check if the backend API is available
 */
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });

    return response.ok;
  } catch (error) {
    console.warn('API health check failed:', error);
    return false;
  }
}
