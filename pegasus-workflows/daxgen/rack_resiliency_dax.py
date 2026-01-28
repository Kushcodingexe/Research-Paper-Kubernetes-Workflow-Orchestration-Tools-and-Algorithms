#!/usr/bin/env python3
"""
Rack Resiliency DAX Generator - Montage Pattern
Generates Pegasus DAX workflow for rack resiliency simulation using Montage-style patterns.

Montage Pattern Mapping:
  mProjectPP    → health-check (parallel projection)
  mDiff         → node-failure-sim (difference computation)
  mFitPlane     → interim-health-check (plane fitting)
  mBackground   → rack-failure-sim (background correction)
  mImgtbl       → final-health-check (catalog generation)
"""

import os
import sys
from datetime import datetime
from Pegasus.api import (
    Workflow,
    Job,
    File,
    Transformation,
    TransformationSite,
    TransformationCatalog,
    SiteCatalog,
    Site,
    Directory,
    FileServer,
    Operation,
    ReplicaCatalog,
    Properties,
)


class RackResiliencyDAXGenerator:
    """
    Generates Pegasus DAX workflows for rack resiliency simulation.
    Supports different scales (1x, 2x, 4x) and job clustering.
    """
    
    SCALE_CONFIGS = {
        '1x': {
            'health_checks': 3,
            'node_sims': 1,
            'interim_checks': 1,
            'rack_sims': 1,
            'final_checks': 1,
        },
        '2x': {
            'health_checks': 6,
            'node_sims': 2,
            'interim_checks': 2,
            'rack_sims': 2,
            'final_checks': 2,
        },
        '4x': {
            'health_checks': 12,
            'node_sims': 4,
            'interim_checks': 4,
            'rack_sims': 4,
            'final_checks': 4,
        },
    }
    
    # Montage-style transformation names
    TRANSFORMATIONS = {
        'health_check': 'rack_resiliency::health-check:1.0',
        'node_sim': 'rack_resiliency::node-failure-sim:1.0',
        'rack_sim': 'rack_resiliency::rack-failure-sim:1.0',
    }
    
    def __init__(self, scale='1x', cluster_factor=1, output_dir='.'):
        """
        Initialize DAX generator.
        
        Args:
            scale: Workflow scale ('1x', '2x', '4x')
            cluster_factor: Job clustering factor (1=no clustering, 10=cluster 10 jobs)
            output_dir: Output directory for generated files
        """
        self.scale = scale
        self.cluster_factor = cluster_factor
        self.output_dir = output_dir
        self.config = self.SCALE_CONFIGS.get(scale, self.SCALE_CONFIGS['1x'])
        
        self.wf = None
        self.tc = None
        self.sc = None
        self.rc = None
        
    def create_transformation_catalog(self):
        """Create transformation catalog defining available executables."""
        self.tc = TransformationCatalog()
        
        # Use actual path on Linux system
        sim_script = '/home/snu/kubernetes/Automation_Scripts/rack_resiliency_to_host.py'
        
        # Health check transformation - use add_sites for multiple site support
        health_check = Transformation(
            'health-check',
            namespace='rack_resiliency',
            version='1.0',
            site='local',
            pfn=sim_script,
            is_stageable=False
        )
        health_check.add_profiles(Namespace.PEGASUS, key='clusters.size', value=self.cluster_factor)
        health_check.add_sites(
            TransformationSite('condorpool', sim_script, is_stageable=False)
        )
        
        # Node failure simulation
        node_sim = Transformation(
            'node-failure-sim',
            namespace='rack_resiliency',
            version='1.0',
            site='local',
            pfn=sim_script,
            is_stageable=False
        )
        node_sim.add_sites(
            TransformationSite('condorpool', sim_script, is_stageable=False)
        )
        
        # Rack failure simulation
        rack_sim = Transformation(
            'rack-failure-sim',
            namespace='rack_resiliency',
            version='1.0',
            site='local',
            pfn=sim_script,
            is_stageable=False
        )
        rack_sim.add_sites(
            TransformationSite('condorpool', sim_script, is_stageable=False)
        )
        
        self.tc.add_transformations(health_check, node_sim, rack_sim)
        
        return self.tc
    
    def create_site_catalog(self, exec_site='local'):
        """Create site catalog defining execution sites."""
        self.sc = SiteCatalog()
        
        # Scratch and output directories
        scratch_dir = '/tmp/pegasus-scratch'
        output_dir = '/home/snu/kubernetes/comparison-logs/pegasus-output'
        
        # Local site (run jobs using condor local universe)
        local = Site('local', arch=Arch.X86_64, os_type=OS.LINUX)
        local.add_directories(
            Directory(Directory.SHARED_SCRATCH, scratch_dir)
                .add_file_servers(FileServer(f'file://{scratch_dir}', Operation.ALL)),
            Directory(Directory.LOCAL_STORAGE, output_dir)
                .add_file_servers(FileServer(f'file://{output_dir}', Operation.ALL))
        )
        # Use condor style with local universe for local execution
        local.add_profiles(Namespace.PEGASUS, key='style', value='condor')
        local.add_profiles(Namespace.CONDOR, key='universe', value='local')
        local.add_profiles(Namespace.ENV, key='KUBECONFIG', value='/home/snu/kubernetes/kubeconfig-master')
        
        # Condorpool site (for HTCondor vanilla universe - optional)
        condorpool = Site('condorpool', arch=Arch.X86_64, os_type=OS.LINUX)
        condorpool.add_profiles(Namespace.PEGASUS, key='style', value='condor')
        condorpool.add_profiles(Namespace.CONDOR, key='universe', value='vanilla')
        condorpool.add_profiles(Namespace.CONDOR, key='requirements', value='True')
        condorpool.add_profiles(Namespace.ENV, key='KUBECONFIG', value='/home/snu/kubernetes/kubeconfig-master')
        
        self.sc.add_sites(local, condorpool)
        
        return self.sc
    
    def create_replica_catalog(self):
        """Create replica catalog for input files."""
        self.rc = ReplicaCatalog()
        
        # Add kubeconfig as input file
        self.rc.add_replica(
            'local',
            File('kubeconfig'),
            '/root/.kube/config'
        )
        
        return self.rc
    
    def create_workflow(self):
        """
        Create the Pegasus workflow DAX using Montage-style pattern.
        
        Workflow Structure (Montage Mapping):
        
        Stage 1: mProjectPP (Parallel Health Checks)
            HC-1, HC-2, HC-3, ... (parallel)
            
        Stage 2: mDiff (Node Failure Simulations) 
            NODE-SIM-1, NODE-SIM-2, ... (depends on HC)
            
        Stage 3: mFitPlane (Interim Health Checks)
            INTERIM-HC-1, ... (depends on NODE-SIM)
            
        Stage 4: mBackground (Rack Failure Simulations)
            RACK-SIM-1, ... (depends on INTERIM-HC)
            
        Stage 5: mImgtbl (Final Health Checks)
            FINAL-HC-1, ... (depends on RACK-SIM)
        """
        
        run_id = f"rack-resiliency-{self.scale}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.wf = Workflow(run_id)
        
        # Input files
        kubeconfig = File('kubeconfig')
        
        # ===== STAGE 1: Parallel Health Checks (mProjectPP pattern) =====
        health_check_jobs = []
        health_check_outputs = []
        
        for i in range(1, self.config['health_checks'] + 1):
            output_file = File(f'health-check-{i}.log')
            health_check_outputs.append(output_file)
            
            job = Job('health-check', namespace='rack_resiliency', version='1.0')
            job.add_args('health-check', '--stabilization-time=10')
            job.add_inputs(kubeconfig)
            job.add_outputs(output_file, stage_out=True)
            job.add_profiles(Namespace.PEGASUS, key='label', value=f'health-check-{i}')
            
            health_check_jobs.append(job)
            self.wf.add_jobs(job)
        
        # ===== STAGE 2: Node Failure Simulations (mDiff pattern) =====
        node_sim_jobs = []
        node_sim_outputs = []
        
        target_nodes = ['worker-w001', 'worker-w002', 'worker-w003', 'worker-w004']
        
        for i in range(1, self.config['node_sims'] + 1):
            output_file = File(f'node-sim-{i}.log')
            node_sim_outputs.append(output_file)
            
            target_node = target_nodes[(i - 1) % len(target_nodes)]
            
            job = Job('node-failure-sim', namespace='rack_resiliency', version='1.0')
            job.add_args('node-failure', target_node, '--stabilization-time=30')
            job.add_inputs(kubeconfig)
            job.add_outputs(output_file, stage_out=True)
            job.add_profiles(Namespace.PEGASUS, key='label', value=f'node-sim-{i}')
            
            # Add job to workflow FIRST
            self.wf.add_jobs(job)
            node_sim_jobs.append(job)
            
            # Then add dependencies: wait for all health checks
            for hc_job in health_check_jobs:
                self.wf.add_dependency(job, parents=[hc_job])
        
        # ===== STAGE 3: Interim Health Checks (mFitPlane pattern) =====
        interim_hc_jobs = []
        interim_hc_outputs = []
        
        for i in range(1, self.config['interim_checks'] + 1):
            output_file = File(f'interim-hc-{i}.log')
            interim_hc_outputs.append(output_file)
            
            job = Job('health-check', namespace='rack_resiliency', version='1.0')
            job.add_args('health-check', '--stabilization-time=10')
            job.add_inputs(kubeconfig)
            job.add_outputs(output_file, stage_out=True)
            job.add_profiles(Namespace.PEGASUS, key='label', value=f'interim-hc-{i}')
            
            # Add job to workflow FIRST
            self.wf.add_jobs(job)
            interim_hc_jobs.append(job)
            
            # Then add dependencies: wait for node simulations
            for ns_job in node_sim_jobs:
                self.wf.add_dependency(job, parents=[ns_job])
        
        # ===== STAGE 4: Rack Failure Simulations (mBackground pattern) =====
        rack_sim_jobs = []
        rack_sim_outputs = []
        
        target_racks = ['R1', 'R2', 'R3']
        
        for i in range(1, self.config['rack_sims'] + 1):
            output_file = File(f'rack-sim-{i}.log')
            rack_sim_outputs.append(output_file)
            
            target_rack = target_racks[(i - 1) % len(target_racks)]
            
            job = Job('rack-failure-sim', namespace='rack_resiliency', version='1.0')
            job.add_args('rack-failure', target_rack, '--stabilization-time=30')
            job.add_inputs(kubeconfig)
            job.add_outputs(output_file, stage_out=True)
            job.add_profiles(Namespace.PEGASUS, key='label', value=f'rack-sim-{i}')
            
            # Add job to workflow FIRST
            self.wf.add_jobs(job)
            rack_sim_jobs.append(job)
            
            # Then add dependencies: wait for interim health checks
            for ihc_job in interim_hc_jobs:
                self.wf.add_dependency(job, parents=[ihc_job])
        
        # ===== STAGE 5: Final Health Checks (mImgtbl pattern) =====
        final_hc_jobs = []
        
        for i in range(1, self.config['final_checks'] + 1):
            output_file = File(f'final-hc-{i}.log')
            
            job = Job('health-check', namespace='rack_resiliency', version='1.0')
            job.add_args('health-check', '--stabilization-time=10')
            job.add_inputs(kubeconfig)
            job.add_outputs(output_file, stage_out=True)
            job.add_profiles(Namespace.PEGASUS, key='label', value=f'final-hc-{i}')
            
            # Add job to workflow FIRST
            self.wf.add_jobs(job)
            final_hc_jobs.append(job)
            
            # Then add dependencies: wait for rack simulations
            for rs_job in rack_sim_jobs:
                self.wf.add_dependency(job, parents=[rs_job])
        
        return self.wf
    
    def get_workflow_stats(self):
        """Get workflow statistics for comparison."""
        total_jobs = (
            self.config['health_checks'] +
            self.config['node_sims'] +
            self.config['interim_checks'] +
            self.config['rack_sims'] +
            self.config['final_checks']
        )
        
        parallel_stages = 5  # HC, NodeSim, InterimHC, RackSim, FinalHC
        max_parallel = max(
            self.config['health_checks'],
            self.config['node_sims'],
            self.config['rack_sims']
        )
        
        return {
            'scale': self.scale,
            'total_jobs': total_jobs,
            'parallel_stages': parallel_stages,
            'max_parallel_jobs': max_parallel,
            'cluster_factor': self.cluster_factor,
            'effective_jobs': total_jobs // self.cluster_factor if self.cluster_factor > 1 else total_jobs,
            'breakdown': self.config,
        }
    
    def write_dax(self, filename=None):
        """Write the DAX workflow to file."""
        if filename is None:
            filename = f'rack-resiliency-{self.scale}.dax'
        
        filepath = os.path.join(self.output_dir, filename)
        self.wf.write(filepath)
        
        print(f"DAX written to: {filepath}")
        return filepath
    
    def write_catalogs(self):
        """Write all catalogs to files."""
        if self.tc:
            tc_path = os.path.join(self.output_dir, 'tc.txt')
            self.tc.write(tc_path)
            print(f"Transformation Catalog: {tc_path}")
        
        if self.sc:
            sc_path = os.path.join(self.output_dir, 'sites.yml')
            self.sc.write(sc_path)
            print(f"Site Catalog: {sc_path}")
        
        if self.rc:
            rc_path = os.path.join(self.output_dir, 'rc.txt')
            self.rc.write(rc_path)
            print(f"Replica Catalog: {rc_path}")


def main():
    """Generate DAX workflows for all scales."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Pegasus DAX for Rack Resiliency')
    parser.add_argument('--scale', choices=['1x', '2x', '4x', 'all'], default='1x',
                        help='Workflow scale')
    parser.add_argument('--cluster', type=int, default=1,
                        help='Job clustering factor')
    parser.add_argument('--output', default='.',
                        help='Output directory')
    parser.add_argument('--stats', action='store_true',
                        help='Print workflow statistics only')
    
    args = parser.parse_args()
    
    scales = ['1x', '2x', '4x'] if args.scale == 'all' else [args.scale]
    
    for scale in scales:
        print(f"\n{'='*60}")
        print(f"Generating {scale} Workflow (Cluster Factor: {args.cluster})")
        print('='*60)
        
        generator = RackResiliencyDAXGenerator(
            scale=scale,
            cluster_factor=args.cluster,
            output_dir=args.output
        )
        
        stats = generator.get_workflow_stats()
        print(f"\nWorkflow Statistics:")
        print(f"  Total Jobs: {stats['total_jobs']}")
        print(f"  Max Parallel: {stats['max_parallel_jobs']}")
        print(f"  Effective Jobs (clustered): {stats['effective_jobs']}")
        print(f"  Breakdown:")
        for stage, count in stats['breakdown'].items():
            print(f"    {stage}: {count}")
        
        if not args.stats:
            generator.create_transformation_catalog()
            generator.create_site_catalog()
            generator.create_replica_catalog()
            generator.create_workflow()
            generator.write_dax()
            generator.write_catalogs()


if __name__ == '__main__':
    # Import Pegasus namespace for profiles
    from Pegasus.api import Namespace, Arch, OS
    main()
