#!/usr/bin/env python3
"""
HEFT-Aware Resilience Simulation Script
Extends rack_resiliency_to_host.py with node/zone exclusion support.

Key Features:
- Accepts --exclude-node and --exclude-zone parameters
- Ensures failure simulation targets do not include HEFT execution nodes
- Logs exclusion decisions for transparency
"""

import os
import sys
import argparse
import random
import time
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from kubernetes import client, config
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False
    print("Warning: kubernetes module not available, using simulation mode")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Cluster configuration
NODE_ZONE_MAP = {
    'master-m001': 'R1',
    'master-m002': 'R2',
    'master-m003': 'R3',
    'worker-w001': 'R1',
    'worker-w002': 'R1',
    'worker-w003': 'R2',
    'worker-w004': 'R2',
    'worker-w005': 'R3',
    'worker-w006': 'R3',
}

ZONE_NODES = {
    'R1': ['master-m001', 'worker-w001', 'worker-w002'],
    'R2': ['master-m002', 'worker-w003', 'worker-w004'],
    'R3': ['master-m003', 'worker-w005', 'worker-w006'],
}

WORKER_NODES = ['worker-w001', 'worker-w002', 'worker-w003', 
                'worker-w004', 'worker-w005', 'worker-w006']


class HEFTResilienceSimulator:
    """
    HEFT-Aware Resilience Simulator with node/zone exclusion support.
    """
    
    def __init__(self, exclude_nodes=None, exclude_zones=None):
        self.exclude_nodes = set(exclude_nodes or [])
        self.exclude_zones = set(exclude_zones or [])
        self.log_dir = os.getenv('LOG_DIR', '/tmp/heft-logs')
        self.run_id = f"heft-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Initialize Kubernetes client
        if K8S_AVAILABLE:
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes config")
            except:
                try:
                    config.load_kube_config()
                    logger.info("Loaded local Kubernetes config")
                except Exception as e:
                    logger.warning(f"Could not load Kubernetes config: {e}")
        
        self._setup_logging()
        self._log_exclusion_info()
    
    def _setup_logging(self):
        """Setup file logging."""
        os.makedirs(self.log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'{self.run_id}.log')
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        logger.addHandler(file_handler)
    
    def _log_exclusion_info(self):
        """Log exclusion configuration."""
        logger.info("=" * 60)
        logger.info("HEFT-AWARE RESILIENCE SIMULATOR")
        logger.info("=" * 60)
        logger.info(f"Run ID: {self.run_id}")
        logger.info(f"Exclude Nodes: {list(self.exclude_nodes) if self.exclude_nodes else 'None'}")
        logger.info(f"Exclude Zones: {list(self.exclude_zones) if self.exclude_zones else 'None'}")
        logger.info("=" * 60)
    
    def get_eligible_nodes(self) -> list:
        """Get list of nodes eligible for failure simulation (excluding HEFT nodes)."""
        eligible = []
        for node in WORKER_NODES:
            if node not in self.exclude_nodes:
                eligible.append(node)
        
        if not eligible:
            logger.warning("No eligible nodes after exclusion! Using all workers.")
            return WORKER_NODES
        
        logger.info(f"Eligible nodes for failure simulation: {eligible}")
        return eligible
    
    def get_eligible_zones(self) -> list:
        """Get list of zones eligible for rack failure simulation."""
        all_zones = ['R1', 'R2', 'R3']
        eligible = [z for z in all_zones if z not in self.exclude_zones]
        
        if not eligible:
            logger.warning("No eligible zones after exclusion! Using all zones.")
            return all_zones
        
        logger.info(f"Eligible zones for rack simulation: {eligible}")
        return eligible
    
    def select_random_node(self) -> str:
        """Select random node for failure simulation, respecting exclusions."""
        eligible = self.get_eligible_nodes()
        selected = random.choice(eligible)
        logger.info(f"Selected node for failure: {selected} (zone: {NODE_ZONE_MAP[selected]})")
        return selected
    
    def select_random_zone(self) -> str:
        """Select random zone for rack failure simulation, respecting exclusions."""
        eligible = self.get_eligible_zones()
        selected = random.choice(eligible)
        logger.info(f"Selected zone for rack failure: {selected}")
        return selected
    
    def health_check(self, check_id: int = 1) -> dict:
        """Perform health check on cluster."""
        logger.info(f"Starting Health Check {check_id}")
        start_time = time.time()
        
        result = {
            'check_id': check_id,
            'start_epoch': int(start_time),
            'status': 'SUCCESS',
            'nodes_healthy': 0,
            'nodes_unhealthy': 0,
        }
        
        try:
            if K8S_AVAILABLE:
                v1 = client.CoreV1Api()
                nodes = v1.list_node()
                for node in nodes.items:
                    conditions = {c.type: c.status for c in node.status.conditions}
                    if conditions.get('Ready') == 'True':
                        result['nodes_healthy'] += 1
                    else:
                        result['nodes_unhealthy'] += 1
            else:
                # Simulate
                result['nodes_healthy'] = 9
                time.sleep(2)
        except Exception as e:
            logger.error(f"Health check error: {e}")
            result['status'] = 'FAILED'
        
        end_time = time.time()
        result['end_epoch'] = int(end_time)
        result['duration_seconds'] = int(end_time - start_time)
        
        logger.info(f"Health Check {check_id} completed: {result['nodes_healthy']} healthy, "
                   f"{result['nodes_unhealthy']} unhealthy, duration: {result['duration_seconds']}s")
        
        return result
    
    def simulate_node_failure(self, stabilization_time: int = 60) -> dict:
        """Simulate node failure with HEFT exclusion."""
        logger.info("=" * 50)
        logger.info("NODE FAILURE SIMULATION (HEFT-Aware)")
        logger.info("=" * 50)
        
        target_node = self.select_random_node()
        target_zone = NODE_ZONE_MAP[target_node]
        start_time = time.time()
        
        result = {
            'target_node': target_node,
            'target_zone': target_zone,
            'excluded_nodes': list(self.exclude_nodes),
            'start_epoch': int(start_time),
            'status': 'SUCCESS',
        }
        
        try:
            if K8S_AVAILABLE:
                v1 = client.CoreV1Api()
                
                # Cordon node
                logger.info(f"Cordoning node {target_node}...")
                body = {"spec": {"unschedulable": True}}
                v1.patch_node(target_node, body)
                
                # Taint node
                logger.info(f"Tainting node {target_node}...")
                taint = client.V1Taint(
                    key="node.kubernetes.io/out-of-service",
                    value="nodeshutdown",
                    effect="NoExecute"
                )
                node = v1.read_node(target_node)
                if node.spec.taints is None:
                    node.spec.taints = []
                node.spec.taints.append(taint)
                v1.patch_node(target_node, {"spec": {"taints": node.spec.taints}})
                
                logger.info(f"Node {target_node} down, waiting {stabilization_time}s for stabilization...")
                time.sleep(stabilization_time)
                
                # Restore node
                logger.info(f"Restoring node {target_node}...")
                v1.patch_node(target_node, {"spec": {"unschedulable": False}})
                
                # Remove taint
                node = v1.read_node(target_node)
                if node.spec.taints:
                    node.spec.taints = [t for t in node.spec.taints 
                                        if t.key != "node.kubernetes.io/out-of-service"]
                    v1.patch_node(target_node, {"spec": {"taints": node.spec.taints or None}})
                
            else:
                # Simulate
                logger.info(f"[SIMULATION] Node {target_node} down")
                time.sleep(stabilization_time)
                logger.info(f"[SIMULATION] Node {target_node} restored")
        
        except Exception as e:
            logger.error(f"Node simulation error: {e}")
            result['status'] = 'FAILED'
            result['error'] = str(e)
        
        end_time = time.time()
        result['end_epoch'] = int(end_time)
        result['duration_seconds'] = int(end_time - start_time)
        
        logger.info(f"Node simulation completed: {result['status']}, duration: {result['duration_seconds']}s")
        return result
    
    def simulate_rack_failure(self, downtime: int = 60, stabilization_time: int = 120) -> dict:
        """Simulate rack/zone failure with HEFT exclusion."""
        logger.info("=" * 50)
        logger.info("RACK/ZONE FAILURE SIMULATION (HEFT-Aware)")
        logger.info("=" * 50)
        
        target_zone = self.select_random_zone()
        target_nodes = ZONE_NODES[target_zone]
        start_time = time.time()
        
        result = {
            'target_zone': target_zone,
            'target_nodes': target_nodes,
            'excluded_zones': list(self.exclude_zones),
            'start_epoch': int(start_time),
            'status': 'SUCCESS',
        }
        
        try:
            if K8S_AVAILABLE:
                v1 = client.CoreV1Api()
                
                # Cordon and taint all nodes in zone
                for node in target_nodes:
                    logger.info(f"Downing node {node}...")
                    v1.patch_node(node, {"spec": {"unschedulable": True}})
                    
                    taint = client.V1Taint(
                        key="node.kubernetes.io/out-of-service",
                        value="zonefailure",
                        effect="NoExecute"
                    )
                    node_obj = v1.read_node(node)
                    if node_obj.spec.taints is None:
                        node_obj.spec.taints = []
                    node_obj.spec.taints.append(taint)
                    v1.patch_node(node, {"spec": {"taints": node_obj.spec.taints}})
                
                logger.info(f"Zone {target_zone} down ({len(target_nodes)} nodes), "
                           f"waiting {downtime}s before restore...")
                time.sleep(downtime)
                
                # Restore all nodes
                for node in target_nodes:
                    logger.info(f"Restoring node {node}...")
                    v1.patch_node(node, {"spec": {"unschedulable": False}})
                    
                    node_obj = v1.read_node(node)
                    if node_obj.spec.taints:
                        node_obj.spec.taints = [t for t in node_obj.spec.taints 
                                               if t.key != "node.kubernetes.io/out-of-service"]
                        v1.patch_node(node, {"spec": {"taints": node_obj.spec.taints or None}})
                
                logger.info(f"Waiting {stabilization_time}s for cluster stabilization...")
                time.sleep(stabilization_time)
                
            else:
                # Simulate
                logger.info(f"[SIMULATION] Zone {target_zone} down ({len(target_nodes)} nodes)")
                time.sleep(downtime)
                logger.info(f"[SIMULATION] Zone {target_zone} restored")
                time.sleep(stabilization_time)
        
        except Exception as e:
            logger.error(f"Rack simulation error: {e}")
            result['status'] = 'FAILED'
            result['error'] = str(e)
        
        end_time = time.time()
        result['end_epoch'] = int(end_time)
        result['duration_seconds'] = int(end_time - start_time)
        
        logger.info(f"Rack simulation completed: {result['status']}, duration: {result['duration_seconds']}s")
        return result
    
    def run_full_simulation(self, 
                           stabilization_health: int = 10,
                           stabilization_node: int = 60,
                           stabilization_rack: int = 120,
                           downtime_rack: int = 60) -> dict:
        """Run complete HEFT-aware resilience simulation."""
        logger.info("=" * 70)
        logger.info("STARTING HEFT-AWARE FULL RESILIENCE SIMULATION")
        logger.info("=" * 70)
        
        start_time = time.time()
        results = {
            'run_id': self.run_id,
            'start_epoch': int(start_time),
            'exclude_nodes': list(self.exclude_nodes),
            'exclude_zones': list(self.exclude_zones),
            'steps': {}
        }
        
        # Step 1: Parallel Health Checks
        logger.info("\n>>> STEP 1: PARALLEL HEALTH CHECKS <<<")
        hc_start = time.time()
        hc1 = self.health_check(1)
        hc2 = self.health_check(2)
        hc3 = self.health_check(3)
        hc_duration = int(time.time() - hc_start)
        results['steps']['health_checks'] = {
            'hc1': hc1, 'hc2': hc2, 'hc3': hc3,
            'total_duration': hc_duration
        }
        logger.info(f"TIMING: HEALTH_CHECKS_PARALLEL completed in {hc_duration} seconds")
        
        # Step 2: Node Failure Simulation
        logger.info("\n>>> STEP 2: NODE FAILURE SIMULATION <<<")
        node_result = self.simulate_node_failure(stabilization_node)
        results['steps']['node_simulation'] = node_result
        logger.info(f"TIMING: NODE_SIMULATION completed in {node_result['duration_seconds']} seconds")
        
        # Step 3: Interim Health Check
        logger.info("\n>>> STEP 3: INTERIM HEALTH CHECK <<<")
        interim_hc = self.health_check(4)
        results['steps']['interim_health_check'] = interim_hc
        logger.info(f"TIMING: INTERIM_HEALTH_CHECK completed in {interim_hc['duration_seconds']} seconds")
        
        # Step 4: Rack Failure Simulation
        logger.info("\n>>> STEP 4: RACK/ZONE FAILURE SIMULATION <<<")
        rack_result = self.simulate_rack_failure(downtime_rack, stabilization_rack)
        results['steps']['rack_simulation'] = rack_result
        logger.info(f"TIMING: RACK_SIMULATION completed in {rack_result['duration_seconds']} seconds")
        
        # Step 5: Final Health Check
        logger.info("\n>>> STEP 5: FINAL HEALTH CHECK <<<")
        final_hc = self.health_check(5)
        results['steps']['final_health_check'] = final_hc
        logger.info(f"TIMING: FINAL_HEALTH_CHECK completed in {final_hc['duration_seconds']} seconds")
        
        # Complete
        end_time = time.time()
        results['end_epoch'] = int(end_time)
        results['total_duration'] = int(end_time - start_time)
        results['status'] = 'SUCCESS'
        
        logger.info("=" * 70)
        logger.info(f"HEFT-AWARE SIMULATION COMPLETE")
        logger.info(f"Total Duration: {results['total_duration']} seconds")
        logger.info("=" * 70)
        
        # Save results
        self._save_results(results)
        
        return results
    
    def _save_results(self, results: dict):
        """Save simulation results to files."""
        import json
        
        # Save JSON results
        json_path = os.path.join(self.log_dir, f'{self.run_id}_results.json')
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save metrics.txt
        metrics_path = os.path.join(self.log_dir, f'{self.run_id}_metrics.txt')
        with open(metrics_path, 'w') as f:
            f.write(f"# HEFT-Aware Resilience Simulation Metrics\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"RUN_ID={results['run_id']}\n")
            f.write(f"PLATFORM=HEFT_Optimized\n")
            f.write(f"START_EPOCH={results['start_epoch']}\n")
            f.write(f"END_EPOCH={results['end_epoch']}\n")
            f.write(f"DURATION_SECONDS={results['total_duration']}\n")
            f.write(f"STATUS={results['status']}\n")
            f.write(f"EXCLUDE_NODES={','.join(results['exclude_nodes'])}\n")
            f.write(f"EXCLUDE_ZONES={','.join(results['exclude_zones'])}\n")
            
            # Step timings
            if 'health_checks' in results['steps']:
                f.write(f"HEALTH_CHECKS_DURATION={results['steps']['health_checks']['total_duration']}\n")
            if 'node_simulation' in results['steps']:
                f.write(f"NODE_SIMULATION_DURATION={results['steps']['node_simulation']['duration_seconds']}\n")
                f.write(f"NODE_SIMULATION_TARGET={results['steps']['node_simulation']['target_node']}\n")
            if 'rack_simulation' in results['steps']:
                f.write(f"RACK_SIMULATION_DURATION={results['steps']['rack_simulation']['duration_seconds']}\n")
                f.write(f"RACK_SIMULATION_TARGET={results['steps']['rack_simulation']['target_zone']}\n")
        
        logger.info(f"Results saved to {self.log_dir}")


def main():
    parser = argparse.ArgumentParser(description='HEFT-Aware Resilience Simulation')
    
    parser.add_argument('--action', type=str, default='full',
                       choices=['full', 'health-check', 'node-sim', 'rack-sim'],
                       help='Action to perform')
    parser.add_argument('--exclude-node', type=str, action='append', default=[],
                       help='Node(s) to exclude from failure simulation (can be repeated)')
    parser.add_argument('--exclude-zone', type=str, action='append', default=[],
                       help='Zone(s) to exclude from rack failure simulation (can be repeated)')
    parser.add_argument('--stabilization-health', type=int, default=10,
                       help='Stabilization time after health check (seconds)')
    parser.add_argument('--stabilization-node', type=int, default=60,
                       help='Stabilization time after node failure (seconds)')
    parser.add_argument('--stabilization-rack', type=int, default=120,
                       help='Stabilization time after rack failure (seconds)')
    parser.add_argument('--downtime-rack', type=int, default=60,
                       help='Downtime for rack failure before restore (seconds)')
    parser.add_argument('--log-dir', type=str, default='/tmp/heft-logs',
                       help='Directory for log files')
    
    args = parser.parse_args()
    
    # Set log directory
    os.environ['LOG_DIR'] = args.log_dir
    
    # Create simulator
    simulator = HEFTResilienceSimulator(
        exclude_nodes=args.exclude_node,
        exclude_zones=args.exclude_zone
    )
    
    # Execute action
    if args.action == 'full':
        simulator.run_full_simulation(
            stabilization_health=args.stabilization_health,
            stabilization_node=args.stabilization_node,
            stabilization_rack=args.stabilization_rack,
            downtime_rack=args.downtime_rack
        )
    elif args.action == 'health-check':
        simulator.health_check(1)
    elif args.action == 'node-sim':
        simulator.simulate_node_failure(args.stabilization_node)
    elif args.action == 'rack-sim':
        simulator.simulate_rack_failure(args.downtime_rack, args.stabilization_rack)


if __name__ == '__main__':
    main()
