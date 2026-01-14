#!/usr/bin/env python3
"""
HEFT (Heterogeneous Earliest Finish Time) Scheduler
Implements HEFT algorithm for optimal task-to-node assignment in DAG workflows.

Industry-standard dynamic per-step scheduling for heterogeneous computing.
"""

import json
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# Cluster configuration
NODES = {
    'master-m001': {'zone': 'R1', 'type': 'master', 'capacity': 0.8},
    'master-m002': {'zone': 'R2', 'type': 'master', 'capacity': 0.8},
    'master-m003': {'zone': 'R3', 'type': 'master', 'capacity': 0.8},
    'worker-w001': {'zone': 'R1', 'type': 'worker', 'capacity': 1.0},
    'worker-w002': {'zone': 'R1', 'type': 'worker', 'capacity': 1.0},
    'worker-w003': {'zone': 'R2', 'type': 'worker', 'capacity': 1.0},
    'worker-w004': {'zone': 'R2', 'type': 'worker', 'capacity': 1.0},
    'worker-w005': {'zone': 'R3', 'type': 'worker', 'capacity': 1.0},
    'worker-w006': {'zone': 'R3', 'type': 'worker', 'capacity': 1.0},
}

# Communication costs between zones (in seconds)
COMM_COSTS = {
    ('R1', 'R1'): 0.1,
    ('R2', 'R2'): 0.1,
    ('R3', 'R3'): 0.1,
    ('R1', 'R2'): 1.5,
    ('R2', 'R1'): 1.5,
    ('R1', 'R3'): 2.0,
    ('R3', 'R1'): 2.0,
    ('R2', 'R3'): 1.5,
    ('R3', 'R2'): 1.5,
}

# Average execution costs per task type (from benchmark data)
# Format: {task_type: {node_type: avg_duration}}
DEFAULT_EXEC_COSTS = {
    'HEALTH_CHECK': {'master': 35, 'worker': 25},
    'NODE_SIMULATION': {'master': 180, 'worker': 150},
    'RACK_SIMULATION': {'master': 380, 'worker': 350},
    'INTERIM_HEALTH_CHECK': {'master': 30, 'worker': 20},
    'FINAL_HEALTH_CHECK': {'master': 30, 'worker': 20},
    'INITIALIZE': {'master': 15, 'worker': 12},
}


@dataclass
class Task:
    """Represents a task in the DAG."""
    id: str
    task_type: str
    predecessors: List[str]
    successors: List[str]
    upward_rank: float = 0.0
    scheduled_node: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0


class HEFTScheduler:
    """
    HEFT (Heterogeneous Earliest Finish Time) Scheduler.
    
    Algorithm:
    1. Compute upward rank for all tasks (priority based on execution + successors)
    2. Sort tasks by decreasing upward rank
    3. For each task, select node that gives earliest finish time
    """
    
    def __init__(self, exec_costs: Dict = None, comm_costs: Dict = None):
        self.nodes = NODES
        self.exec_costs = exec_costs or DEFAULT_EXEC_COSTS
        self.comm_costs = comm_costs or COMM_COSTS
        self.tasks: Dict[str, Task] = {}
        self.schedule: Dict[str, Tuple[str, float, float]] = {}  # task_id -> (node, start, end)
        self.node_availability: Dict[str, float] = {n: 0.0 for n in NODES}
    
    def load_benchmark_data(self, filepath: str):
        """Load execution costs from benchmark JSON."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Extract average step timings
            for platform, platform_data in data.get('platforms', {}).items():
                step_stats = platform_data.get('step_statistics', {})
                for step, stats in step_stats.items():
                    if stats.get('mean'):
                        task_type = self._normalize_task_type(step)
                        if task_type in self.exec_costs:
                            # Use benchmark mean as worker cost
                            self.exec_costs[task_type]['worker'] = stats['mean']
                            self.exec_costs[task_type]['master'] = stats['mean'] * 1.2
            
            print(f"Loaded execution costs from {filepath}")
        except Exception as e:
            print(f"Warning: Could not load benchmark data: {e}")
    
    def _normalize_task_type(self, step_name: str) -> str:
        """Map step names to task types."""
        step_upper = step_name.upper()
        if 'HEALTH_CHECK_1' in step_upper or 'HEALTH_CHECK_2' in step_upper or 'HEALTH_CHECK_3' in step_upper:
            return 'HEALTH_CHECK'
        elif 'NODE' in step_upper and 'SIM' in step_upper:
            return 'NODE_SIMULATION'
        elif 'RACK' in step_upper and 'SIM' in step_upper:
            return 'RACK_SIMULATION'
        elif 'INTERIM' in step_upper:
            return 'INTERIM_HEALTH_CHECK'
        elif 'FINAL' in step_upper:
            return 'FINAL_HEALTH_CHECK'
        elif 'INIT' in step_upper:
            return 'INITIALIZE'
        return step_name.upper()
    
    def define_dag(self):
        """Define the resilience workflow DAG."""
        # DAG structure for resilience simulation
        dag_def = {
            'initialize': {
                'type': 'INITIALIZE',
                'pred': [],
                'succ': ['health-check-1', 'health-check-2', 'health-check-3']
            },
            'health-check-1': {
                'type': 'HEALTH_CHECK',
                'pred': ['initialize'],
                'succ': ['node-simulation']
            },
            'health-check-2': {
                'type': 'HEALTH_CHECK',
                'pred': ['initialize'],
                'succ': ['node-simulation']
            },
            'health-check-3': {
                'type': 'HEALTH_CHECK',
                'pred': ['initialize'],
                'succ': ['node-simulation']
            },
            'node-simulation': {
                'type': 'NODE_SIMULATION',
                'pred': ['health-check-1', 'health-check-2', 'health-check-3'],
                'succ': ['interim-health-check']
            },
            'interim-health-check': {
                'type': 'INTERIM_HEALTH_CHECK',
                'pred': ['node-simulation'],
                'succ': ['rack-simulation']
            },
            'rack-simulation': {
                'type': 'RACK_SIMULATION',
                'pred': ['interim-health-check'],
                'succ': ['final-health-check']
            },
            'final-health-check': {
                'type': 'FINAL_HEALTH_CHECK',
                'pred': ['rack-simulation'],
                'succ': []
            },
        }
        
        for task_id, info in dag_def.items():
            self.tasks[task_id] = Task(
                id=task_id,
                task_type=info['type'],
                predecessors=info['pred'],
                successors=info['succ']
            )
    
    def get_exec_cost(self, task_type: str, node: str) -> float:
        """Get execution cost for task on node."""
        node_type = self.nodes[node]['type']
        capacity = self.nodes[node]['capacity']
        base_cost = self.exec_costs.get(task_type, {'master': 100, 'worker': 80})
        return base_cost[node_type] / capacity
    
    def get_comm_cost(self, src_node: str, dst_node: str, data_size: float = 1.0) -> float:
        """Get communication cost between nodes."""
        src_zone = self.nodes[src_node]['zone']
        dst_zone = self.nodes[dst_node]['zone']
        return self.comm_costs.get((src_zone, dst_zone), 1.0) * data_size
    
    def compute_upward_rank(self, task_id: str, memo: Dict[str, float] = None) -> float:
        """Compute upward rank recursively for a task."""
        if memo is None:
            memo = {}
        
        if task_id in memo:
            return memo[task_id]
        
        task = self.tasks[task_id]
        
        # Average execution cost across all nodes
        avg_exec = sum(self.get_exec_cost(task.task_type, n) for n in self.nodes) / len(self.nodes)
        
        if not task.successors:
            # Exit task
            rank = avg_exec
        else:
            # Max of (comm_cost + successor rank)
            max_successor_rank = 0
            for succ_id in task.successors:
                succ_rank = self.compute_upward_rank(succ_id, memo)
                avg_comm = sum(self.get_comm_cost(n, n) for n in self.nodes) / len(self.nodes)
                max_successor_rank = max(max_successor_rank, avg_comm + succ_rank)
            rank = avg_exec + max_successor_rank
        
        memo[task_id] = rank
        task.upward_rank = rank
        return rank
    
    def compute_all_ranks(self):
        """Compute upward ranks for all tasks."""
        memo = {}
        for task_id in self.tasks:
            self.compute_upward_rank(task_id, memo)
    
    def get_earliest_finish_time(self, task: Task, node: str) -> Tuple[float, float]:
        """Compute earliest start and finish time for task on node."""
        # Node availability
        node_ready = self.node_availability[node]
        
        # Max predecessor finish time + communication cost
        pred_ready = 0.0
        for pred_id in task.predecessors:
            pred_task = self.tasks[pred_id]
            if pred_task.scheduled_node:
                pred_end = pred_task.end_time
                comm = self.get_comm_cost(pred_task.scheduled_node, node)
                pred_ready = max(pred_ready, pred_end + comm)
        
        start_time = max(node_ready, pred_ready)
        exec_time = self.get_exec_cost(task.task_type, node)
        end_time = start_time + exec_time
        
        return start_time, end_time
    
    def schedule_task(self, task_id: str) -> Tuple[str, float, float]:
        """Schedule a task to the node with earliest finish time."""
        task = self.tasks[task_id]
        
        best_node = None
        best_start = float('inf')
        best_end = float('inf')
        
        for node in self.nodes:
            start, end = self.get_earliest_finish_time(task, node)
            if end < best_end:
                best_node = node
                best_start = start
                best_end = end
        
        # Update task and node availability
        task.scheduled_node = best_node
        task.start_time = best_start
        task.end_time = best_end
        self.node_availability[best_node] = best_end
        
        self.schedule[task_id] = (best_node, best_start, best_end)
        return best_node, best_start, best_end
    
    def run_heft(self) -> Dict[str, Tuple[str, float, float]]:
        """Execute HEFT algorithm."""
        # Step 1: Define DAG
        self.define_dag()
        
        # Step 2: Compute upward ranks
        self.compute_all_ranks()
        
        # Step 3: Sort tasks by decreasing upward rank
        sorted_tasks = sorted(self.tasks.values(), key=lambda t: t.upward_rank, reverse=True)
        
        # Step 4: Schedule each task
        for task in sorted_tasks:
            self.schedule_task(task.id)
        
        return self.schedule
    
    def get_exclusion_info(self, task_id: str = None) -> Dict:
        """
        Get node/zone exclusion info for failure simulation.
        
        If task_id provided, returns exclusion for that specific task.
        Otherwise, returns all scheduled nodes/zones.
        """
        if task_id and task_id in self.schedule:
            node, _, _ = self.schedule[task_id]
            zone = self.nodes[node]['zone']
            return {
                'exclude_node': node,
                'exclude_zone': zone,
            }
        
        # All scheduled nodes
        scheduled_nodes = set(s[0] for s in self.schedule.values())
        scheduled_zones = set(self.nodes[n]['zone'] for n in scheduled_nodes)
        
        return {
            'exclude_nodes': list(scheduled_nodes),
            'exclude_zones': list(scheduled_zones),
        }
    
    def print_schedule(self):
        """Print the computed schedule."""
        print("\n" + "=" * 70)
        print("HEFT SCHEDULE")
        print("=" * 70)
        print(f"{'Task':<25} {'Node':<15} {'Start':>10} {'End':>10} {'Rank':>10}")
        print("-" * 70)
        
        for task_id in sorted(self.schedule.keys(), key=lambda t: self.schedule[t][1]):
            node, start, end = self.schedule[task_id]
            rank = self.tasks[task_id].upward_rank
            zone = self.nodes[node]['zone']
            print(f"{task_id:<25} {node} ({zone}){' '*(15-len(node)-4)} {start:>10.1f} {end:>10.1f} {rank:>10.1f}")
        
        makespan = max(s[2] for s in self.schedule.values())
        print("-" * 70)
        print(f"Makespan: {makespan:.1f}s")
        print("=" * 70)


def main():
    """Test HEFT scheduler."""
    scheduler = HEFTScheduler()
    
    # Optionally load benchmark data
    import sys
    if len(sys.argv) > 1:
        scheduler.load_benchmark_data(sys.argv[1])
    
    # Run HEFT
    schedule = scheduler.run_heft()
    scheduler.print_schedule()
    
    # Get exclusion info
    print("\nExclusion Info for Failure Simulation:")
    exclusion = scheduler.get_exclusion_info()
    print(f"  Exclude Nodes: {exclusion.get('exclude_nodes', [])}")
    print(f"  Exclude Zones: {exclusion.get('exclude_zones', [])}")
    
    # Per-task exclusion
    print("\nPer-Task Execution Nodes:")
    for task_id in sorted(schedule.keys()):
        info = scheduler.get_exclusion_info(task_id)
        print(f"  {task_id}: Run on {info['exclude_node']} (zone {info['exclude_zone']})")


if __name__ == '__main__':
    main()
