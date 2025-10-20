/**
 * Timeline utilities for calculating task states at specific points in time
 */

import { Task, TaskStatus } from '../data/mockDataGenerator';

/**
 * Calculate what state a task should be in at a given time
 */
export function getTaskStateAtTime(task: Task, currentAbsTime: number): {
  status: TaskStatus;
  progress: number;
  isActive: boolean;
} {
  const taskStart = new Date(task.created_at).getTime();
  const taskEnd = new Date(task.updated_at).getTime();
  const taskDuration = taskEnd - taskStart;

  // Before task starts
  if (currentAbsTime < taskStart) {
    return {
      status: TaskStatus.TODO,
      progress: 0,
      isActive: false,
    };
  }

  // After task completes
  if (currentAbsTime >= taskEnd) {
    return {
      status: task.status, // Final status (DONE or BLOCKED)
      progress: task.progress,
      isActive: false,
    };
  }

  // During task execution
  const elapsed = currentAbsTime - taskStart;
  const progressPercent = Math.min(100, (elapsed / taskDuration) * task.progress);

  return {
    status: TaskStatus.IN_PROGRESS,
    progress: Math.round(progressPercent),
    isActive: true,
  };
}

/**
 * Get all tasks with their current states at a given time
 */
export function getTasksAtTime(tasks: Task[], currentAbsTime: number): Array<Task & {
  currentStatus: TaskStatus;
  currentProgress: number;
  isActive: boolean;
}> {
  return tasks.map(task => {
    const state = getTaskStateAtTime(task, currentAbsTime);
    return {
      ...task,
      currentStatus: state.status,
      currentProgress: state.progress,
      isActive: state.isActive,
    };
  });
}
