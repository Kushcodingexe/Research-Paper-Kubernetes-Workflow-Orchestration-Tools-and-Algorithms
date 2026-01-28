#!/usr/bin/env python3
"""
Rack Resiliency DAX Generator for Docker - Simplified Version
Generates Pegasus DAX workflow for running inside Docker container.
"""

import os
import sys
from datetime import datetime
from Pegasus.api import (
    Workflow,
    Job,
    File,
    Transformation,
    TransformationCatalog,
    SiteCatalog,
    Site,
    Directory,
    FileServer,
    Operation,
    ReplicaCatalog,
    Properties,
    Namespace,
    Arch,
    OS,
)


class RackResiliencyDAXGenerator:
    """Generates Pegasus DAX workflows for rack resiliency simulation."""
    
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
    
    def __init__(self, scale='1x', cluster_factor=1, output_dir='.'):
        self.scale = scale
        self.cluster_factor = cluster_factor
        self.output_dir = output_dir
        self.config = self.SCALE_CONFIGS.get(scale, self.SCALE_CONFIGS['1x'])
        
        self.wf = None
        self.tc = None
        self.sc = None
        self.rc = None
        
    def create_transformation_catalog(self):
        """Create transformation catalog with Docker paths."""
        self.tc = TransformationCatalog()
        
        # Path inside Docker container
        sim_script = '/app/simulations/rack_resiliency_sim.py'
        
        # Health check transformation
        health_check = Transformation(
            'health-check',
            namespace='rack_resiliency',
            version='1.0',
            site='local',
            pfn=sim_script,
            is_stageable=False
        )
        health_check.add_profiles(Namespace.PEGASUS, key='clusters.size', value=self.cluster_factor)
        
        # Node failure simulation
        node_sim = Transformation(
            'node-failure-sim',
            namespace='rack_resiliency',
            version='1.0',
            site='local',
            pfn=sim_script,
            is_stageable=False
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
        
        self.tc.add_transformations(health_check, node_sim, rack_sim)
        return self.tc
    
    def create_site_catalog(self):
        """Create site catalog for Docker execution."""
        self.sc = SiteCatalog()
        
        # Local site inside Docker
        local = Site('local', arch=Arch.X86_64, os_type=OS.LINUX)
        local.add_directories(
            Directory(Directory.SHARED_SCRATCH, '/app/scratch')
                .add_file_servers(FileServer('file:///app/scratch', Operation.ALL)),
            Directory(Directory.LOCAL_STORAGE, '/app/output')
                .add_file_servers(FileServer('file:///app/output', Operation.ALL))
        )
        # Use condor local universe
        local.add_profiles(Namespace.PEGASUS, key='style', value='condor')
        local.add_profiles(Namespace.CONDOR, key='universe', value='local')
        
        self.sc.add_sites(local)
        return self.sc
    
    def create_replica_catalog(self):
        """Create replica catalog."""
        self.rc = ReplicaCatalog()
        return self.rc
    
    def create_workflow(self):
        """Create the Pegasus workflow DAX."""
        run_id = f"rack-resiliency-{self.scale}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.wf = Workflow(run_id)
        
        # Stage 1: Health Checks (parallel)
        health_check_jobs = []
        for i in range(1, self.config['health_checks'] + 1):
            output_file = File(f'health-check-{i}.log')
            job = Job('health-check', namespace='rack_resiliency', version='1.0')
            job.add_args('health-check', '--stabilization-time=5')
            job.add_outputs(output_file, stage_out=True)
            self.wf.add_jobs(job)
            health_check_jobs.append(job)
        
        # Stage 2: Node Failure Simulations
        node_sim_jobs = []
        target_nodes = ['worker-w001', 'worker-w002', 'worker-w003', 'worker-w004']
        for i in range(1, self.config['node_sims'] + 1):
            output_file = File(f'node-sim-{i}.log')
            target_node = target_nodes[(i - 1) % len(target_nodes)]
            job = Job('node-failure-sim', namespace='rack_resiliency', version='1.0')
            job.add_args('node-failure', target_node, '--stabilization-time=10')
            job.add_outputs(output_file, stage_out=True)
            self.wf.add_jobs(job)
            for hc_job in health_check_jobs:
                self.wf.add_dependency(job, parents=[hc_job])
            node_sim_jobs.append(job)
        
        # Stage 3: Interim Health Checks
        interim_hc_jobs = []
        for i in range(1, self.config['interim_checks'] + 1):
            output_file = File(f'interim-hc-{i}.log')
            job = Job('health-check', namespace='rack_resiliency', version='1.0')
            job.add_args('health-check', '--stabilization-time=5')
            job.add_outputs(output_file, stage_out=True)
            self.wf.add_jobs(job)
            for ns_job in node_sim_jobs:
                self.wf.add_dependency(job, parents=[ns_job])
            interim_hc_jobs.append(job)
        
        # Stage 4: Rack Failure Simulations
        rack_sim_jobs = []
        target_racks = ['R1', 'R2', 'R3']
        for i in range(1, self.config['rack_sims'] + 1):
            output_file = File(f'rack-sim-{i}.log')
            target_rack = target_racks[(i - 1) % len(target_racks)]
            job = Job('rack-failure-sim', namespace='rack_resiliency', version='1.0')
            job.add_args('rack-failure', target_rack, '--stabilization-time=10')
            job.add_outputs(output_file, stage_out=True)
            self.wf.add_jobs(job)
            for ihc_job in interim_hc_jobs:
                self.wf.add_dependency(job, parents=[ihc_job])
            rack_sim_jobs.append(job)
        
        # Stage 5: Final Health Checks
        for i in range(1, self.config['final_checks'] + 1):
            output_file = File(f'final-hc-{i}.log')
            job = Job('health-check', namespace='rack_resiliency', version='1.0')
            job.add_args('health-check', '--stabilization-time=5')
            job.add_outputs(output_file, stage_out=True)
            self.wf.add_jobs(job)
            for rs_job in rack_sim_jobs:
                self.wf.add_dependency(job, parents=[rs_job])
        
        return self.wf
    
    def get_workflow_stats(self):
        """Get workflow statistics."""
        total_jobs = sum(self.config.values())
        return {
            'scale': self.scale,
            'total_jobs': total_jobs,
            'cluster_factor': self.cluster_factor,
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
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Pegasus DAX for Docker')
    parser.add_argument('--scale', choices=['1x', '2x', '4x'], default='1x')
    parser.add_argument('--cluster', type=int, default=1)
    parser.add_argument('--output', default='/app/output')
    parser.add_argument('--stats', action='store_true')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"Generating {args.scale} Workflow (Cluster Factor: {args.cluster})")
    print('='*60)
    
    generator = RackResiliencyDAXGenerator(
        scale=args.scale,
        cluster_factor=args.cluster,
        output_dir=args.output
    )
    
    stats = generator.get_workflow_stats()
    print(f"\nWorkflow Statistics:")
    print(f"  Total Jobs: {stats['total_jobs']}")
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
    main()
